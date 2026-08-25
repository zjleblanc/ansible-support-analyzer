#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Ansible Support Analyzer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: gsheet_update
short_description: Update a Google Spreadsheet cell by row lookup
version_added: "1.4.0"
description:
    - Finds a row by matching O(lookup_value) in O(lookup_column), then writes O(update_value) to O(update_column) on that row.
    - Requires the Google Sheets API and a service account JSON key with access to the spreadsheet.
author:
    - Ansible Support Analyzer
options:
    credentials_path:
        description:
            - Path to the Google service account JSON key file.
            - When omitted, the module uses the C(GOOGLE_SA_CRED_PATH) environment variable.
            - Mutually exclusive with O(credentials).
        type: path
    credentials:
        description:
            - Service account JSON key as a dictionary (e.g. from Ansible Vault).
            - Mutually exclusive with O(credentials_path).
        type: dict
        no_log: true
    gsheet_id:
        description:
            - The spreadsheet ID from the Google Sheets URL.
            - When omitted, the module uses the C(GOOGLE_SHEET_ID) environment variable.
        type: str
        aliases: [spreadsheet_id]
    sheet:
        description:
            - Worksheet name within the spreadsheet.
        type: str
        default: Sheet1
    lookup_column:
        description:
            - Column letter to search for O(lookup_value) (e.g. C(A)).
        required: true
        type: str
    lookup_value:
        description:
            - Value to find in O(lookup_column); the matching row is updated.
        required: true
        type: raw
    update_column:
        description:
            - Column letter to write O(update_value) on the matched row (e.g. C(C)).
        required: true
        type: str
    update_value:
        description:
            - Value written to O(update_column) on the matched row.
        required: true
        type: raw
    truncate:
        description:
            - When O(update_value) is JSON and exceeds the Google Sheets single-cell
              character limit, shorten trimmable text values (case descriptions and
              summaries, the AI insights summary) until it fits.
            - Only string values are ever shortened; no JSON key or array element is
              ever added or removed, so the schema written to the cell always matches
              the schema of the untruncated payload.
            - If the payload still does not fit after every trimmable value has been
              shortened as far as possible, the task fails instead of writing
              malformed or schema-inconsistent data.
        type: bool
        default: true
    truncate_priority_products:
        description:
            - Product names whose case text (descriptions, summaries) is shortened
              last, and by the smallest amount, when O(truncate) is needed. Text for
              other products is shortened first.
        type: list
        elements: str
        default: ["Red Hat Ansible Automation Platform"]
    max_cell_chars:
        description:
            - Character threshold used to trigger O(truncate). Kept slightly below
              the Google Sheets 50000-character single-cell limit to leave margin.
        type: int
        default: 49500
'''

EXAMPLES = r'''
- name: Update case count for a customer row (uses GOOGLE_SA_CRED_PATH and GOOGLE_SHEET_ID)
  gsheet_update:
    sheet: Customers
    lookup_column: A
    lookup_value: "{{ support_case_account_name }}"
    update_column: C
    update_value: "{{ all_cases | length }}"

- name: Update with explicit credentials path
  gsheet_update:
    credentials_path: /path/to/service-account.json
    gsheet_id: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    lookup_column: B
    lookup_value: "SWA-1024286"
    update_column: E
    update_value: "Closed"
  register: gsheet_result
'''

RETURN = r'''
row:
    description: 1-based row number that was updated.
    type: int
    returned: success
    sample: 5
updated_range:
    description: A1 notation of the cell that was updated.
    type: str
    returned: success
    sample: "Customers!C5"
gsheet_id:
    description: The spreadsheet ID that was updated.
    type: str
    returned: success
spreadsheet_id:
    description: Alias of O(gsheet_id) for backward compatibility.
    type: str
    returned: success
truncated:
    description: Whether O(update_value) was truncated to fit the single-cell character limit.
    type: bool
    returned: success
    sample: false
original_chars:
    description: Character length of the serialized value before truncation.
    type: int
    returned: when truncated
final_chars:
    description: Character length of the serialized value actually written.
    type: int
    returned: when truncated
'''

import json
import os
import re

from ansible.module_utils.basic import AnsibleModule

try:
    from google.oauth2.service_account import Credentials
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
GOOGLE_SA_CRED_ENV = "GOOGLE_SA_CRED_PATH"
GOOGLE_SHEET_ID_ENV = "GOOGLE_SHEET_ID"
COLUMN_LETTER_RE = re.compile(r"^[A-Za-z]+$")
VALUE_INPUT_OPTION = "USER_ENTERED"
GSHEET_MAX_CELL_CHARS = 49500


def resolve_credentials_path(credentials_path):
    """Return explicit path or fall back to GOOGLE_SA_CRED_PATH."""
    if credentials_path:
        return credentials_path
    return os.environ.get(GOOGLE_SA_CRED_ENV)


def resolve_gsheet_id(gsheet_id):
    """Return explicit spreadsheet ID or fall back to GOOGLE_SHEET_ID."""
    if gsheet_id:
        return gsheet_id
    return os.environ.get(GOOGLE_SHEET_ID_ENV)


def load_credentials(credentials_path, credentials_dict):
    """Build Google service account credentials from a file path or dict."""
    if credentials_path:
        if not os.path.isfile(credentials_path):
            raise ValueError(f"credentials file not found: {credentials_path}")
        return Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return Credentials.from_service_account_info(credentials_dict, scopes=SCOPES)


def normalize_column(column):
    """Validate and return an uppercase column letter."""
    column = str(column).strip()
    if not COLUMN_LETTER_RE.match(column):
        raise ValueError(f"invalid column letter: {column}")
    return column.upper()


def quote_sheet(sheet):
    """Quote a worksheet name for A1 notation."""
    escaped = sheet.replace("'", "''")
    return f"'{escaped}'"


def column_range(sheet, column):
    """Return A1 range for an entire column on a worksheet."""
    return f"{quote_sheet(sheet)}!{column}:{column}"


def cell_range(sheet, column, row):
    """Return A1 range for a single cell."""
    return f"{quote_sheet(sheet)}!{column}{row}"


def coerce_cell_value(value):
    """Return a scalar Google Sheets accepts (str, int, float, bool).

    Ansible may pass dict/list for type=raw when the rendered value looks like
    JSON; the API rejects those as struct_value unless serialized to text.
    """
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return json.dumps(value, default=str, separators=(",", ":"))
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    return str(value)


def cell_values_match(cell, lookup_value):
    """Compare a sheet cell to the requested lookup value."""
    if cell is None or cell == "":
        return False
    return str(cell) == str(coerce_cell_value(lookup_value))


def find_row_by_lookup(column_values, lookup_value):
    """Return 1-based row number for the first matching lookup_value."""
    for index, row in enumerate(column_values):
        cell = row[0] if row else None
        if cell_values_match(cell, lookup_value):
            return index + 1
    return None


def get_column_values(service, spreadsheet_id, sheet, column):
    """Read all values from a single column."""
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=column_range(sheet, column),
        )
        .execute()
    )
    return result.get("values", [])


def update_cell(service, spreadsheet_id, range_name, value):
    """Write a single cell using USER_ENTERED parsing."""
    cell_value = coerce_cell_value(value)
    return (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=VALUE_INPUT_OPTION,
            body={"values": [[cell_value]]},
        )
        .execute()
    )


# Successive character caps applied to trimmable text fields, largest first.
# 0 means "shrink to an empty string" -- the key is always kept.
_TRIM_LENGTH_STAGES = (1500, 500, 150, 40, 0)


def _is_priority_case(case, priority_products):
    """Return True when a case's product is in the preserved priority set."""
    return isinstance(case, dict) and case.get("product") in priority_products


def _dumps(data):
    """Serialize to minified JSON, tolerating non-JSON-native leftovers."""
    return json.dumps(data, separators=(",", ":"), default=str)


def _cap_string(value, max_len):
    """Shorten a string value to at most max_len characters.

    Returns (new_value, changed). Never returns anything but a string when
    given a string, so the field's key and type are always preserved.
    """
    if not isinstance(value, str) or len(value) <= max_len:
        return value, False
    if max_len <= 0:
        return "", True
    return value[: max_len - 1].rstrip() + "\u2026", True


def _collect_trim_tiers(data, priority_products):
    """Group every trimmable (container, key) text field into three tiers.

    Tier 0 (shrunk first): fields belonging to non-priority products.
    Tier 1 (shrunk next): fields belonging to priority products.
    Tier 2 (shrunk last): account/report-level text not tied to a product
    (e.g. the AI summary).

    Only *values* are ever modified by the caller -- no key is added or
    removed here, so the JSON schema is always preserved.
    """
    tier0, tier1, tier2 = [], [], []

    for case in data.get("cases") or []:
        if not isinstance(case, dict):
            continue
        tier = tier1 if _is_priority_case(case, priority_products) else tier0
        for key in ("description", "summary"):
            if isinstance(case.get(key), str):
                tier.append((case, key))

    for product in data.get("products") or []:
        if not isinstance(product, dict):
            continue
        tier = tier1 if product.get("product") in priority_products else tier0
        for row in product.get("cases") or []:
            if isinstance(row, dict) and isinstance(row.get("summary"), str):
                tier.append((row, "summary"))

    for account in data.get("accounts") or []:
        if not isinstance(account, dict):
            continue
        for bucket in account.get("cases_by_severity") or []:
            if not isinstance(bucket, dict):
                continue
            for row in bucket.get("cases") or []:
                if not isinstance(row, dict):
                    continue
                tier = tier1 if _is_priority_case(row, priority_products) else tier0
                if isinstance(row.get("summary"), str):
                    tier.append((row, "summary"))

    ai_insights = data.get("ai_insights")
    if isinstance(ai_insights, dict) and isinstance(ai_insights.get("summary"), str):
        tier2.append((ai_insights, "summary"))

    return tier0, tier1, tier2


def smart_truncate_json(value_str, max_chars, priority_products):
    """Shrink text fields in a JSON-serialized value to fit within max_chars.

    Only string *values* are ever shortened in place; no key or array
    element is ever added or removed, so the schema of the payload written
    to the cell is always identical to the untruncated version -- callers
    relying on json.loads() with a fixed shape will not break.

    Non-priority-product text is shrunk before priority-product text, and
    report-level text (e.g. the AI summary) is shrunk last.

    Returns a (value, truncated) tuple, or (None, None) if the payload still
    can't fit under max_chars even after every trimmable field has been
    shrunk to empty -- callers should treat that as a hard failure rather
    than emit something inconsistent or invalid.
    """
    if len(value_str) <= max_chars:
        return value_str, False

    try:
        data = json.loads(value_str)
    except (ValueError, TypeError):
        return None, None

    if not isinstance(data, dict):
        return None, None

    priority_products = set(priority_products or [])

    def fits():
        return len(_dumps(data)) <= max_chars

    for tier in _collect_trim_tiers(data, priority_products):
        if not tier:
            continue
        for cap in _TRIM_LENGTH_STAGES:
            changed = False
            for container, key in tier:
                new_value, did_change = _cap_string(container.get(key), cap)
                if did_change:
                    container[key] = new_value
                    changed = True
            if changed and fits():
                return _dumps(data), True

    return (None, None) if not fits() else (_dumps(data), True)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            credentials_path=dict(type="path"),
            credentials=dict(type="dict", no_log=True),
            gsheet_id=dict(type="str", aliases=["spreadsheet_id"]),
            sheet=dict(type="str", default="Sheet1"),
            lookup_column=dict(type="str", required=True),
            lookup_value=dict(type="raw", required=True),
            update_column=dict(type="str", required=True),
            update_value=dict(type="raw", required=True),
            truncate=dict(type="bool", default=True),
            truncate_priority_products=dict(
                type="list",
                elements="str",
                default=["Red Hat Ansible Automation Platform"],
            ),
            max_cell_chars=dict(type="int", default=GSHEET_MAX_CELL_CHARS),
        ),
        mutually_exclusive=[["credentials_path", "credentials"]],
        supports_check_mode=True,
    )

    if not HAS_GOOGLE:
        module.fail_json(
            msg=(
                "google-api-python-client and google-auth are required. "
                "Install with: pip install google-api-python-client google-auth"
            )
        )

    credentials_dict = module.params["credentials"]
    credentials_path = module.params["credentials_path"]
    if not credentials_dict:
        credentials_path = resolve_credentials_path(credentials_path)

    gsheet_id = resolve_gsheet_id(module.params["gsheet_id"])
    sheet = module.params["sheet"]
    lookup_value = module.params["lookup_value"]
    update_value = module.params["update_value"]

    if not gsheet_id:
        module.fail_json(
            msg=(
                "Spreadsheet ID required: set gsheet_id "
                f"or {GOOGLE_SHEET_ID_ENV} environment variable"
            )
        )

    if not credentials_dict and not credentials_path:
        module.fail_json(
            msg=(
                "Google credentials required: set credentials_path, credentials, "
                f"or {GOOGLE_SA_CRED_ENV} environment variable"
            )
        )

    try:
        lookup_column = normalize_column(module.params["lookup_column"])
        update_column = normalize_column(module.params["update_column"])
    except ValueError as exc:
        module.fail_json(msg=str(exc))

    try:
        creds = load_credentials(credentials_path, credentials_dict)
    except (ValueError, OSError) as exc:
        module.fail_json(msg=str(exc))

    try:
        service = build("sheets", "v4", credentials=creds)
        column_values = get_column_values(
            service, gsheet_id, sheet, lookup_column
        )
    except HttpError as exc:
        module.fail_json(msg=f"Google Sheets API error: {exc}")
    except Exception as exc:
        module.fail_json(msg=f"Failed to read spreadsheet: {exc}")

    row = find_row_by_lookup(column_values, lookup_value)
    if row is None:
        module.fail_json(
            msg=(
                f"lookup_value {lookup_value!r} not found in column "
                f"{lookup_column} on sheet {sheet!r}"
            )
        )

    target_range = cell_range(sheet, update_column, row)

    cell_value = coerce_cell_value(update_value)
    truncated = False
    original_chars = None
    final_chars = None
    if module.params["truncate"] and isinstance(cell_value, str):
        max_cell_chars = module.params["max_cell_chars"]
        if len(cell_value) > max_cell_chars:
            original_chars = len(cell_value)
            shrunk_value, truncated = smart_truncate_json(
                cell_value, max_cell_chars, module.params["truncate_priority_products"]
            )
            if shrunk_value is None:
                module.fail_json(
                    msg=(
                        f"update_value is {original_chars} characters, which exceeds "
                        f"the Google Sheets {max_cell_chars}-character cell limit even "
                        "after shortening every trimmable text field (case "
                        "descriptions/summaries, AI insights summary) as far as "
                        "possible while preserving the JSON schema. Reduce the amount "
                        "of case data included in the report, raise max_cell_chars if "
                        "you control the consuming schema, or set truncate=false to "
                        "surface the original API error."
                    )
                )
            cell_value = shrunk_value
            final_chars = len(cell_value)

    if module.check_mode:
        module.exit_json(
            changed=True,
            gsheet_id=gsheet_id,
            spreadsheet_id=gsheet_id,
            row=row,
            updated_range=target_range,
            truncated=truncated,
            **({"original_chars": original_chars, "final_chars": final_chars} if truncated else {}),
            check_mode=True,
        )

    try:
        result = update_cell(service, gsheet_id, target_range, cell_value)
    except HttpError as exc:
        module.fail_json(msg=f"Google Sheets API error: {exc}")
    except Exception as exc:
        module.fail_json(msg=f"Failed to update spreadsheet: {exc}")

    module.exit_json(
        changed=True,
        gsheet_id=result.get("spreadsheetId", gsheet_id),
        spreadsheet_id=result.get("spreadsheetId", gsheet_id),
        row=row,
        updated_range=result.get("updatedRange", target_range),
        updated_cells=result.get("updatedCells", 1),
        truncated=truncated,
        **({"original_chars": original_chars, "final_chars": final_chars} if truncated else {}),
    )


if __name__ == "__main__":
    main()

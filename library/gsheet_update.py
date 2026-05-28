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
'''

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


def cell_values_match(cell, lookup_value):
    """Compare a sheet cell to the requested lookup value."""
    if cell is None or cell == "":
        return False
    return str(cell) == str(lookup_value)


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
    return (
        service.spreadsheets()
        .values()
        .update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption=VALUE_INPUT_OPTION,
            body={"values": [[value]]},
        )
        .execute()
    )


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

    if module.check_mode:
        module.exit_json(
            changed=True,
            gsheet_id=gsheet_id,
            spreadsheet_id=gsheet_id,
            row=row,
            updated_range=target_range,
            check_mode=True,
        )

    try:
        result = update_cell(service, gsheet_id, target_range, update_value)
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
    )


if __name__ == "__main__":
    main()

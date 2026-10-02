#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Ansible Support Analyzer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: gsheet_tracker
short_description: Track active support cases in a dedicated Google Sheet tab and diff against the previous run
version_added: "1.5.0"
description:
    - Owns a single worksheet tab end-to-end as a case tracker. The module manages the sheet's
      structure itself (header row, column layout, row contents); callers should treat the tab
      as owned storage rather than a hand-maintained spreadsheet.
    - On each run, reads the previously recorded rows for O(account_name), compares them against
      O(cases) (the current set of active cases), and replaces that account's rows with the new
      data. Rows belonging to other accounts already present in the sheet are left untouched.
    - Returns the computed diff (new cases, closed cases, and cases whose severity/status/owner
      changed) so a playbook can build a change notification without re-deriving it in Jinja2.
    - Requires the Google Sheets API and a service account JSON key with Editor access to the
      spreadsheet.
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
            - Worksheet tab name dedicated to case tracking. The module owns this tab completely
              (header row and all data rows); do not share it with other playbooks or reports.
        type: str
        default: "Support Case Tracker"
    account_name:
        description:
            - Identifies which rows in the tracker tab belong to this account. Only rows whose
              Account column matches this value are read, diffed, and replaced.
        required: true
        type: str
    cases:
        description:
            - Current active cases for O(account_name). Each case is a dict with keys
              C(case_id) (required), C(summary), C(product), C(severity), C(status), C(owner),
              C(created), and C(last_modified). Unknown keys are ignored.
        type: list
        elements: dict
        default: []
'''

EXAMPLES = r'''
- name: Record active cases and compute the diff since the last run
  gsheet_tracker:
    sheet: "Case Tracker"
    account_name: "Parasol"
    cases:
      - case_id: "03919019"
        summary: "Cluster nodes failing to join"
        product: "Red Hat Ansible Automation Platform"
        severity: "1 (Urgent)"
        status: "Waiting on Red Hat"
        owner: "Jane Doe"
        created: "2026-09-01T12:00:00Z"
        last_modified: "2026-09-30T08:15:00Z"
  register: tracker_result

- name: Use explicit credentials path
  gsheet_tracker:
    credentials_path: /path/to/service-account.json
    gsheet_id: "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms"
    sheet: "Case Tracker"
    account_name: "Southwest Airlines"
    cases: "{{ current_cases }}"
  register: tracker_result
'''

RETURN = r'''
changed:
    description: Whether the sheet was modified (always true unless check_mode, since last_seen is refreshed).
    type: bool
    returned: success
new_cases:
    description: Cases present now that were not present on the previous run.
    type: list
    elements: dict
    returned: success
closed_cases:
    description: Cases present on the previous run that are no longer active.
    type: list
    elements: dict
    returned: success
updated_cases:
    description: >-
        Cases present on both runs whose severity, status, or owner changed. Each entry includes
        the case identity plus a C(changes) dict of C(field) -> C({old, new}).
    type: list
    elements: dict
    returned: success
total_current:
    description: Number of cases passed in via O(cases).
    type: int
    returned: success
total_previous:
    description: Number of cases previously recorded for O(account_name).
    type: int
    returned: success
has_changes:
    description: True when any case was added, closed, or updated.
    type: bool
    returned: success
gsheet_id:
    description: The spreadsheet ID that was updated.
    type: str
    returned: success
sheet:
    description: The worksheet tab name used.
    type: str
    returned: success
'''

import os

from datetime import datetime, timezone

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
VALUE_INPUT_OPTION = "USER_ENTERED"

# Column layout owned by this module. "account" is always column A so a single
# tab can safely hold rows for many accounts.
HEADER_DISPLAY = [
    "Account", "Case ID", "Summary", "Product", "Severity",
    "Status", "Owner", "Created", "Last Modified", "Last Seen",
]
HEADER_KEYS = [
    "account", "case_id", "summary", "product", "severity",
    "status", "owner", "created", "last_modified", "last_seen",
]

# Fields whose change on an otherwise-still-open case is worth surfacing in a
# notification (as opposed to e.g. a cosmetic resync of the same values).
TRACKED_CHANGE_FIELDS = ["severity", "status", "owner"]

CASE_INPUT_KEYS = [
    "case_id", "summary", "product", "severity",
    "status", "owner", "created", "last_modified",
]


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


def quote_sheet(sheet):
    """Quote a worksheet name for A1 notation."""
    escaped = sheet.replace("'", "''")
    return f"'{escaped}'"


def get_sheet_values(service, spreadsheet_id, sheet):
    """Read every populated row from a worksheet tab."""
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=quote_sheet(sheet))
        .execute()
    )
    return result.get("values", [])


def pad_row(row, width):
    """Right-pad a row with empty strings so every row has the same width."""
    row = list(row[:width])
    row.extend([""] * (width - len(row)))
    return row


def row_to_dict(row):
    """Map a padded raw row to a dict keyed by HEADER_KEYS."""
    return dict(zip(HEADER_KEYS, row))


def case_to_row(account_name, case, last_seen):
    """Build a raw sheet row from a normalized case dict."""
    return [
        account_name,
        str(case.get("case_id", "")),
        case.get("summary", "") or "",
        case.get("product", "") or "",
        case.get("severity", "") or "",
        case.get("status", "") or "",
        case.get("owner", "") or "",
        case.get("created", "") or "",
        case.get("last_modified", "") or "",
        last_seen,
    ]


def normalize_case(case):
    """Keep only recognized keys and coerce case_id to a string."""
    normalized = {key: case.get(key, "") for key in CASE_INPUT_KEYS}
    normalized["case_id"] = str(normalized["case_id"]).strip()
    return normalized


def diff_cases(previous_by_id, current_by_id):
    """Compute new/closed/updated cases between two case_id-keyed dicts."""
    previous_ids = set(previous_by_id)
    current_ids = set(current_by_id)

    new_cases = [current_by_id[cid] for cid in sorted(current_ids - previous_ids)]
    closed_cases = [previous_by_id[cid] for cid in sorted(previous_ids - current_ids)]

    updated_cases = []
    for cid in sorted(previous_ids & current_ids):
        previous_case = previous_by_id[cid]
        current_case = current_by_id[cid]
        changes = {}
        for field in TRACKED_CHANGE_FIELDS:
            old_value = previous_case.get(field, "")
            new_value = current_case.get(field, "")
            if (old_value or "") != (new_value or ""):
                changes[field] = {"old": old_value, "new": new_value}
        if changes:
            updated_cases.append({
                "case_id": cid,
                "summary": current_case.get("summary", ""),
                "product": current_case.get("product", ""),
                "changes": changes,
            })

    return new_cases, closed_cases, updated_cases


def main():
    module = AnsibleModule(
        argument_spec=dict(
            credentials_path=dict(type="path"),
            credentials=dict(type="dict", no_log=True),
            gsheet_id=dict(type="str", aliases=["spreadsheet_id"]),
            sheet=dict(type="str", default="Support Case Tracker"),
            account_name=dict(type="str", required=True),
            cases=dict(type="list", elements="dict", default=[]),
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
    account_name = module.params["account_name"]

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
        creds = load_credentials(credentials_path, credentials_dict)
    except (ValueError, OSError) as exc:
        module.fail_json(msg=str(exc))

    try:
        service = build("sheets", "v4", credentials=creds)
        existing_values = get_sheet_values(service, gsheet_id, sheet)
    except HttpError as exc:
        module.fail_json(msg=f"Google Sheets API error: {exc}")
    except Exception as exc:
        module.fail_json(msg=f"Failed to read spreadsheet: {exc}")

    # Row 0 (if present) is always treated as the header this module writes;
    # every remaining row is a data row in the fixed HEADER_KEYS column order.
    data_rows = [pad_row(row, len(HEADER_DISPLAY)) for row in existing_values[1:]]

    other_account_rows = [row for row in data_rows if row[0] != account_name]
    previous_account_rows = [row_to_dict(row) for row in data_rows if row[0] == account_name]
    previous_by_id = {
        row["case_id"]: row for row in previous_account_rows if row.get("case_id")
    }

    normalized_cases = [normalize_case(case) for case in module.params["cases"]]
    missing_id = next((c for c in normalized_cases if not c["case_id"]), None)
    if missing_id is not None:
        module.fail_json(msg="Every case in 'cases' must include a non-empty case_id")
    current_by_id = {case["case_id"]: case for case in normalized_cases}

    new_cases, closed_cases, updated_cases = diff_cases(previous_by_id, current_by_id)
    has_changes = bool(new_cases or closed_cases or updated_cases)

    last_seen = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    this_account_rows = [
        case_to_row(account_name, case, last_seen)
        for case in sorted(
            normalized_cases,
            key=lambda c: (c.get("severity") or "", c.get("case_id") or ""),
        )
    ]

    result = dict(
        changed=True,
        new_cases=new_cases,
        closed_cases=closed_cases,
        updated_cases=updated_cases,
        total_current=len(current_by_id),
        total_previous=len(previous_by_id),
        has_changes=has_changes,
        gsheet_id=gsheet_id,
        sheet=sheet,
    )

    if module.check_mode:
        result["check_mode"] = True
        module.exit_json(**result)

    full_matrix = [HEADER_DISPLAY] + other_account_rows + this_account_rows

    try:
        service.spreadsheets().values().clear(
            spreadsheetId=gsheet_id, range=quote_sheet(sheet), body={}
        ).execute()
        service.spreadsheets().values().update(
            spreadsheetId=gsheet_id,
            range=f"{quote_sheet(sheet)}!A1",
            valueInputOption=VALUE_INPUT_OPTION,
            body={"values": full_matrix},
        ).execute()
    except HttpError as exc:
        module.fail_json(msg=f"Google Sheets API error: {exc}")
    except Exception as exc:
        module.fail_json(msg=f"Failed to update spreadsheet: {exc}")

    module.exit_json(**result)


if __name__ == "__main__":
    main()

#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Ansible Support Analyzer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: gsheet_tracker
short_description: Track active support cases in a dedicated Google Sheet tab and diff against the previous run
version_added: "1.5.0"
description:
    - Owns a single worksheet tab end-to-end as a case tracker. The module manages the sheet's
      structure itself (header row, column layout, row contents); callers should treat the tab
      as owned storage rather than a hand-maintained spreadsheet.
    - Split into three explicit, composable operations so a multi-account playbook can make
      B(exactly one) read and B(exactly one) write against the Google Sheets API per run,
      regardless of how many accounts are tracked, instead of one read+write pair per account.
    - C(read) reads the whole tab once and returns the previous rows for a set of accounts
      (grouped per account) plus every row that belongs to B(other) accounts, verbatim
      (including any C(HYPERLINK) formulas — the read uses the Sheets API C(FORMULA) render
      option so round-tripping those rows back through C(write) does not strip them).
    - C(diff) is a pure, local computation — no Google API calls at all. Given the
      O(existing_rows) from a prior C(read) and the current O(cases) for one O(account_name),
      it computes the diff (new/closed/updated cases) and builds that account's replacement
      rows, stamped with a fresh C(last_seen) timestamp.
    - C(write) takes the fully assembled row list (the untouched rows from C(read)'s
      O(other_rows) plus every account's rows from its C(diff) call, concatenated by the
      caller) and performs a single clear+rewrite of the tab.
author:
    - Ansible Support Analyzer
options:
    state:
        description:
            - C(read) reads the sheet once and returns previous state for O(account_names)
              (grouped per account, including each one's C(last_seen_timestamp)) plus
              C(other_rows) — raw rows belonging to accounts outside O(account_names) — B(without
              writing anything).
            - C(diff) computes the new/closed/updated diff for one account against
              O(existing_rows) (as returned by a prior C(read) call) and builds that account's
              replacement rows. Purely local; makes no Google API calls.
            - C(write) performs the single clear+rewrite of the tab with O(rows) (the full,
              pre-assembled row list for every account).
        type: str
        choices: [read, diff, write]
        required: true
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
    table_name:
        description:
            - Name of a Google Sheets API "Table" object to create (or resize) over the tab's
              data range on every C(write). Google Sheets Tables are a Sheets API v4 feature
              (C(addTable)/C(updateTable) C(batchUpdate) requests); the Google B(Drive) API has
              no concept of spreadsheet tables or cell data at all, so this is implemented purely
              against the Sheets API the module already uses.
            - Only used by C(state=write). Set to an empty string to skip table management.
            - Best-effort: a failure to create/resize the table emits an Ansible warning rather
              than failing the task, since the row data itself has already been written
              successfully by the time this runs.
        type: str
    account_name:
        description:
            - Identifies which rows belong to this account. Required for O(state=diff).
        type: str
    account_names:
        description:
            - List of account names to summarize previous state for. Required for O(state=read).
              Rows belonging to any other account are returned verbatim via C(other_rows)
              instead.
        type: list
        elements: str
    existing_rows:
        description:
            - The full, raw data-row matrix as returned by a prior O(state=read) call's
              C(existing_rows). Required for O(state=diff).
        type: list
        elements: list
    cases:
        description:
            - Current active cases for O(account_name). Each case is a dict with keys
              C(case_id) (required), C(summary), C(product), C(severity), C(status), C(owner),
              C(created), and C(last_modified). Unknown keys are ignored. Used by O(state=diff).
        type: list
        elements: dict
        default: []
    rows:
        description:
            - The full, pre-assembled row matrix (header excluded) to write to the sheet.
              Typically O(state=read)'s C(other_rows) concatenated with every tracked
              account's C(rows) from its own O(state=diff) call. Used by O(state=write).
        type: list
        elements: list
        default: []
"""

EXAMPLES = r"""
- name: Read previous state once for every tracked account
  gsheet_tracker:
    state: read
    sheet: "Case Tracker"
    account_names: "{{ support_case_accounts | map(attribute='name') | list }}"
  register: tracker_read

- name: Compute the diff for one account (no API calls)
  gsheet_tracker:
    state: diff
    account_name: "Parasol"
    existing_rows: "{{ tracker_read.existing_rows }}"
    cases:
      - case_id: "03919019"
        summary: "Cluster nodes failing to join"
        product: "Red Hat Ansible Automation Platform"
        severity: "1 (Urgent)"
        status: "Waiting on Red Hat"
        owner: "Jane Doe"
        created: "2026-09-01T12:00:00Z"
        last_modified: "2026-09-30T08:15:00Z"
  register: tracker_diff

- name: Write every account's rows back in a single call
  gsheet_tracker:
    state: write
    sheet: "Case Tracker"
    table_name: "Case Tracker"
    rows: "{{ tracker_read.other_rows + tracker_diff.rows }}"
  register: tracker_write
"""

RETURN = r"""
changed:
    description: Whether the sheet was modified. Always false for C(read)/C(diff); true for C(write) (unless check_mode).
    type: bool
    returned: success
existing_rows:
    description: >-
        Every raw data row currently in the sheet (padded, header excluded). Pass straight
        into O(state=diff)'s O(existing_rows). Returned by C(state=read).
    type: list
    elements: list
    returned: state=read
other_rows:
    description: >-
        Raw rows belonging to accounts outside O(account_names), verbatim (including any
        HYPERLINK formulas). Concatenate with every account's C(diff) rows before
        O(state=write). Returned by C(state=read).
    type: list
    elements: list
    returned: state=read
accounts:
    description: Per-account previous state, keyed by account name. Returned by C(state=read).
    type: dict
    returned: state=read
    contains:
        last_seen_timestamp:
            description: >-
                The latest C(Last Seen) value previously recorded for this account, or an
                empty string when no previous rows exist.
            type: str
        total_previous:
            description: Number of rows previously recorded for this account.
            type: int
new_cases:
    description: Cases present now that were not present on the previous run. Returned by C(state=diff).
    type: list
    elements: dict
    returned: state=diff
closed_cases:
    description: Cases present on the previous run that are no longer active. Returned by C(state=diff).
    type: list
    elements: dict
    returned: state=diff
updated_cases:
    description: >-
        Cases present on both runs whose severity, status, or owner changed. Each entry includes
        the case identity plus a C(changes) dict of C(field) -> C({old, new}). Returned by C(state=diff).
    type: list
    elements: dict
    returned: state=diff
total_current:
    description: Number of cases passed in via O(cases). Returned by C(state=diff).
    type: int
    returned: state=diff
total_previous:
    description: Number of cases previously recorded for O(account_name). Returned by C(state=diff).
    type: int
    returned: state=diff
has_changes:
    description: True when any case was added, closed, or updated. Returned by C(state=diff).
    type: bool
    returned: state=diff
rows:
    description: >-
        This account's freshly-built replacement rows, stamped with the current
        C(last_seen) timestamp. Accumulate across accounts and pass to O(state=write)'s
        O(rows). Returned by C(state=diff).
    type: list
    elements: list
    returned: state=diff
total_rows:
    description: Number of data rows written to the sheet (header not included). Returned by C(state=write).
    type: int
    returned: state=write
gsheet_id:
    description: The spreadsheet ID used.
    type: str
    returned: success
sheet:
    description: The worksheet tab name used.
    type: str
    returned: success
"""

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
    "Account",
    "Case ID",
    "Summary",
    "Product",
    "Severity",
    "Status",
    "Owner",
    "Created",
    "Last Modified",
    "Last Seen",
]
HEADER_KEYS = [
    "account",
    "case_id",
    "summary",
    "product",
    "severity",
    "status",
    "owner",
    "created",
    "last_modified",
    "last_seen",
]

# Fields whose change on an otherwise-still-open case is worth surfacing in a
# notification (as opposed to e.g. a cosmetic resync of the same values).
TRACKED_CHANGE_FIELDS = ["severity", "status", "owner"]

CASE_INPUT_KEYS = [
    "case_id",
    "summary",
    "product",
    "severity",
    "status",
    "owner",
    "created",
    "last_modified",
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
    """Read every populated row from a worksheet tab.

    Uses valueRenderOption=FORMULA so that cells containing a formula (e.g. the
    Case ID column's =HYPERLINK(...) formulas) round-trip back through write()
    verbatim instead of being flattened to their last computed display value.
    """
    result = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=quote_sheet(sheet),
            valueRenderOption="FORMULA",
        )
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


CASE_URL_BASE = "https://access.redhat.com/support/cases/#/case/"


def case_id_cell(case_id):
    """Return a HYPERLINK formula for the case ID, or a plain string if empty."""
    if not case_id:
        return ""
    return f'=HYPERLINK("{CASE_URL_BASE}{case_id}","{case_id}")'


def case_to_row(account_name, case, last_seen):
    """Build a raw sheet row from a normalized case dict."""
    return [
        account_name,
        case_id_cell(str(case.get("case_id", ""))),
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


def latest_last_seen(previous_account_rows):
    """Return the most recent last_seen value from previous account rows, or ''."""
    timestamps = [row.get("last_seen", "") for row in previous_account_rows]
    timestamps = [t for t in timestamps if t]
    return max(timestamps) if timestamps else ""


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
            updated_cases.append(
                {
                    "case_id": cid,
                    "summary": current_case.get("summary", ""),
                    "product": current_case.get("product", ""),
                    "changes": changes,
                }
            )

    return new_cases, closed_cases, updated_cases


def find_sheet_and_table(service, spreadsheet_id, sheet_name, table_name):
    """Return (sheet_id, existing_table_or_None) for the given tab/table name.

    Note: this is a Sheets API v4 feature (addTable/updateTable batchUpdate
    requests); the Drive API has no endpoint for spreadsheet cell data or
    tables at all, so table management is implemented purely against the same
    Sheets API service this module already builds.
    """
    meta = (
        service.spreadsheets()
        .get(
            spreadsheetId=spreadsheet_id,
            fields="sheets(properties(sheetId,title),tables(tableId,name,range))",
        )
        .execute()
    )
    for sheet_meta in meta.get("sheets", []):
        props = sheet_meta.get("properties", {})
        if props.get("title") != sheet_name:
            continue
        sheet_id = props.get("sheetId")
        for table in sheet_meta.get("tables", []) or []:
            if table.get("name") == table_name:
                return sheet_id, table
        return sheet_id, None
    return None, None


def ensure_table(service, spreadsheet_id, sheet_name, table_name, num_rows, num_cols):
    """Create (or resize) a Sheets API Table covering the tab's full data range."""
    sheet_id, existing_table = find_sheet_and_table(
        service, spreadsheet_id, sheet_name, table_name
    )
    if sheet_id is None:
        raise ValueError(f"worksheet tab '{sheet_name}' not found")

    table_range = {
        "sheetId": sheet_id,
        "startRowIndex": 0,
        "endRowIndex": max(num_rows, 1),
        "startColumnIndex": 0,
        "endColumnIndex": max(num_cols, 1),
    }

    if existing_table is None:
        request = {"addTable": {"table": {"name": table_name, "range": table_range}}}
    else:
        request = {
            "updateTable": {
                "table": {"tableId": existing_table["tableId"], "range": table_range},
                "fields": "range",
            }
        }

    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id, body={"requests": [request]}
    ).execute()


def build_service(module):
    """Resolve credentials/gsheet_id and build the Sheets API service, failing the module on error."""
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
    except Exception as exc:
        module.fail_json(msg=f"Failed to build Sheets API client: {exc}")

    return service, gsheet_id


def do_read(module, sheet):
    """state=read: one API read; returns per-account previous state plus other accounts' raw rows."""
    service, gsheet_id = build_service(module)
    account_names = module.params["account_names"] or []

    try:
        existing_values = get_sheet_values(service, gsheet_id, sheet)
    except HttpError as exc:
        module.fail_json(msg=f"Google Sheets API error: {exc}")
    except Exception as exc:
        module.fail_json(msg=f"Failed to read spreadsheet: {exc}")

    # Row 0 (if present) is always treated as the header this module writes;
    # every remaining row is a data row in the fixed HEADER_KEYS column order.
    data_rows = [pad_row(row, len(HEADER_DISPLAY)) for row in existing_values[1:]]

    other_rows = [row for row in data_rows if row[0] not in account_names]

    accounts = {}
    for name in account_names:
        rows_for_account = [row_to_dict(row) for row in data_rows if row[0] == name]
        accounts[name] = {
            "last_seen_timestamp": latest_last_seen(rows_for_account),
            "total_previous": len(rows_for_account),
        }

    module.exit_json(
        changed=False,
        existing_rows=data_rows,
        other_rows=other_rows,
        accounts=accounts,
        gsheet_id=gsheet_id,
        sheet=sheet,
    )


def do_diff(module, sheet):
    """state=diff: pure local computation, no Google API calls."""
    account_name = module.params["account_name"]
    if not account_name:
        module.fail_json(msg="account_name is required when state=diff")

    existing_rows = module.params["existing_rows"]
    if existing_rows is None:
        module.fail_json(
            msg="existing_rows is required when state=diff (pass through state=read's existing_rows)"
        )

    data_rows = [pad_row(row, len(HEADER_DISPLAY)) for row in existing_rows]
    previous_account_rows = [
        row_to_dict(row) for row in data_rows if row and row[0] == account_name
    ]
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

    module.exit_json(
        changed=False,
        new_cases=new_cases,
        closed_cases=closed_cases,
        updated_cases=updated_cases,
        total_current=len(current_by_id),
        total_previous=len(previous_by_id),
        has_changes=has_changes,
        rows=this_account_rows,
        gsheet_id=resolve_gsheet_id(module.params["gsheet_id"]) or "",
        sheet=sheet,
    )


def do_write(module, sheet):
    """state=write: the single clear+rewrite of the whole tab for this run."""
    rows = module.params["rows"]
    table_name = module.params["table_name"]

    if module.check_mode:
        module.exit_json(
            changed=True,
            check_mode=True,
            total_rows=len(rows),
            gsheet_id=resolve_gsheet_id(module.params["gsheet_id"]) or "",
            sheet=sheet,
        )

    service, gsheet_id = build_service(module)
    full_matrix = [HEADER_DISPLAY] + rows

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

    if table_name:
        try:
            ensure_table(
                service,
                gsheet_id,
                sheet,
                table_name,
                len(full_matrix),
                len(HEADER_DISPLAY),
            )
        except Exception as exc:
            module.warn(
                f"Row data was written, but creating/resizing table '{table_name}' failed: {exc}"
            )

    module.exit_json(
        changed=True,
        total_rows=len(rows),
        gsheet_id=gsheet_id,
        sheet=sheet,
    )


def main():
    module = AnsibleModule(
        argument_spec=dict(
            state=dict(type="str", required=True, choices=["read", "diff", "write"]),
            credentials_path=dict(type="path"),
            credentials=dict(type="dict", no_log=True),
            gsheet_id=dict(type="str", aliases=["spreadsheet_id"]),
            sheet=dict(type="str", default="Support Case Tracker"),
            table_name=dict(type="str"),
            account_name=dict(type="str"),
            account_names=dict(type="list", elements="str"),
            existing_rows=dict(type="list", elements="list"),
            cases=dict(type="list", elements="dict", default=[]),
            rows=dict(type="list", elements="list", default=[]),
        ),
        mutually_exclusive=[["credentials_path", "credentials"]],
        supports_check_mode=True,
    )

    state = module.params["state"]
    sheet = module.params["sheet"]

    if state == "read":
        do_read(module, sheet)
    elif state == "diff":
        do_diff(module, sheet)
    elif state == "write":
        do_write(module, sheet)


if __name__ == "__main__":
    main()

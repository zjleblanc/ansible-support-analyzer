# Google Sheets Quick Start

Push support-case analysis JSON into a shared Google Spreadsheet using a **service account**. This guide covers Google Cloud setup, credentials, and running the playbook with the `json` tag.

## Overview

1. The playbook analyzes each entry in `support_case_accounts`.
2. With the `json` tag (included in a normal run), it renders `templates/report.json.j2` and calls `gsheet_update`.
3. The module finds a row where the **lookup column** matches the account name (or `gsheet_lookup_value`), then writes the JSON into the **update column**.

```
Spreadsheet row:  ... | K (lookup) = "Parasol" | ... | O (update) = { "report": ... } |
```

## 1. Google Cloud setup

### Enable the API

1. Open [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project.
3. Go to **APIs & Services → Library**.
4. Enable **Google Sheets API**.

### Create a service account

1. **IAM & Admin → Service Accounts → Create service account**.
2. Name it (e.g. `support-analyzer-sheets`).
3. Skip optional role grants (Sheets access is granted by sharing the spreadsheet).
4. **Keys → Add key → Create new key → JSON**.
5. Save the downloaded JSON file securely (e.g. `~/.config/support-analyzer/google-sa.json`).

Note the service account email (`...@....iam.gserviceaccount.com`).

### Share the spreadsheet

1. Open your target Google Sheet.
2. **Share** with the service account email as **Editor**.
3. Copy the **spreadsheet ID** from the URL:
   `https://docs.google.com/spreadsheets/d/`**`SPREADSHEET_ID`**`/edit`

### Prepare the worksheet

- Use a worksheet tab name that matches `GSHEET_SHEET` (default: `Accounts`).
- Put each customer’s lookup value in the lookup column (e.g. column `K`).
- The playbook writes the JSON report to the update column (e.g. column `O`) on the matching row.

## 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

This installs `google-api-python-client` and `google-auth` required by `library/gsheet_update.py`.

## 3. Configure credentials

### Environment variables (CLI / CI)

```bash
export GOOGLE_SA_CRED_PATH="$HOME/.config/support-analyzer/google-sa.json"
export GOOGLE_SHEET_ID="your-spreadsheet-id"
export GSHEET_SHEET="Accounts"
export GSHEET_LOOKUP_COLUMN="K"
export GSHEET_UPDATE_COLUMN="O"
```

Also set Red Hat and LLM variables (see [QUICKSTART.md](QUICKSTART.md)).

### Ansible Automation Platform

Use the custom credential type in `support_analyzer.cred.yml` (or `controller/credential_types/support_analyzer.spec.yml`). It injects the same environment variables and materializes the service account JSON at job runtime. See [controller/README.md](../controller/README.md).

## 4. Configure accounts

Create `vars/accounts.yml` (gitignored) from the example:

```bash
cp vars/accounts.example.yml vars/accounts.yml
# edit vars/accounts.yml
```

Example:

```yaml
---
support_case_accounts:
  - name: Parasol
    ids: ['12345678']
  - name: Southwest Airlines
    ids: ['647971']
    gsheet_lookup_value: SWA   # optional; defaults to name
```

The lookup value in the sheet must match `gsheet_lookup_value` (or `name` if omitted).

## 5. Run the playbook

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml
```

By default, tasks tagged `never` (markdown/PDF) are skipped. The `json` path runs and updates Google Sheets.

### Markdown or PDF reports

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags pdf
```

Requires `pandoc` and `weasyprint` (see `requirements.txt`).

### Sheets only (skip LLM)

Not recommended for production, but useful for testing connectivity:

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --skip-tags ai
```

## 6. Verify

1. Check playbook output for `Update Google Sheet` (changed).
2. Open the spreadsheet and confirm the update column on the correct row contains JSON.
3. If lookup fails: `lookup_value 'X' not found in column K` — align sheet values with account `name` or `gsheet_lookup_value`.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `google-api-python-client ... required` | `pip install -r requirements.txt` |
| `credentials file not found` | Set `GOOGLE_SA_CRED_PATH` to the JSON key path |
| `Spreadsheet ID required` | Set `GOOGLE_SHEET_ID` |
| `403` / permission errors | Share the sheet with the service account email (Editor) |
| `lookup_value not found` | Match lookup column cell to account name or `gsheet_lookup_value` |
| Empty or stale cell | Re-run with `--tags json`; confirm `--skip-tags ai` was not used unintentionally |

## Module reference

Direct module usage (e.g. in another playbook):

```yaml
- name: Update spreadsheet cell
  gsheet_update:
    sheet: Customers
    lookup_column: A
    lookup_value: "{{ support_case_account_name }}"
    update_column: C
    update_value: "{{ report_json }}"
```

Credentials: `credentials_path` / `GOOGLE_SA_CRED_PATH`, or `credentials` dict from Vault. Spreadsheet: `gsheet_id` / `GOOGLE_SHEET_ID`.

## Related docs

- [EXAMPLES.md](EXAMPLES.md) — account lists, tags, automation
- [QUICKSTART.md](QUICKSTART.md) — Red Hat and LLM setup
- [controller/README.md](../controller/README.md) — Automation Platform credential type

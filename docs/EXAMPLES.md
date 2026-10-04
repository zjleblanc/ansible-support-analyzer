# Usage Examples

This document provides practical examples for using the Ansible Support Analyzer.

## Configuration files

Runtime inputs are usually loaded from `vars/` (see `vars/.gitignore`):

| File | Purpose |
|------|---------|
| `vars/accounts.example.yml` → `vars/accounts.yml` | `support_case_accounts` list |
| `vars/inputs.example.yml` → `vars/inputs.yml` | Legacy single-account vars (optional) |

```bash
cp vars/accounts.example.yml vars/accounts.yml
# edit vars/accounts.yml
```

## Basic Examples

### 1. Single account (legacy variables)

```bash
ansible-playbook analyze_support_cases.yml \
  -e "support_case_account_name=Parasol" \
  -e "support_case_account_ids=['123456']"
```

### 2. Multiple accounts (recommended)

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml
```

Example `vars/accounts.yml`:

```yaml
support_case_accounts:
  - name: Parasol
    ids: ['123456']
  - name: Acme Corp
    ids: ['789012', '345678']
```

### 3. Per-account output path

Override the report path for one account in `vars/accounts.yml`:

```yaml
support_case_accounts:
  - name: Parasol
    ids: ['123456']
    analysis_file_dest: reports/parasol_q4_2024
```

### 4. Google Sheets (JSON output)

Set Google credentials (see [GSUITE_QUICKSTART.md](GSUITE_QUICKSTART.md)), then run:

```bash
export GOOGLE_SA_CRED_PATH="$HOME/.config/support-analyzer/google-sa.json"
export GOOGLE_SHEET_ID="your-spreadsheet-id"
export GSHEET_SHEET="Accounts"
export GSHEET_LOOKUP_COLUMN="K"
export GSHEET_UPDATE_COLUMN="O"

ansible-playbook analyze_support_cases.yml -e @vars/accounts.yml
```

The `json` tag path updates the spreadsheet; lookup defaults to each account `name` unless `gsheet_lookup_value` is set.

### 5. Markdown and PDF reports

Tasks tagged `pdf` are skipped by default. Request them explicitly:

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags pdf
```

Reports are written under `reports/` (or `analysis_file_dest` per account).

## Using Ansible Vault

### With Vault Password Prompt

```bash
ansible-playbook analyze_support_cases.yml \
  --ask-vault-pass \
  -e @vars/accounts.yml
```

### With Vault Password File

```bash
ansible-playbook analyze_support_cases.yml \
  --vault-password-file ~/.ansible/vault_pass.txt \
  -e @vars/accounts.yml
```

## Advanced Examples

### 6. Verbose Output for Debugging

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  -vvv
```

### 7. Skip AI Analysis

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --skip-tags ai
```

### 8. Only Fetch Data

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags fetch,filter
```

### 9. Sheets only (no PDF)

Default run updates Google Sheets and skips markdown/PDF (`never` tag). To avoid Sheets:

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --skip-tags json
```

### 10. Split accounts across runs

```yaml
# vars/accounts-priority.yml
support_case_accounts:
  - name: Tier1 Customer
    ids: ['111111']
```

```bash
ansible-playbook analyze_support_cases.yml -e @vars/accounts-priority.yml
ansible-playbook analyze_support_cases.yml -e @vars/accounts-standard.yml
```

## Automation Examples

### 11. Weekly Automated Report (Crontab)

Add to crontab for weekly Monday morning reports:

```bash
# Edit crontab
crontab -e

# Add this line (runs every Monday at 9 AM)
0 9 * * 1 cd /path/to/ansible-support-analyzer && /usr/bin/ansible-playbook analyze_support_cases.yml -e @vars/accounts.yml >> /var/log/ansible-support-analyzer.log 2>&1
```

### 12. Monthly Report on First of Month

```bash
# Add to crontab (runs at 6 AM on the 1st of each month)
0 6 1 * * cd /path/to/ansible-support-analyzer && /usr/bin/ansible-playbook analyze_support_cases.yml -e @vars/accounts.yml --tags pdf
```

### 13. Shell Script Wrapper

Create a script `run_analysis.sh`:

```bash
#!/bin/bash
# Run support case analysis with error handling

set -e

echo "Running support case analysis..."

ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml

if [ $? -eq 0 ]; then
    echo "Analysis complete!"
    # Optional: send notification
else
    echo "Analysis failed!"
    exit 1
fi
```

## Integration Examples

### 14. Email Report After Generation

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags pdf

# Email the report
mail -s "Red Hat Support Case Analysis" \
  -a reports/latest.md \
  team@company.com < /dev/null
```

### 15. Convert to PDF and Share

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags pdf

# Convert to PDF using pandoc
pandoc reports/analysis.md -o reports/analysis.pdf

# Upload to shared storage
aws s3 cp reports/analysis.pdf s3://company-reports/
```

### 16. Commit to Git Repository

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags pdf

# Commit the report
cd reports
git add $(date +%Y%m%d)_analysis.md
git commit -m "Support case analysis for $(date +%Y-%m-%d)"
git push
```

### 17. Post Summary to Slack

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags pdf

# Extract summary and post to Slack
SUMMARY=$(head -n 50 reports/latest.md)
curl -X POST -H 'Content-type: application/json' \
  --data "{\"text\":\"Support Case Analysis:\n\`\`\`$SUMMARY\`\`\`\"}" \
  YOUR_SLACK_WEBHOOK_URL
```

## Environment-Specific Examples

### Development Environment

```bash
# Use test credentials
export REDHAT_OFFLINE_TOKEN="test-offline-token"
export LLM_API_KEY="test-key"

ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  -vvv
```

### Production Environment

```bash
# Load from secure vault
ansible-playbook analyze_support_cases.yml \
  --vault-password-file /secure/vault_pass \
  -e @vars/accounts.yml \
  --tags pdf
```

## Troubleshooting Examples

### 18. Dry Run with Maximum Verbosity

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --check \
  -vvvv
```

### 19. Test API Connectivity Only

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags fetch \
  --step
```

### 20. Skip Failing Tasks

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --skip-tags ai \
  -v
```

## Performance Examples

### 21. Parallel Account Processing

The playbook processes accounts in sequence by default. For large numbers of accounts, consider splitting into multiple runs:

```bash
# Terminal 1
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts-batch1.yml &

# Terminal 2
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts-batch2.yml &
```

## Tips

- **Account IDs**: Provide as YAML lists under each account’s `ids`
- **Output**: Default run updates Google Sheets (`json` tag); use `--tags pdf` for markdown/PDF under `reports/`
- **Rate limiting**: Be mindful of Red Hat API limits when processing many accounts
- **LLM quotas**: Monitor your LLM provider when analyzing large case volumes
- **Google Sheets**: See [GSUITE_QUICKSTART.md](GSUITE_QUICKSTART.md) for service account setup
- **GraphQL API**: Both playbooks query `https://graphql.redhat.com` via the `graphql_cases`
  module, which filters and paginates server-side. Override the endpoint or Apollo headers via
  `redhat_graphql_url`, `redhat_graphql_client_name`, and `redhat_graphql_client_version`
  in `group_vars/all/vars.yml`.
- **Product filtering**: Use `product_filter` with the GraphQL `like` operator for starts-with
  matching (e.g. `{like: "Red Hat Ansible%"}`). See `library/graphql_cases.py` for all options.

## Tracking Support Case Changes (`track_support_cases.yml`)

`track_support_cases.yml` is a separate, lightweight playbook designed to run as its **own job
template** on a cadence (cron, AAP schedule, etc.). Each run:

1. Reads the tracker sheet **once, for every tracked account at the same time**
   (via `gsheet_tracker state=read`) to retrieve each account's `last_seen_timestamp` from the
   previous run, plus the raw rows belonging to any account *not* in this run (`other_rows`).
2. Per account, queries only non-closed cases modified **since that account's previous run**
   through the GraphQL API (`status_filter`, default `{ne: "Closed"}`, excludes closed cases
   server-side) — avoids re-fetching the entire case history on every cadence tick.
3. Diffs the current cases against what was recorded on the previous run (new / closed /
   changed severity, status, or owner) via `gsheet_tracker state=diff` — a pure local
   computation with **no Google API calls** — and accumulates that account's replacement rows.
4. After every account has been processed, writes the whole tab **exactly once**
   (`gsheet_tracker state=write`: `other_rows` + every account's accumulated rows in a single
   clear+rewrite) — a dedicated worksheet tab that the `gsheet_tracker` module owns completely
   (header row and all data rows). It is *not* the `Accounts` tab used by
   `analyze_support_cases.yml`, and does not rely on that playbook's lookup/update column
   configuration. Treat it as its own green-field tab (default name: `Support Case Tracker`).
   The same step also creates/resizes a Sheets API Table over the tab, named `gsheet_table_name`
   (defaults to the sheet name).
5. Emails a summary of the diff via `community.general.mail` — only when something changed,
   unless `tracker_notify_on_no_changes: true`.

The date cutoff is resolved in order: `tracker_last_run_date` (manual override via `-e`) →
sheet `last_seen_timestamp` → `activity_date` fallback.

No matter how many accounts are tracked, each run makes exactly **one** read and **one** write
against the Google Sheets API (plus one small `batchUpdate` for table maintenance) — not one
read/write pair per account.

No LLM is required for this playbook.

### Credentials

`track_support_cases.yml` leverages the **same credential type definitions** as
`analyze_support_cases.yml` (see [`config/credential_types.yml`](../config/credential_types.yml)),
but as a separate job template it attaches its own, separate credentials:

1. **"Ansible Support Analyzer"** — a *second Credential instance* of the same credential type
   used by `analyze_support_cases.yml` (Red Hat offline token, Google service account JSON,
   `GOOGLE_SHEET_ID`, etc.). Leave `gsheet_sheet` at its default (`Support Case Tracker`) on this
   instance — only the `analyze_support_cases.yml` job template's Credential overrides it to
   `Accounts`.
2. **"SMTP Server"** — also defined in `config/credential_types.yml`, mirrored from
   [ansible-cac's credential_types.yml](https://github.com/zjleblanc/ansible-cac/blob/main/config/common/credential_types.yml).
   Supplies `email_smtp_server`, `email_smtp_server_port`, `email_smtp_username`,
   `email_smtp_password`, and `email_smtp_from_address` as `extra_vars` for the
   change-notification email. Only the tracker job template needs this credential.

No `TRACKER_*` environment variables are used anywhere in this project.

### Setup

```bash
# Collection required for the notification email
ansible-galaxy collection install community.general

# "Ansible Support Analyzer" credential fields (env vars), e.g. for local/CLI runs —
# on AAP these come from a Credential of the type in config/credential_types.yml
export REDHAT_OFFLINE_TOKEN="your-redhat-offline-token"
export GOOGLE_SA_CRED_PATH="$HOME/.config/support-analyzer/google-sa.json"
export GOOGLE_SHEET_ID="your-spreadsheet-id"
# Optional: override the dedicated tracker tab name (default: "Support Case Tracker")
export GSHEET_SHEET="Support Case Tracker"
```

The "SMTP Server" credential type injects `extra_vars`, not environment variables, so for
local/CLI runs pass them with `-e` instead of `export`:

```bash
ansible-playbook track_support_cases.yml \
  -e @vars/accounts.yml \
  -e email_smtp_server="smtp.example.com" \
  -e email_smtp_server_port="587" \
  -e email_smtp_username="notifier@example.com" \
  -e email_smtp_password="..." \
  -e email_smtp_from_address="support-tracker@example.com" \
  -e tracker_smtp_secure="starttls" \
  -e tracker_email_to='["team@example.com","oncall@example.com"]'
```

`tracker_smtp_secure` (optional: `try`|`always`|`never`|`starttls`) and `tracker_email_to` are
plain playbook variables — they are **not** sourced from any credential type, so set them with
`-e` or as extra vars on the job template either way.

### Run once

```bash
ansible-playbook track_support_cases.yml -e @vars/accounts.yml
```

### Run on a cadence (cron)

```bash
# Every 4 hours
0 */4 * * * cd /path/to/ansible-support-analyzer && /usr/bin/ansible-playbook track_support_cases.yml -e @vars/accounts.yml >> /var/log/ansible-case-tracker.log 2>&1
```

### Always send a notification, even with no changes

```bash
ansible-playbook track_support_cases.yml \
  -e @vars/accounts.yml \
  -e tracker_notify_on_no_changes=true
```

### Override the last-run date cutoff

Force the tracker to re-fetch all cases modified since a specific date, ignoring the sheet's
stored `last_seen` timestamp:

```bash
ansible-playbook track_support_cases.yml \
  -e @vars/accounts.yml \
  -e tracker_last_run_date="2026-01-01T00:00:00Z"
```

### What gets written to the sheet

Each run rewrites the entire tracker tab exactly once, with columns:

`Account | Case ID | Summary | Product | Severity | Status | Owner | Created | Last Modified | Last Seen`

Rows for accounts not in this run's `support_case_accounts` list are carried through verbatim
(including any `HYPERLINK` formulas in the Case ID column); rows for every tracked account are
replaced with that account's freshly-diffed rows.

### What the module returns, by state

The `gsheet_tracker` module (see [library/gsheet_tracker.py](../library/gsheet_tracker.py)) has
three states, called in this order once per run:

- **`state: read`** (once, before the account loop) — returns `existing_rows` (the full raw
  matrix, passed into every `diff` call), `other_rows` (untouched accounts' rows, passed into
  the final `write` call), and `accounts` — a dict keyed by account name with
  `last_seen_timestamp` / `total_previous` for each — without writing anything. This powers the
  incremental GraphQL fetch described above.
- **`state: diff`** (once per account, no API calls) — returns `new_cases`, `closed_cases`,
  `updated_cases` (with before/after values for severity, status, and owner), `total_current` /
  `total_previous` counts, and `rows` (that account's freshly-built replacement rows to
  accumulate). These drive both the email template
  ([templates/tracking_email.html.j2](../templates/tracking_email.html.j2)) and the per-account
  debug summary printed during the run.
- **`state: write`** (once, after the account loop) — takes the fully assembled `rows` (every
  account's accumulated rows, concatenated with `other_rows`) and performs the single
  clear+rewrite, plus best-effort Table maintenance (`table_name`).

## Getting Help

For more information:
- Main documentation: [README.md](../README.md)
- Quick start: [QUICKSTART.md](QUICKSTART.md)
- Google Sheets: [GSUITE_QUICKSTART.md](GSUITE_QUICKSTART.md)
- Running on Ansible Automation Platform: [USAGE.md](USAGE.md)
- Open an issue for bugs or questions

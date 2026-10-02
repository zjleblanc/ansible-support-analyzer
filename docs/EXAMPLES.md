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

## Tracking Support Case Changes (`track_support_cases.yml`)

`track_support_cases.yml` is a separate, lightweight playbook designed to run on a cadence
(cron, AAP schedule, etc.). Each run:

1. Queries the same `support_case_accounts` for active support cases.
2. Records them as individual rows in a **dedicated worksheet tab** that the `gsheet_tracker`
   module owns completely (header row and all data rows) — it is *not* the `Accounts` tab used
   by `analyze_support_cases.yml`, and does not rely on that playbook's lookup/update column
   configuration. Treat it as its own green-field tab (default name: `Case Tracker`).
3. Diffs the current cases against what was recorded on the previous run (new / closed /
   changed severity, status, or owner).
4. Emails a summary of the diff via `community.general.mail` — only when something changed,
   unless `tracker_notify_on_no_changes: true`.

No LLM is required for this playbook.

### Setup

```bash
# Collection required for the notification email
ansible-galaxy collection install community.general

# Reuse the same Red Hat + Google Sheets credentials as analyze_support_cases.yml
export REDHAT_OFFLINE_TOKEN="your-redhat-offline-token"
export GOOGLE_SA_CRED_PATH="$HOME/.config/support-analyzer/google-sa.json"
export GOOGLE_SHEET_ID="your-spreadsheet-id"

# Optional: override the dedicated tracker tab name (default: "Case Tracker")
export TRACKER_GSHEET_SHEET="Case Tracker"

# SMTP for the change-notification email
export TRACKER_SMTP_HOST="smtp.example.com"
export TRACKER_SMTP_PORT="587"
export TRACKER_SMTP_USERNAME="notifier@example.com"   # optional
export TRACKER_SMTP_PASSWORD="..."                     # optional
export TRACKER_SMTP_SECURE="starttls"                  # optional: try|always|never|starttls
export TRACKER_EMAIL_FROM="support-tracker@example.com"
export TRACKER_EMAIL_TO="team@example.com,oncall@example.com"
```

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

### What gets written to the sheet

Each run replaces the rows for a given account in the tracker tab (other accounts' rows are
left untouched) with columns:

`Account | Case ID | Summary | Product | Severity | Status | Owner | Created | Last Modified | Last Seen`

### What the module returns per account

The `gsheet_tracker` module (see [library/gsheet_tracker.py](../library/gsheet_tracker.py))
returns `new_cases`, `closed_cases`, `updated_cases` (with before/after values for severity,
status, and owner), plus `total_current` / `total_previous` counts — these drive both the
email template ([templates/tracking_email.html.j2](../templates/tracking_email.html.j2)) and
the per-account debug summary printed during the run.

## Getting Help

For more information:
- Main documentation: [README.md](../README.md)
- Quick start: [QUICKSTART.md](QUICKSTART.md)
- Google Sheets: [GSUITE_QUICKSTART.md](GSUITE_QUICKSTART.md)
- Open an issue for bugs or questions

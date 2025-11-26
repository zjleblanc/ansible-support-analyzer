# Usage Examples

This document provides practical examples for using the Ansible Support Analyzer.

## Basic Examples

### 1. Single Account Analysis

Analyze support cases for one customer account:

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01"
```

### 2. Multiple Accounts

Analyze multiple customer accounts simultaneously:

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456','789012','345678']" \
  -e "activity_date=2024-01-01"
```

### 3. Recent Activity Only

Get cases with activity in the last 30 days:

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=$(date -d '30 days ago' +%Y-%m-%d)"
```

### 4. Last Week's Activity

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=$(date -d '1 week ago' +%Y-%m-%d)"
```

### 5. Custom Output File

Specify where to save the report:

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  -e "output_file=reports/q4_2024_customer_review.md"
```

## Using Ansible Vault

### With Vault Password Prompt

```bash
ansible-playbook analyze_support_cases.yml \
  --ask-vault-pass \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01"
```

### With Vault Password File

```bash
ansible-playbook analyze_support_cases.yml \
  --vault-password-file ~/.ansible/vault_pass.txt \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01"
```

## Advanced Examples

### 6. Verbose Output for Debugging

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  -vvv
```

### 7. Skip AI Analysis (Faster, Basic Report Only)

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  --skip-tags ai
```

### 8. Only Fetch Data (No Report Generation)

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  --tags fetch,filter
```

### 9. Quarterly Report

Generate a report for the entire quarter:

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456','789012']" \
  -e "activity_date=2024-10-01" \
  -e "output_file=reports/Q4_2024_Summary.md"
```

### 10. Multiple Accounts with Different Priorities

```bash
# High-priority accounts
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['111111','222222']" \
  -e "activity_date=2024-11-01" \
  -e "output_file=reports/priority_accounts_nov2024.md"

# Standard accounts
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['333333','444444','555555']" \
  -e "activity_date=2024-11-01" \
  -e "output_file=reports/standard_accounts_nov2024.md"
```

## Automation Examples

### 11. Weekly Automated Report (Crontab)

Add to crontab for weekly Monday morning reports:

```bash
# Edit crontab
crontab -e

# Add this line (runs every Monday at 9 AM)
0 9 * * 1 cd /path/to/ansible-support-analyzer && /usr/bin/ansible-playbook analyze_support_cases.yml -e "customer_account_ids=['123456']" -e "activity_date=$(date -d '7 days ago' +\%Y-\%m-\%d)" -e "output_file=reports/weekly_$(date +\%Y\%m\%d).md" >> /var/log/ansible-support-analyzer.log 2>&1
```

### 12. Monthly Report on First of Month

```bash
# Add to crontab (runs at 6 AM on the 1st of each month)
0 6 1 * * cd /path/to/ansible-support-analyzer && /usr/bin/ansible-playbook analyze_support_cases.yml -e "customer_account_ids=['123456']" -e "activity_date=$(date -d '1 month ago' +\%Y-\%m-\%d)" -e "output_file=reports/monthly_$(date +\%Y\%m).md"
```

### 13. Shell Script Wrapper

Create a script `run_analysis.sh`:

```bash
#!/bin/bash
# Run support case analysis with error handling

set -e

ACCOUNTS="['123456','789012']"
DATE=$(date -d '30 days ago' +%Y-%m-%d)
OUTPUT="reports/analysis_$(date +%Y%m%d).md"

echo "Running support case analysis..."
echo "Accounts: $ACCOUNTS"
echo "Date filter: $DATE"
echo "Output: $OUTPUT"

ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=$ACCOUNTS" \
  -e "activity_date=$DATE" \
  -e "output_file=$OUTPUT"

if [ $? -eq 0 ]; then
    echo "Analysis complete! Report saved to $OUTPUT"
    # Optional: send notification
    # mail -s "Support Analysis Complete" admin@company.com < $OUTPUT
else
    echo "Analysis failed!"
    exit 1
fi
```

## Integration Examples

### 14. Email Report After Generation

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  -e "output_file=reports/latest.md"

# Email the report
mail -s "Red Hat Support Case Analysis" \
  -a reports/latest.md \
  team@company.com < /dev/null
```

### 15. Convert to PDF and Share

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  -e "output_file=reports/analysis.md"

# Convert to PDF using pandoc
pandoc reports/analysis.md -o reports/analysis.pdf

# Upload to shared storage
aws s3 cp reports/analysis.pdf s3://company-reports/
```

### 16. Commit to Git Repository

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  -e "output_file=reports/$(date +%Y%m%d)_analysis.md"

# Commit the report
cd reports
git add $(date +%Y%m%d)_analysis.md
git commit -m "Support case analysis for $(date +%Y-%m-%d)"
git push
```

### 17. Post Summary to Slack

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  -e "output_file=reports/latest.md"

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
export GEMINI_API_KEY="test-key"

ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['999999']" \
  -e "activity_date=2024-01-01" \
  -vvv
```

### Production Environment

```bash
# Load from secure vault
ansible-playbook analyze_support_cases.yml \
  --vault-password-file /secure/vault_pass \
  -e "customer_account_ids=['123456','789012','345678']" \
  -e "activity_date=2024-01-01" \
  -e "output_file=/secure/reports/production_$(date +%Y%m%d).md"
```

## Troubleshooting Examples

### 18. Dry Run with Maximum Verbosity

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  --check \
  -vvvv
```

### 19. Test API Connectivity Only

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  --tags fetch \
  --step
```

### 20. Skip Failing Tasks

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  --skip-tags ai \
  -v
```

## Performance Examples

### 21. Parallel Account Processing

The playbook processes accounts in sequence by default. For large numbers of accounts, consider splitting into multiple runs:

```bash
# Terminal 1
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['111111','222222']" \
  -e "activity_date=2024-01-01" \
  -e "output_file=reports/batch1.md" &

# Terminal 2
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['333333','444444']" \
  -e "activity_date=2024-01-01" \
  -e "output_file=reports/batch2.md" &
```

## Tips

- **Date Format**: Always use `YYYY-MM-DD` format for dates
- **Account IDs**: Must be provided as a list: `['123456']` or `['123456','789012']`
- **Output Directory**: Will be created automatically if it doesn't exist
- **Rate Limiting**: Be mindful of Red Hat API rate limits when processing many accounts
- **API Quotas**: Check your Gemini API quota if processing large numbers of cases

## Getting Help

For more information:
- Main documentation: [README.md](README.md)
- Quick start: [QUICKSTART.md](QUICKSTART.md)
- Open an issue for bugs or questions


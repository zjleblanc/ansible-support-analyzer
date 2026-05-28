# Quick Start Guide

Get up and running with Ansible Support Analyzer in 5 minutes!

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Credentials

Choose one method:

### Method A: Environment Variables (Quickest)

**For local vLLM (recommended - keeps data private):**
```bash
export REDHAT_OFFLINE_TOKEN="your-redhat-offline-token"
export LLM_API_KEY="EMPTY"
export LLM_API_BASE_URL="http://localhost:8000/v1"
export LLM_MODEL="meta-llama/Llama-2-70b-chat-hf"
```

**For OpenAI:**
```bash
export REDHAT_OFFLINE_TOKEN="your-redhat-offline-token"
export LLM_API_KEY="sk-your-openai-key"
export LLM_API_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-4"
```

To get your Red Hat offline token:
1. Visit https://access.redhat.com/management/api
2. Log in with your Red Hat account
3. Click "Generate Token"
4. Copy the offline token and use it as shown above
5. The playbook will automatically exchange this for an access token via Red Hat SSO

### Method B: Ansible Vault (Most Secure)

```bash
# Copy the example vault file
cp group_vars/all/vault.yml.example group_vars/all/vault.yml

# Edit and encrypt it
ansible-vault create group_vars/all/vault.yml
```

Then add your credentials:
```yaml
---
vault_redhat_offline_token: "your-redhat-offline-token"

# For local vLLM (no auth needed)
vault_llm_api_key: "EMPTY"
vault_llm_api_base_url: "http://localhost:8000/v1"
vault_llm_model: "meta-llama/Llama-2-70b-chat-hf"
```

## Step 3: Configure accounts

```bash
cp vars/accounts.example.yml vars/accounts.yml
```

Edit `vars/accounts.yml` with your account display name and Red Hat account number(s):

```yaml
support_case_accounts:
  - name: My Customer
    ids: ['YOUR_ACCOUNT_ID']
```

## Step 4: Run your first analysis

```bash
ansible-playbook analyze_support_cases.yml -e @vars/accounts.yml
```

By default this runs the **Google Sheets / JSON** path (see [GSUITE_QUICKSTART.md](GSUITE_QUICKSTART.md)). Set `GOOGLE_SA_CRED_PATH` and `GOOGLE_SHEET_ID` before running if you use Sheets.

For a local markdown report instead:

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags pdf
```

## Step 5: View output

**Google Sheets:** open your spreadsheet and check the update column for the account row.

**Markdown (with `--tags pdf`):**

```bash
cat reports/*_support_case_summary_*.md
```

## Common Use Cases

### Multiple accounts

Add entries to `vars/accounts.yml` (see `vars/accounts.example.yml`), then:

```bash
ansible-playbook analyze_support_cases.yml -e @vars/accounts.yml
```

### Google Sheets dashboard

See [GSUITE_QUICKSTART.md](GSUITE_QUICKSTART.md) for service account setup, then export:

```bash
export GOOGLE_SA_CRED_PATH="/path/to/service-account.json"
export GOOGLE_SHEET_ID="your-spreadsheet-id"

ansible-playbook analyze_support_cases.yml -e @vars/accounts.yml
```

### PDF / markdown reports

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags pdf
```

## Troubleshooting

### "API credentials not configured"

Make sure you've set either environment variables OR created a vault file.

### "Failed to generate summary"

**For local LLM:** Check server is running: `curl http://localhost:8000/v1/models`

**For OpenAI:** Check your API key is valid and you have quota available.

### "No cases found"

- Verify your account ID is correct
- Try a date further in the past
- Check your Red Hat API credentials have access to the account

## Next Steps

- Read the full [README.md](README.md) for detailed documentation
- Customize the report template in `templates/report.md.j2`
- Adjust AI prompts in `library/llm_summarize.py`
- Set up automated reports with cron

## Getting API Keys

### Red Hat Customer Portal Offline Token
1. Visit https://access.redhat.com/management/api
2. Log in with your Red Hat account
3. Click "Generate Token" button to get an offline token
4. Copy the offline token (it will only be shown once!)
5. Store it securely in your environment variables or vault file

**How it works**: The offline token is a long-lived token that the playbook exchanges for a temporary access token via Red Hat SSO before making API calls. This provides better security as the access tokens are short-lived.

Note: If you don't see the API management page, you may need API access. Contact your Red Hat account team.

### LLM Setup (Choose One)

**Option 1: Local vLLM (Best for Privacy)**
1. Install vLLM: `pip install vllm`
2. Start server:
   ```bash
   python -m vllm.entrypoints.openai.api_server \
     --model meta-llama/Llama-2-70b-chat-hf \
     --port 8000
   ```
3. Use `LLM_API_KEY="EMPTY"` and `LLM_API_BASE_URL="http://localhost:8000/v1"`

**Option 2: Ollama (Easiest Local Setup)**
1. Install from https://ollama.ai/download
2. Start: `ollama serve`
3. Pull model: `ollama pull llama2`
4. Use `LLM_API_KEY="EMPTY"` and `LLM_API_BASE_URL="http://localhost:11434/v1"`

**Option 3: OpenAI (Cloud-based)**
1. Visit https://platform.openai.com/api-keys
2. Create an API key
3. Use your API key and `LLM_API_BASE_URL="https://api.openai.com/v1"`

**See [LLM_CONFIGURATION.md](LLM_CONFIGURATION.md) for detailed setup**

### Google Sheets (optional)
See [GSUITE_QUICKSTART.md](GSUITE_QUICKSTART.md) for service account and spreadsheet sharing steps.

## Support

For issues or questions, please refer to the main [README.md](README.md) or open an issue in the repository.


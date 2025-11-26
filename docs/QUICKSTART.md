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

## Step 3: Run Your First Analysis

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['YOUR_ACCOUNT_ID']" \
  -e "activity_date=2024-01-01"
```

Replace `YOUR_ACCOUNT_ID` with your actual Red Hat customer account number.

## Step 4: View the Report

```bash
cat reports/support_case_summary_*.md
```

## Common Use Cases

### Analyze Multiple Accounts

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456','789012','345678']" \
  -e "activity_date=2024-01-01"
```

### Last 30 Days Only

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=$(date -d '30 days ago' +%Y-%m-%d)"
```

### Custom Report Name

```bash
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  -e "output_file=reports/monthly_review.md"
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
- Adjust AI prompts in `library/gemini_summarize.py`
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

### Google Gemini API
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key and use it in your configuration

## Support

For issues or questions, please refer to the main [README.md](README.md) or open an issue in the repository.


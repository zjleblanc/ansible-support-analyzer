# Ansible Support Analyzer

An Ansible automation project that fetches Red Hat support cases, filters by activity date, and generates intelligent summaries using Google Gemini AI. Perfect for customer success teams, support managers, and technical account managers who need to analyze and report on customer support cases.

## Features

- 🔍 **Multi-Account Support**: Query support cases across multiple customer accounts simultaneously
- 📅 **Activity Filtering**: Filter cases by last activity date to focus on recent issues
- 📊 **Comprehensive Reports**: Generate detailed markdown reports with case breakdowns by severity, product, and status
- 🤖 **AI-Powered Insights**: Use any OpenAI-compatible LLM (vLLM, Ollama, OpenAI, etc.) to identify trends, common issues, and business impacts
- 📋 **Google Sheets**: Optional `gsheet_update` integration to write JSON analysis into a shared spreadsheet
- 🏠 **Local or Cloud LLMs**: Deploy LLMs locally with vLLM/Ollama for privacy, or use cloud APIs like OpenAI
- 🔐 **Secure Authentication**: OAuth 2.0 via Red Hat SSO with offline token support
- 🔒 **Credential Protection**: Support for both environment variables and Ansible Vault encryption
- 📈 **Product Analysis**: Automatic grouping and analysis by Red Hat product

## Prerequisites

- Python 3.8 or higher
- Ansible 2.15 or higher
- Red Hat Customer Portal API credentials
- LLM API (one of):
  - Local vLLM server (recommended for privacy)
  - Local Ollama server
  - OpenAI API key
  - Any OpenAI-compatible API

## Installation

1. **Clone the repository**:
```bash
git clone <repository-url>
cd ansible-support-analyzer
```

2. **Install Python dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure credentials** (choose one method):

   **Option A: Environment Variables (Recommended for CI/CD)**
   
   **For local vLLM:**
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
   - Visit https://access.redhat.com/management/api
   - Click "Generate Token" to create an offline token
   - Copy the offline token (it will be exchanged for an access token automatically via Red Hat SSO)

   **Option B: Ansible Vault (Recommended for Team Use)**
   ```bash
   # Create vault file from example
   cp group_vars/all/vault.yml.example group_vars/all/vault.yml
   
   # Edit with your credentials
   ansible-vault edit group_vars/all/vault.yml
   
   # Create vault password file (optional)
   echo "your-vault-password" > ~/.ansible/vault_pass.txt
   chmod 600 ~/.ansible/vault_pass.txt
   ```

## Usage

See [docs/EXAMPLES.md](docs/EXAMPLES.md) for detailed examples and [docs/QUICKSTART.md](docs/QUICKSTART.md) for a five-minute setup.

### Basic usage

```bash
cp vars/accounts.example.yml vars/accounts.yml
# edit vars/accounts.yml

ansible-playbook analyze_support_cases.yml -e @vars/accounts.yml
```

### Multiple accounts

Define `support_case_accounts` in `vars/accounts.yml` (one playbook run processes each entry). See `vars/accounts.example.yml`.

### Google Sheets output

Push JSON reports into a shared spreadsheet with a Google service account. See [docs/GSUITE_QUICKSTART.md](docs/GSUITE_QUICKSTART.md).

### Markdown / PDF reports

```bash
ansible-playbook analyze_support_cases.yml \
  -e @vars/accounts.yml \
  --tags pdf
```

### With Vault Password

If using Ansible Vault without a password file:

```bash
ansible-playbook analyze_support_cases.yml \
  --ask-vault-pass \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01"
```

### Using Tags

Run specific parts of the playbook:

```bash
# Only fetch data (skip AI analysis)
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  --tags fetch,filter,report

# Only run AI analysis (assumes data already fetched)
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  --tags ai,report
```

## Configuration

### Default Variables

Edit `group_vars/all/vars.yml` to customize default behavior:

```yaml
# API configuration
redhat_api_base_url: "https://api.access.redhat.com/rs"
redhat_api_timeout: 30

# Output configuration
default_output_file: "reports/support_case_summary_{{ ansible_date_time.date }}.md"

# Gemini AI configuration
gemini_model: "gemini-pro"
gemini_temperature: 0.7
gemini_max_tokens: 2048
```

### Ansible Configuration

The `ansible.cfg` file includes sensible defaults. Modify as needed:

```ini
[defaults]
inventory = inventory
stdout_callback = yaml
vault_identity_list = default@~/.ansible/vault_pass.txt
```

## Project Structure

```
ansible-support-analyzer/
├── analyze_support_cases.yml    # Main playbook
├── ansible.cfg                  # Ansible configuration
├── inventory                    # Inventory file (localhost)
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
├── README.md                    # This file
│
├── group_vars/
│   └── all/
│       ├── vars.yml            # Default variables
│       └── vault.yml.example   # Vault template
│
├── templates/
│   └── report.md.j2            # Report template
│
├── library/
│   └── gemini_summarize.py     # Custom Gemini AI module
│
└── reports/                     # Generated reports (created automatically)
```

## Report Output

The generated markdown report includes:

1. **Executive Summary**: High-level statistics and severity breakdown
2. **Customer Account Overview**: Cases grouped by account with detailed tables
3. **Product Breakdown**: Cases organized by Red Hat product
4. **Detailed Case Information**: Full details for each case
5. **AI-Generated Insights**: Gemini AI analysis including:
   - High-level overview of support situation
   - Most impacted products
   - Common issues and trends
   - Projects and business impact analysis
   - Severity distribution insights
   - Recommendations for improvement

## API Requirements

### Red Hat Customer Portal API

- **Authentication**: OAuth 2.0 via Red Hat SSO (offline token → access token exchange)
- **SSO Endpoint**: `https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token`
- **API Endpoint**: `https://api.access.redhat.com/rs/cases`
- **Permissions**: Read access to customer support cases
- **Get Offline Token**: Visit https://access.redhat.com/management/api to generate an offline token
- **Token Flow**: The playbook automatically exchanges your offline token for a temporary access token via Red Hat SSO
- **Documentation**: [Red Hat API Documentation](https://access.redhat.com/documentation/en-us/red_hat_customer_portal/1/html/red_hat_customer_portal_api_guide/index)

### LLM API (Choose One)

**Option 1: Local vLLM (Recommended for Privacy)**
- **Installation**: `pip install vllm`
- **Start Server**: `python -m vllm.entrypoints.openai.api_server --model meta-llama/Llama-2-70b-chat-hf --port 8000`
- **API Endpoint**: `http://localhost:8000/v1`
- **Authentication**: Not required (use `LLM_API_KEY="EMPTY"`)
- **Documentation**: [vLLM Documentation](https://vllm.readthedocs.io/)

**Option 2: Ollama**
- **Installation**: [Ollama Download](https://ollama.ai/download)
- **Start Server**: `ollama serve`
- **Pull Model**: `ollama pull llama2`
- **API Endpoint**: `http://localhost:11434/v1`
- **Authentication**: Not required
- **Documentation**: [Ollama Documentation](https://ollama.ai/docs)

**Option 3: OpenAI**
- **Authentication**: API key
- **API Endpoint**: `https://api.openai.com/v1`
- **Get API Key**: [OpenAI Platform](https://platform.openai.com/api-keys)
- **Models**: `gpt-3.5-turbo`, `gpt-4`, etc.
- **Documentation**: [OpenAI API Reference](https://platform.openai.com/docs/api-reference)

**See [LLM_CONFIGURATION.md](LLM_CONFIGURATION.md) for detailed setup instructions**

## Troubleshooting

### Missing Python Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### API Authentication Errors

1. Verify credentials are correct
2. Check environment variables are set
3. Ensure vault file is properly encrypted and accessible

```bash
# Test vault file
ansible-vault view group_vars/all/vault.yml
```

### No Cases Found

- Verify customer account IDs are correct
- Check the activity_date filter isn't too restrictive
- Ensure the Red Hat API credentials have access to these accounts

### LLM API Errors

**Local vLLM/Ollama:**
- Verify the LLM server is running: `curl http://localhost:8000/v1/models`
- Check server logs for errors
- Ensure sufficient VRAM for your model

**OpenAI:**
- Verify your API key is valid
- Check your API quota at [OpenAI Platform](https://platform.openai.com/)
- Ensure `requests` Python package is installed

### Permission Errors on Reports Directory

```bash
mkdir -p reports
chmod 755 reports
```

## Example Workflow

Here's a complete workflow example:

```bash
# 1. Set up environment
export REDHAT_OFFLINE_TOKEN="your-redhat-offline-token"
export LLM_API_KEY="EMPTY"
export LLM_API_BASE_URL="http://localhost:8000/v1"
export LLM_MODEL="meta-llama/Llama-2-70b-chat-hf"

# 2. Run analysis for multiple accounts
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456','789012']" \
  -e "activity_date=2024-11-01" \
  -e "output_file=reports/november_2024_review.md"

# 3. View the report
cat reports/november_2024_review.md
```

## Advanced Usage

### Custom Gemini Prompts

Modify `library/gemini_summarize.py` to customize the AI prompt for your specific needs.

### Scheduling with Cron

Run automated weekly reports:

```bash
# Add to crontab
0 9 * * 1 cd /path/to/ansible-support-analyzer && ansible-playbook analyze_support_cases.yml -e "customer_account_ids=['123456']" -e "activity_date=$(date -d '7 days ago' +\%Y-\%m-\%d)"
```

### Integration with Other Tools

The generated markdown reports can be:
- Converted to PDF using pandoc
- Committed to git for version control
- Sent via email using `mail` command
- Posted to Slack or other collaboration tools

## Security Best Practices

1. **Never commit credentials to git**
   - Use `.gitignore` to exclude vault files and environment files
   - Use Ansible Vault for sensitive data

2. **Rotate API keys regularly**
   - Red Hat API credentials
   - Gemini API keys

3. **Restrict file permissions**
   ```bash
   chmod 600 group_vars/all/vault.yml
   chmod 600 ~/.ansible/vault_pass.txt
   ```

4. **Use read-only API credentials when possible**

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## License

GNU General Public License v3.0 or later

See [LICENSE](LICENSE) for the full license text.

## Support

For issues and questions:
- Open an issue on the project repository
- Check the troubleshooting section above
- Review Red Hat API documentation for API-related questions

## Changelog

### Version 1.0.0 (Initial Release)
- Multi-account support case fetching
- Date-based activity filtering
- Markdown report generation
- Gemini AI integration for intelligent insights
- Secure credential management
- Comprehensive documentation

## Acknowledgments

- Red Hat for providing the Customer Portal API
- Google for the Gemini AI API
- The Ansible community for excellent automation tools

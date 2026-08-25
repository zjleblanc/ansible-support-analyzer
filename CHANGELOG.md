# Changelog

All notable changes to the Ansible Support Analyzer project will be documented in this file.

## [1.5.0] - 2026-08-25

### Added
- **Smart JSON truncation**: The `gsheet_update` module now proactively shortens text fields (descriptions and summaries) to fit the Google Sheets 50,000-character single-cell limit.
- **Schema-safe implementation**: Truncation only modifies string values; it never deletes keys, removes array elements, or adds new metadata to the JSON payload, ensuring downstream consumers aren't broken.
- **Priority-aware trimming**: Case data for specific products (defaulting to "Red Hat Ansible Automation Platform") is preserved longest during the truncation cascade.
- **Truncation metadata**: Module returns `truncated` (bool), `original_chars` (int), and `final_chars` (int) to the Ansible result for visibility.
- **New module parameters**: Added `truncate`, `truncate_priority_products`, and `max_cell_chars` to the `gsheet_update` module for fine-grained control.
- **Centrally managed priority**: `gsheet_truncate_priority_products` variable added to `group_vars/all/vars.yml`.

### Changed
- **Truncation warnings**: The report generation workflow now includes a warning task that triggers when a Google Sheets report has been shortened, directing users to the full Markdown/PDF reports.

## [1.4.0] - 2026-05-28

### Added
- **Default activity date filter**: `default_activity_date` in `group_vars/all/vars.yml` sets a 6-month lookback from the run date using the `now()` Jinja filter (no `gather_facts` required)
- **Activity date filtering**: Cases are filtered by `lastModifiedDate >= activity_date` in `tasks/analyze_account.yml`
- **Google Sheets integration**: New `gsheet_update` module updates a spreadsheet row by lookup column/value
- **JSON report output**: `templates/report.json.j2` produces minified JSON for sheet cells (tag: `json`)
- **Multi-account batch runs**: `support_case_accounts` list with per-account `name`, `ids`, and optional overrides
- **Task refactor**: Per-account workflow in `tasks/analyze_account.yml` (included from main playbook)
- **Ansible Automation Platform**: Custom credential type (`support_analyzer.cred.yml`, `controller/`) injects Red Hat, LLM, and Google credentials
- **Google API dependencies**: `google-api-python-client`, `google-auth`, and related packages in `requirements.txt`
- **Documentation**: [docs/GSUITE_QUICKSTART.md](docs/GSUITE_QUICKSTART.md) for Google Cloud and Sheets setup

### Fixed
- **`gsheet_update` on Automation Platform**: Serialize dict/list `update_value` payloads to JSON text before writing to Google Sheets, fixing `Invalid values... struct_value` when the controller parses rendered report JSON as a Python object

### Changed
- Main playbook sets `activity_date` from `default_activity_date`; override with `-e activity_date=YYYY-MM-DD` or per-account `activity_date`
- Main playbook loops `support_case_accounts` instead of inlining fetch/analyze tasks
- Legacy single-account variables (`support_case_account_name` + `support_case_account_ids`) still supported
- **Tag-based outputs**: `json` (default) writes to Google Sheets; `pdf` generates markdown/HTML/PDF reports
- `llm_summarize` accepts optional `format_instructions` (e.g. HTML for PDF pipeline)
- `vars/inputs.example.yml` updated for current variable names; documents optional `activity_date` override

### Environment Variables (Google Sheets)

| Variable | Purpose |
|----------|---------|
| `GOOGLE_SA_CRED_PATH` | Path to service account JSON key file |
| `GOOGLE_SHEET_ID` | Spreadsheet ID from the Google Sheets URL |
| `GSHEET_SHEET` | Worksheet name (default: `Accounts` in Controller credential) |
| `GSHEET_LOOKUP_COLUMN` | Column letter to find the account row |
| `GSHEET_UPDATE_COLUMN` | Column letter to write the JSON report |

Per-account `gsheet_lookup_value` defaults to the account `name` when not set on the account dict.

## [1.3.0] - 2024-11-21

### Changed - Breaking Changes
- **Generic LLM Support**: Replaced Google Gemini-specific implementation with generic OpenAI-compatible API support
  - Now supports vLLM, Ollama, LocalAI, OpenAI, and any OpenAI-compatible endpoint
  - Module renamed: `gemini_summarize` → `llm_summarize`
  - Variables renamed:
    - `gemini_api_key` → `llm_api_key`
    - `gemini_model` → `llm_model`
    - `gemini_temperature` → `llm_temperature`
    - `gemini_max_tokens` → `llm_max_tokens`
  - Added new variable: `llm_api_base_url` (required)
  - Added new variable: `llm_timeout` (default: 120 seconds)

### Added
- Support for local LLM deployment with vLLM
- Support for Ollama, LocalAI, and other OpenAI-compatible APIs
- `llm_summarize.py` - New generic module with OpenAI-compatible API
- `LLM_CONFIGURATION.md` - Comprehensive guide for LLM setup and deployment
- Configurable API timeout for slow/large models
- Better privacy: data never leaves your network when using local LLMs

### Removed
- `gemini_summarize.py` - Replaced by generic `llm_summarize.py`
- `google-generativeai` dependency - No longer required
- Gemini-specific configuration variables

### Migration Guide

**If you're upgrading from version 1.2.0:**

1. **Update environment variables**:
   ```bash
   # Old (v1.2.0)
   export GEMINI_API_KEY="your-gemini-key"
   
   # New (v1.3.0) - Local vLLM
   export LLM_API_KEY="EMPTY"
   export LLM_API_BASE_URL="http://localhost:8000/v1"
   export LLM_MODEL="meta-llama/Llama-2-70b-chat-hf"
   
   # Or for OpenAI
   export LLM_API_KEY="sk-..."
   export LLM_API_BASE_URL="https://api.openai.com/v1"
   export LLM_MODEL="gpt-4"
   ```

2. **Update vault file** (if using Ansible Vault):
   ```bash
   ansible-vault edit group_vars/all/vault.yml
   ```
   
   Replace:
   ```yaml
   # Old
   vault_gemini_api_key: "your-gemini-key"
   
   # New
   vault_llm_api_key: "EMPTY"  # or your API key
   vault_llm_api_base_url: "http://localhost:8000/v1"
   vault_llm_model: "meta-llama/Llama-2-70b-chat-hf"
   ```

3. **Update Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start your LLM server** (if using local deployment):
   ```bash
   # For vLLM
   python -m vllm.entrypoints.openai.api_server \
     --model meta-llama/Llama-2-70b-chat-hf \
     --port 8000
   
   # Or for Ollama
   ollama serve
   ollama pull llama2
   ```

5. **Test the updated configuration**:
   ```bash
   ansible-playbook analyze_support_cases.yml \
     -e "customer_account_ids=['123456']" \
     -e "activity_date=2024-01-01"
   ```

### Benefits

- **Privacy**: Run LLMs entirely on your infrastructure
- **Cost**: No per-request API fees with local deployment
- **Flexibility**: Use any OpenAI-compatible LLM provider
- **Control**: Full control over model selection and configuration
- **Performance**: Optimize for your specific hardware

## [1.2.0] - 2024-11-21

### Changed
- **Fully Qualified Collection Names (FQCNs)**: Updated all module references in the playbook to use FQCNs
  - `assert` → `ansible.builtin.assert`
  - `debug` → `ansible.builtin.debug`
  - `file` → `ansible.builtin.file`
  - `uri` → `ansible.builtin.uri`
  - `set_fact` → `ansible.builtin.set_fact`
  - `template` → `ansible.builtin.template`
  - This follows Ansible best practices and ensures compatibility across different Ansible environments

### Benefits
- **Better Compatibility**: Avoids module name conflicts in environments with multiple collections
- **Future Proof**: Aligns with Ansible best practices and recommendations
- **Explicit Dependencies**: Makes it clear which collection each module comes from
- **Improved Maintainability**: Easier to identify module sources and versions

## [1.1.0] - 2024-11-21

### Changed - Breaking Changes
- **Authentication Method Updated**: Switched from basic authentication (username/password) to OAuth 2.0 via Red Hat SSO
  - Now uses offline token instead of username/password
  - Automatically exchanges offline token for temporary access token
  - Improved security with short-lived access tokens

### Added
- Red Hat SSO integration for token-based authentication
- Automatic offline token to access token exchange
- `SSO_AUTHENTICATION.md` - Comprehensive guide for SSO authentication
- Token expiration logging
- Support for Red Hat's OAuth 2.0 refresh token flow

### Updated
- `analyze_support_cases.yml`: Added SSO token exchange task
- `group_vars/all/vars.yml`: Changed from `redhat_api_username/password` to `redhat_offline_token`
- `group_vars/all/vault.yml.example`: Updated with offline token configuration
- Documentation updated across all files:
  - README.md
  - QUICKSTART.md
  - EXAMPLES.md
  - IMPLEMENTATION_SUMMARY.md

### Migration Guide

**If you're upgrading from version 1.0.0:**

1. **Get an offline token**:
   - Visit https://access.redhat.com/management/api
   - Click "Generate Token"
   - Copy the offline token

2. **Update environment variables**:
   ```bash
   # Old (v1.0.0)
   export REDHAT_API_USERNAME="your-username"
   export REDHAT_API_PASSWORD="your-password"
   
   # New (v1.1.0)
   export REDHAT_OFFLINE_TOKEN="your-offline-token"
   ```

3. **Update vault file** (if using Ansible Vault):
   ```bash
   ansible-vault edit group_vars/all/vault.yml
   ```
   
   Replace:
   ```yaml
   # Old
   vault_redhat_api_username: "username"
   vault_redhat_api_password: "password"
   
   # New
   vault_redhat_offline_token: "offline-token"
   ```

4. **Test the updated authentication**:
   ```bash
   ansible-playbook analyze_support_cases.yml \
     -e "customer_account_ids=['123456']" \
     -e "activity_date=2024-01-01"
   ```

### Technical Details

**New SSO Endpoint**: `https://sso.redhat.com/auth/realms/redhat-external/protocol/openid-connect/token`

**Authentication Flow**:
1. Playbook receives offline token (from env var or vault)
2. Playbook sends offline token to Red Hat SSO
3. SSO returns temporary access token (typically expires in 5 minutes)
4. Playbook uses access token for all API requests

**Security Improvements**:
- Access tokens are short-lived (improved security)
- No password storage required
- Tokens can be revoked from Red Hat portal
- Offline tokens are long-lived but can be rotated easily

## [1.0.0] - 2024-11-21

### Added
- Initial release
- Multi-account support case analysis
- Date-based activity filtering
- Markdown report generation
- Google Gemini AI integration
- Ansible Vault support for credentials
- Comprehensive documentation
- 20+ usage examples


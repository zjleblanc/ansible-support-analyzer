# LLM Configuration Guide

## Overview

The Ansible Support Analyzer now supports **any OpenAI-compatible LLM API**, including:
- **vLLM** - High-performance LLM serving (local or remote)
- **Ollama** - Local LLM deployment
- **LocalAI** - Self-hosted OpenAI alternative
- **OpenAI** - Cloud-based GPT models
- **Azure OpenAI** - Enterprise OpenAI deployment
- Any other service with OpenAI-compatible `/v1/chat/completions` endpoint

## Quick Start

### Option 1: Local vLLM (Recommended for Privacy)

```bash
# 1. Install vLLM
pip install vllm

# 2. Start vLLM server with your model
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --host 0.0.0.0 \
  --port 8000

# 3. Configure Ansible playbook
export REDHAT_OFFLINE_TOKEN="your-redhat-token"
export LLM_API_KEY="EMPTY"
export LLM_API_BASE_URL="http://localhost:8000/v1"
export LLM_MODEL="meta-llama/Llama-2-70b-chat-hf"

# 4. Run analysis
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01"
```

### Option 2: Ollama

```bash
# 1. Install and start Ollama
ollama serve

# 2. Pull a model
ollama pull llama2

# 3. Configure
export LLM_API_KEY="EMPTY"
export LLM_API_BASE_URL="http://localhost:11434/v1"
export LLM_MODEL="llama2"

# 4. Run analysis
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01"
```

### Option 3: OpenAI

```bash
# Configure
export LLM_API_KEY="sk-your-openai-api-key"
export LLM_API_BASE_URL="https://api.openai.com/v1"
export LLM_MODEL="gpt-4"

# Run analysis
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01"
```

## Configuration Options

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key (use "EMPTY" for local deployments without auth) | `"EMPTY"` or `"sk-..."` |
| `LLM_API_BASE_URL` | Base URL for LLM API | `"http://localhost:8000/v1"` |
| `LLM_MODEL` | Model name | `"meta-llama/Llama-2-70b-chat-hf"` |

### Ansible Vault

Edit `group_vars/all/vault.yml`:

```yaml
---
vault_redhat_offline_token: "your-redhat-token"

# For local vLLM
vault_llm_api_key: "EMPTY"
vault_llm_api_base_url: "http://localhost:8000/v1"
vault_llm_model: "meta-llama/Llama-2-70b-chat-hf"

# For OpenAI
# vault_llm_api_key: "sk-..."
# vault_llm_api_base_url: "https://api.openai.com/v1"
# vault_llm_model: "gpt-4"
```

### Additional Parameters

Configure in `group_vars/all/vars.yml`:

```yaml
llm_temperature: 0.7          # Creativity (0.0-1.0)
llm_max_tokens: 2048         # Maximum response length
llm_timeout: 120             # Request timeout in seconds
```

## vLLM Deployment Guide

### Local Deployment

#### Prerequisites
- NVIDIA GPU (recommended: A100, H100, or multiple V100s)
- CUDA 11.8+
- Python 3.8+
- 40GB+ VRAM for 70B models, 20GB+ for 13B models

#### Installation

```bash
# Install vLLM
pip install vllm

# Or with specific CUDA version
pip install vllm --extra-index-url https://download.pytorch.org/whl/cu118
```

#### Start Server

**Basic:**
```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --host 0.0.0.0 \
  --port 8000
```

**With Tensor Parallelism (multiple GPUs):**
```bash
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --tensor-parallel-size 4 \
  --host 0.0.0.0 \
  --port 8000
```

**With Quantization (lower memory):**
```bash
python -m vllm.entrypoints.openai.api_server \
  --model TheBloke/Llama-2-70B-chat-AWQ \
  --quantization awq \
  --host 0.0.0.0 \
  --port 8000
```

### Remote vLLM Deployment

If running vLLM on a remote server:

```bash
# On remote server
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --host 0.0.0.0 \
  --port 8000

# On Ansible control machine
export LLM_API_BASE_URL="http://your-server:8000/v1"
```

### Docker Deployment

```bash
# Pull vLLM image
docker pull vllm/vllm-openai:latest

# Run with GPU support
docker run --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 8000:8000 \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-70b-chat-hf
```

## Recommended Models

### For Support Case Analysis

| Model | Size | VRAM | Quality | Speed | Use Case |
|-------|------|------|---------|-------|----------|
| Llama-2-70B-chat | 70B | 140GB | Excellent | Slow | Best quality, production |
| Llama-2-13B-chat | 13B | 26GB | Good | Fast | Development, testing |
| Mistral-7B-Instruct | 7B | 14GB | Good | Very Fast | Quick analysis |
| GPT-4 (OpenAI) | - | N/A | Excellent | Medium | Cloud-based option |
| GPT-3.5-turbo (OpenAI) | - | N/A | Good | Fast | Cost-effective cloud |

### Model Selection Guide

**For Production (High Quality):**
- Llama-2-70B-chat-hf
- GPT-4 (if using OpenAI)

**For Development/Testing:**
- Llama-2-13B-chat-hf
- Mistral-7B-Instruct-v0.2

**For Budget/Speed:**
- Llama-2-7B-chat-hf
- GPT-3.5-turbo (if using OpenAI)

## Performance Tuning

### vLLM Optimization

```bash
# Increase batch size for better throughput
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --max-num-seqs 32 \
  --host 0.0.0.0 \
  --port 8000

# Use PagedAttention for better memory efficiency
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --block-size 16 \
  --host 0.0.0.0 \
  --port 8000
```

### Playbook Optimization

Adjust timeouts for slower models:

```yaml
# In group_vars/all/vars.yml
llm_timeout: 300  # 5 minutes for large models
```

## Troubleshooting

### Connection Issues

**Error: "Connection refused"**

```bash
# Check if vLLM is running
curl http://localhost:8000/v1/models

# Expected response
{"object":"list","data":[{"id":"meta-llama/Llama-2-70b-chat-hf",...}]}
```

**Error: "Request timeout"**

Increase timeout:
```bash
export LLM_TIMEOUT=300
```

Or in vault:
```yaml
vault_llm_timeout: 300
```

### Model Issues

**Error: "Model not found"**

Check available models:
```bash
curl http://localhost:8000/v1/models
```

Use exact model name from response.

**Error: "Out of memory"**

Options:
1. Use quantized model (AWQ, GPTQ)
2. Reduce batch size
3. Use smaller model
4. Add more GPUs with tensor parallelism

### Authentication Issues

**Local vLLM** doesn't require authentication. Use:
```bash
export LLM_API_KEY="EMPTY"
```

**OpenAI** requires valid API key:
```bash
export LLM_API_KEY="sk-..."
```

## Security Considerations

### Local Deployment (vLLM, Ollama)

**Advantages:**
- ✅ Data never leaves your network
- ✅ No API rate limits
- ✅ No per-request costs
- ✅ Full control over models

**Security:**
- Ensure vLLM server is not exposed to internet
- Use firewall rules to restrict access
- Consider VPN for remote access

### Cloud Deployment (OpenAI, etc.)

**Considerations:**
- ⚠️ Data sent to third-party API
- ⚠️ Subject to terms of service
- ⚠️ Potential compliance concerns
- ✅ No infrastructure maintenance
- ✅ Always up-to-date models

**Mitigation:**
- Review data sensitivity
- Check compliance requirements (GDPR, HIPAA, etc.)
- Consider data anonymization
- Use Azure OpenAI for enterprise compliance

## Example Configurations

### Configuration 1: High-Performance Local

```yaml
# group_vars/all/vars.yml
vault_llm_api_key: "EMPTY"
vault_llm_api_base_url: "http://localhost:8000/v1"
vault_llm_model: "meta-llama/Llama-2-70b-chat-hf"
llm_temperature: 0.7
llm_max_tokens: 2048
llm_timeout: 180
```

### Configuration 2: Fast Local Development

```yaml
# group_vars/all/vars.yml
vault_llm_api_key: "EMPTY"
vault_llm_api_base_url: "http://localhost:8000/v1"
vault_llm_model: "mistralai/Mistral-7B-Instruct-v0.2"
llm_temperature: 0.7
llm_max_tokens: 1500
llm_timeout: 60
```

### Configuration 3: OpenAI Cloud

```yaml
# group_vars/all/vars.yml
vault_llm_api_key: "sk-your-api-key"
vault_llm_api_base_url: "https://api.openai.com/v1"
vault_llm_model: "gpt-4"
llm_temperature: 0.7
llm_max_tokens: 2048
llm_timeout: 120
```

### Configuration 4: Azure OpenAI Enterprise

```yaml
# group_vars/all/vars.yml
vault_llm_api_key: "your-azure-api-key"
vault_llm_api_base_url: "https://your-resource.openai.azure.com/openai/deployments/your-deployment"
vault_llm_model: "gpt-4"
llm_temperature: 0.7
llm_max_tokens: 2048
llm_timeout: 120
```

## Testing Your Configuration

### Test vLLM Server

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-2-70b-chat-hf",
    "messages": [{"role": "user", "content": "Hello!"}],
    "max_tokens": 50
  }'
```

### Test with Ansible Playbook

```bash
# Run with minimal data for testing
ansible-playbook analyze_support_cases.yml \
  -e "customer_account_ids=['123456']" \
  -e "activity_date=2024-01-01" \
  --tags ai \
  -vvv
```

## Resources

### Documentation
- [vLLM Documentation](https://vllm.readthedocs.io/)
- [Ollama Documentation](https://ollama.ai/docs)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [HuggingFace Models](https://huggingface.co/models)

### Model Repositories
- [Llama 2 Models](https://huggingface.co/meta-llama)
- [Mistral Models](https://huggingface.co/mistralai)
- [Quantized Models by TheBloke](https://huggingface.co/TheBloke)

### Tools
- [vLLM GitHub](https://github.com/vllm-project/vllm)
- [Ollama GitHub](https://github.com/jmorganca/ollama)
- [LM Studio](https://lmstudio.ai/) - GUI for local LLMs

---

**Version**: 1.3.0  
**Status**: ✅ Tested with vLLM, Ollama, and OpenAI


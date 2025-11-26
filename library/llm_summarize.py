#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Ansible Support Analyzer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: llm_summarize
short_description: Summarize support case data using any OpenAI-compatible LLM API
version_added: "1.3.0"
description:
    - This module sends support case data to any OpenAI-compatible LLM API for intelligent summarization
    - Supports vLLM, Ollama, LocalAI, OpenAI, Azure OpenAI, and other compatible endpoints
    - Extracts insights about customer issues, affected products, and impacted projects
    - Returns formatted summary for inclusion in reports
author:
    - Ansible Support Analyzer
options:
    api_key:
        description:
            - API key for authentication (use "EMPTY" for local deployments without auth)
        required: true
        type: str
    api_base_url:
        description:
            - Base URL for the LLM API (e.g., http://localhost:8000/v1)
        required: true
        type: str
    case_data:
        description:
            - Dictionary containing support case information to analyze
        required: true
        type: dict
    model:
        description:
            - Model name to use for generation
        required: false
        type: str
        default: 'gpt-3.5-turbo'
    temperature:
        description:
            - Temperature for text generation (0.0-1.0)
        required: false
        type: float
        default: 0.7
    max_tokens:
        description:
            - Maximum tokens for response
        required: false
        type: int
        default: 2048
    timeout:
        description:
            - Request timeout in seconds
        required: false
        type: int
        default: 120
'''

EXAMPLES = r'''
# vLLM example
- name: Generate AI summary with vLLM
  llm_summarize:
    api_key: "EMPTY"
    api_base_url: "http://localhost:8000/v1"
    case_data:
      total_cases: 15
      accounts: ['123456', '789012']
      cases: "{{ all_cases }}"
    model: "meta-llama/Llama-2-70b-chat-hf"
    temperature: 0.7
    timeout: 180
  register: ai_summary

# OpenAI example
- name: Generate AI summary with OpenAI
  llm_summarize:
    api_key: "{{ openai_api_key }}"
    api_base_url: "https://api.openai.com/v1"
    case_data:
      total_cases: 15
      accounts: ['123456', '789012']
      cases: "{{ all_cases }}"
    model: "gpt-4"
    temperature: 0.7
  register: ai_summary

# Ollama example
- name: Generate AI summary with Ollama
  llm_summarize:
    api_key: "EMPTY"
    api_base_url: "http://localhost:11434/v1"
    case_data:
      total_cases: 15
      accounts: ['123456']
      cases: "{{ all_cases }}"
    model: "llama2"
    temperature: 0.7
  register: ai_summary
'''

RETURN = r'''
summary:
    description: AI-generated summary of the support cases
    type: str
    returned: always
    sample: |
        ### Overview
        Analysis reveals 15 active support cases across 2 customer accounts...
insights:
    description: Structured insights extracted from the analysis
    type: dict
    returned: always
    sample:
        top_products: ["Red Hat Enterprise Linux", "OpenShift"]
        common_issues: ["Performance degradation", "Configuration problems"]
model_used:
    description: The model that was used for generation
    type: str
    returned: always
    sample: "meta-llama/Llama-2-70b-chat-hf"
'''

from ansible.module_utils.basic import AnsibleModule
import json

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


def build_prompt(case_data):
    """Build a comprehensive prompt for LLM analysis."""
    
    total_cases = len(case_data.get('cases', []))
    accounts = case_data.get('accounts', [])
    cases = case_data.get('cases', [])
    
    # Build case summary for prompt
    case_summaries = []
    for case in cases[:50]:  # Limit to first 50 cases to avoid token limits
        case_summaries.append(
            f"- Case {case.get('caseNumber')}: {case.get('summary')}, {case.get('description')} "
            f"[Product: {case.get('product')}, Severity: {case.get('severity')}, "
            f"Urgency {case.get('timeFramesAndUrgency')}, Status: {case.get('status')}]"
        )
    
    prompt = f"""You are an expert technical analyst reviewing Red Hat support cases for enterprise customers.

Analyze the following support case data and provide a comprehensive executive summary:

**Case Statistics:**
- Total Cases: {total_cases}
- Customer Accounts: {len(accounts)}

**Cases:**
{chr(10).join(case_summaries)}

Please provide:

- **High-Level Overview**: A concise summary of the overall support situation across these customers

- **Top Impacted Products**: List the products with the most support cases and any patterns you notice

- **Common Issues and Trends**: Identify recurring themes, issues, or patterns across cases

- **Projects and Business Impact**: Based on case descriptions, identify which projects or business areas appear to be most affected

- **Recommendations**: Any recommendations for addressing common issues or improving support efficiency

- **Important Contacts**: Identify important email addresses involved in the support case activity.

Format your response in clear markdown without headers and use bullet points for readability. Do not use numbered lists.
"""
    
    return prompt


def generate_summary(api_key, api_base_url, case_data, model, temperature, max_tokens, timeout):
    """Generate summary using OpenAI-compatible API."""
    
    try:
        # Initialize OpenAI client with custom base URL
        # Handle "EMPTY" api_key for local deployments
        client_api_key = api_key if api_key and api_key != "EMPTY" else "sk-no-key-required"
        
        client = OpenAI(
            api_key=client_api_key,
            base_url=api_base_url,
            timeout=timeout
        )
        
        # Build prompt
        prompt = build_prompt(case_data)
        
        # Create chat completion
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert technical analyst specializing in Red Hat support case analysis."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        # Extract the generated text
        summary = response.choices[0].message.content
        
        return summary, None
        
    except Exception as e:
        return None, str(e)


def main():
    module = AnsibleModule(
        argument_spec=dict(
            api_key=dict(type='str', required=True, no_log=True),
            api_base_url=dict(type='str', required=True),
            case_data=dict(type='dict', required=True),
            model=dict(type='str', required=False, default='gpt-3.5-turbo'),
            temperature=dict(type='float', required=False, default=0.7),
            max_tokens=dict(type='int', required=False, default=4096),
            timeout=dict(type='int', required=False, default=120),
        ),
        supports_check_mode=False
    )
    
    if not HAS_OPENAI:
        module.fail_json(msg='openai Python library is required. Install with: pip install openai')
    
    api_key = module.params['api_key']
    api_base_url = module.params['api_base_url']
    case_data = module.params['case_data']
    model = module.params['model']
    temperature = module.params['temperature']
    max_tokens = module.params['max_tokens']
    timeout = module.params['timeout']
    
    # Validate inputs
    if not api_key:
        module.fail_json(msg='API key is required (use "EMPTY" for local deployments without authentication)')
    
    if not api_base_url:
        module.fail_json(msg='API base URL is required')
    
    if not case_data or 'cases' not in case_data:
        module.fail_json(msg='case_data must contain "cases" key with case list')
    
    # Generate summary
    summary, error = generate_summary(
        api_key, api_base_url, case_data, model, 
        temperature, max_tokens, timeout
    )
    
    if error:
        module.fail_json(msg=f'Failed to generate summary: {error}')
    
    # Extract insights (basic parsing)
    insights = {
        'generated': True,
        'model_used': model,
        'cases_analyzed': len(case_data.get('cases', []))
    }
    
    module.exit_json(
        changed=False,
        summary=summary,
        insights=insights,
        model_used=model
    )


if __name__ == '__main__':
    main()

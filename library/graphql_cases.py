#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2024, Ansible Support Analyzer
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: graphql_cases
short_description: Fetch Red Hat support cases via the GraphQL API with server-side filtering
version_added: "2.0.0"
description:
    - Queries the Red Hat GraphQL API (C(https://graphql.redhat.com)) for support cases,
      applying server-side filters (account, date, status, product) and requesting only
      the fields each workflow needs.
    - Handles cursor-based pagination automatically, collecting all matching cases across
      multiple pages (max 200 records per page per Red Hat API guidelines).
    - Normalizes the GraphQL response fields to match the legacy REST v3 field names
      (C(caseNumber), C(summary), C(product), etc.) so existing templates and downstream
      tasks work without modification.
    - Reuses the same SSO bearer token already exchanged from the Red Hat offline token.
author:
    - Ansible Support Analyzer
options:
    access_token:
        description:
            - SSO bearer token obtained by exchanging a Red Hat offline token.
        required: true
        type: str
        no_log: true
    graphql_url:
        description:
            - Red Hat GraphQL endpoint URL.
        type: str
        default: "https://graphql.redhat.com"
    client_name:
        description:
            - Value for the C(apollographql-client-name) header required by the API.
        type: str
        default: "ansible-support-analyzer"
    client_version:
        description:
            - Value for the C(apollographql-client-version) header required by the API.
        type: str
        default: "1.0"
    account_numbers:
        description:
            - One or more Red Hat account numbers. Passed as an C(in) filter on
              C(RedHatSupportAccount.AccountNumber).
        required: true
        type: list
        elements: str
    last_modified_since:
        description:
            - ISO-8601 datetime string. Only cases with C(LastModifiedDate) greater than
              this value are returned (server-side C(gt) filter).
            - Omit to skip date filtering entirely.
        type: str
    status_filter:
        description:
            - Optional filter dict applied to the C(Status) field.
            - "Example: C({ne: Closed}) or C({in: ['Waiting on Red Hat', 'Waiting on Customer']})."
        type: dict
    product_filter:
        description:
            - Optional filter dict applied to C(Product.ParentProduct__r.Name).
            - Uses Red Hat GraphQL string operators (C(eq), C(ne), C(like), C(in), C(nin)).
            - "The C(like) operator uses C(%) as a wildcard: C({like: 'Red Hat Ansible%'})."
        type: dict
    extra_where:
        description:
            - Arbitrary additional filter dict merged into the top-level C(and) clause.
            - Use for ad-hoc filters not covered by the dedicated parameters.
        type: dict
    include_description:
        description:
            - Whether to request the C(Description) field from the API.
            - Set to C(false) for lighter payloads when descriptions are not needed (e.g. the tracker workflow).
        type: bool
        default: true
    page_size:
        description:
            - Number of records to request per pagination round.
            - Red Hat recommends a maximum of 200.
        type: int
        default: 200
    timeout:
        description:
            - HTTP request timeout in seconds, applied per pagination request.
        type: int
        default: 30
"""

EXAMPLES = r"""
- name: Fetch cases modified in the last 6 months for a single account
  graphql_cases:
    access_token: "{{ redhat_access_token }}"
    account_numbers: ["12345678"]
    last_modified_since: "2026-04-01T00:00:00Z"
  register: r_cases

- name: Fetch cases for multiple accounts without descriptions (tracker mode)
  graphql_cases:
    access_token: "{{ redhat_access_token }}"
    account_numbers: "{{ support_case_account_ids }}"
    last_modified_since: "{{ last_seen_timestamp }}"
    include_description: false
  register: r_cases

- name: Fetch only Ansible-related cases using product wildcard
  graphql_cases:
    access_token: "{{ redhat_access_token }}"
    account_numbers: ["12345678"]
    last_modified_since: "2026-01-01T00:00:00Z"
    product_filter:
      like: "Red Hat Ansible%"
  register: r_cases

- name: Fetch non-closed cases with custom GraphQL URL
  graphql_cases:
    access_token: "{{ redhat_access_token }}"
    graphql_url: "https://graphql.redhat.com"
    client_name: "my-custom-client"
    client_version: "2.0"
    account_numbers: ["12345678"]
    status_filter:
      ne: "Closed"
  register: r_cases
"""

RETURN = r"""
cases:
    description: >-
        List of case dicts with field names normalized to match the legacy REST v3
        response shape (C(caseNumber), C(summary), C(product), C(severity), C(status),
        C(createdDate), C(lastModifiedDate), C(owner), C(accountNumberRef), C(version),
        C(description)).
    type: list
    elements: dict
    returned: success
    sample:
        - caseNumber: "03919019"
          summary: "Cluster nodes failing to join"
          product: "Red Hat Ansible Automation Platform"
          version: "2.4"
          severity: "1 (Urgent)"
          status: "Waiting on Red Hat"
          createdDate: "2026-09-01T12:00:00.000Z"
          lastModifiedDate: "2026-09-30T08:15:00.000Z"
          owner: "Jane Doe"
          accountNumberRef: "12345678"
          description: "Detailed description of the issue..."
total_count:
    description: Total number of cases collected across all pages.
    type: int
    returned: success
pages_fetched:
    description: Number of pagination rounds performed.
    type: int
    returned: success
"""

import json

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.urls import open_url

# ---------------------------------------------------------------------------
# GraphQL query construction
# ---------------------------------------------------------------------------

# Fields requested for every case.  Description is conditionally appended.
CASE_FIELDS_CORE = """
    Id
    CaseNumber__c { value }
    Subject { value }
    Status { value }
    Priority { value }
    CreatedDate { value }
    LastModifiedDate { value }
    Product {
        Id
        Name { value }
        VersionName__c { value }
        ParentProduct__r {
            Id
            Name { value }
        }
    }
    RedHatSupportAccount {
        Id
        Name { value }
        AccountNumber { value }
    }
    Owner {
        ... on RedHatSupportGroup {
            Id
            Name { value }
        }
        ... on RedHatSupportUser {
            Id
            Name { value }
        }
    }
"""

CASE_FIELD_DESCRIPTION = """
    Description { value }
"""

QUERY_TEMPLATE = """
query FetchCases($where: RedHatSupportCase_Filter, $first: Int, $after: String) {
    redhat_support_uiapi {
        query {
            RedHatSupportCase(
                where: $where,
                first: $first,
                after: $after,
                orderBy: { LastModifiedDate: { order: DESC } }
            ) {
                totalCount
                edges {
                    node {
                        %s
                    }
                    cursor
                }
                pageInfo {
                    hasNextPage
                    endCursor
                }
            }
        }
    }
}
"""


def build_fields(include_description):
    """Return the GraphQL field selection string."""
    fields = CASE_FIELDS_CORE
    if include_description:
        fields += CASE_FIELD_DESCRIPTION
    return fields


def build_where(
    account_numbers, last_modified_since, status_filter, product_filter, extra_where
):
    """Build the ``where`` variable dict for the GraphQL query."""
    conditions = [
        {"RedHatSupportRecordType": {"Name": {"eq": "Technical Support"}}},
        {"AccessRestrictions__c": {"eq": "None"}},
    ]

    if len(account_numbers) == 1:
        conditions.append(
            {"RedHatSupportAccount": {"AccountNumber": {"eq": account_numbers[0]}}}
        )
    else:
        conditions.append(
            {"RedHatSupportAccount": {"AccountNumber": {"in": account_numbers}}}
        )

    if last_modified_since:
        conditions.append({"LastModifiedDate": {"gt": {"value": last_modified_since}}})

    if status_filter:
        conditions.append({"Status": status_filter})

    if product_filter:
        conditions.append({"Product": {"ParentProduct__r": {"Name": product_filter}}})

    if extra_where:
        conditions.append(extra_where)

    return {"and": conditions}


# ---------------------------------------------------------------------------
# Response normalization
# ---------------------------------------------------------------------------


def _val(obj, *keys):
    """Safely traverse nested dicts, returning the ``value`` leaf or empty string."""
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return ""
        current = current.get(key)
        if current is None:
            return ""
    return current


def normalize_node(node):
    """Convert a single GraphQL case node to the legacy REST field dict."""
    product_obj = node.get("Product") or {}
    parent_product = product_obj.get("ParentProduct__r") or {}

    owner_obj = node.get("Owner") or {}
    owner_name = _val(owner_obj, "Name", "value")

    account_obj = node.get("RedHatSupportAccount") or {}

    return {
        "caseNumber": _val(node, "CaseNumber__c", "value"),
        "summary": _val(node, "Subject", "value"),
        "status": _val(node, "Status", "value"),
        "severity": _val(node, "Priority", "value"),
        "product": _val(parent_product, "Name", "value")
        or _val(product_obj, "Name", "value"),
        "version": _val(product_obj, "VersionName__c", "value"),
        "createdDate": _val(node, "CreatedDate", "value"),
        "lastModifiedDate": _val(node, "LastModifiedDate", "value"),
        "owner": owner_name,
        "accountNumberRef": _val(account_obj, "AccountNumber", "value"),
        "description": _val(node, "Description", "value"),
    }


# ---------------------------------------------------------------------------
# HTTP / pagination
# ---------------------------------------------------------------------------


def execute_query(graphql_url, headers, query, variables, timeout):
    """POST a single GraphQL request and return the parsed JSON body."""
    payload = json.dumps({"query": query, "variables": variables})
    response = open_url(
        graphql_url,
        method="POST",
        headers=headers,
        data=payload,
        timeout=timeout,
    )
    body = json.loads(response.read())
    return body


def fetch_all_cases(
    module, graphql_url, headers, query, where_clause, page_size, timeout
):
    """Paginate through all result pages and return (cases, total_count, pages)."""
    all_cases = []
    cursor = None
    pages = 0
    total_count = None

    while True:
        variables = {
            "where": where_clause,
            "first": page_size,
            "after": cursor,
        }
        try:
            body = execute_query(graphql_url, headers, query, variables, timeout)
        except Exception as exc:
            module.fail_json(msg=f"GraphQL request failed: {exc}")

        errors = body.get("errors")
        if errors:
            messages = "; ".join(e.get("message", str(e)) for e in errors)
            module.fail_json(msg=f"GraphQL errors: {messages}")

        case_data = (
            body.get("data", {})
            .get("redhat_support_uiapi", {})
            .get("query", {})
            .get("RedHatSupportCase", {})
        )
        if not case_data:
            module.fail_json(
                msg="Unexpected GraphQL response structure — RedHatSupportCase key missing"
            )

        if total_count is None:
            total_count = case_data.get("totalCount", 0)

        edges = case_data.get("edges", [])
        for edge in edges:
            node = edge.get("node", {})
            all_cases.append(normalize_node(node))

        pages += 1
        page_info = case_data.get("pageInfo", {})
        if page_info.get("hasNextPage"):
            cursor = page_info.get("endCursor")
        else:
            break

    return all_cases, total_count or len(all_cases), pages


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------


def main():
    module = AnsibleModule(
        argument_spec=dict(
            access_token=dict(type="str", required=True, no_log=True),
            graphql_url=dict(type="str", default="https://graphql.redhat.com"),
            client_name=dict(type="str", default="ansible-support-analyzer"),
            client_version=dict(type="str", default="1.0"),
            account_numbers=dict(type="list", elements="str", required=True),
            last_modified_since=dict(type="str"),
            status_filter=dict(type="dict"),
            product_filter=dict(type="dict"),
            extra_where=dict(type="dict"),
            include_description=dict(type="bool", default=True),
            page_size=dict(type="int", default=200),
            timeout=dict(type="int", default=30),
        ),
        supports_check_mode=True,
    )

    access_token = module.params["access_token"]
    graphql_url = module.params["graphql_url"]
    client_name = module.params["client_name"]
    client_version = module.params["client_version"]
    account_numbers = module.params["account_numbers"]
    last_modified_since = module.params["last_modified_since"]
    status_filter = module.params["status_filter"]
    product_filter = module.params["product_filter"]
    extra_where = module.params["extra_where"]
    include_description = module.params["include_description"]
    page_size = module.params["page_size"]
    timeout = module.params["timeout"]

    if not account_numbers:
        module.fail_json(msg="account_numbers must contain at least one account number")

    if page_size < 1 or page_size > 200:
        module.fail_json(msg="page_size must be between 1 and 200")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "apollographql-client-name": client_name,
        "apollographql-client-version": client_version,
    }

    fields = build_fields(include_description)
    query = QUERY_TEMPLATE % fields
    where_clause = build_where(
        account_numbers, last_modified_since, status_filter, product_filter, extra_where
    )

    if module.check_mode:
        module.exit_json(changed=False, cases=[], total_count=0, pages_fetched=0)

    cases, total_count, pages = fetch_all_cases(
        module, graphql_url, headers, query, where_clause, page_size, timeout
    )

    module.exit_json(
        changed=False,
        cases=cases,
        total_count=total_count,
        pages_fetched=pages,
    )


if __name__ == "__main__":
    main()

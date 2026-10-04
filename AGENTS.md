# AGENTS.md

Guidance for agents (and humans) working in this repository.

## Project Layout

- `analyze_support_cases.yml` / `track_support_cases.yml` — top-level playbooks.
- `tasks/` — included task files (`analyze_account.yml`, `track_account.yml`).
- `library/` — custom Ansible modules (Python): `gsheet_update.py`, `gsheet_tracker.py`, `graphql_cases.py`, `llm_summarize.py`.
- `templates/` — Jinja2 templates for markdown/JSON/HTML reports.
- `group_vars/all/vars.yml` — default variables; `vars/inputs.example.yml` — per-run input example.
- `config/credential_types.yml` — Ansible Automation Platform custom credential type definitions
  (`controller_credential_types` list: "Ansible Support Analyzer" and "SMTP Server"; uses
  Ansible's `!unsafe` YAML tag). Both `analyze_support_cases.yml` and `track_support_cases.yml`
  job templates attach their own separate Credential instance of "Ansible Support Analyzer";
  only the tracker job template also needs an "SMTP Server" credential.

## Pre-commit Hooks

Configured in [`.pre-commit-config.yaml`](.pre-commit-config.yaml). Run locally with:

```bash
source .venv/bin/activate
pre-commit install          # one-time, installs the git hook
pre-commit run --all-files  # run on demand
```

Notable, non-obvious configuration choices:

- **`check-yaml --unsafe`**: `config/credential_types.yml` uses Ansible's `!unsafe` YAML tag.
  check-yaml's default safe loader rejects unknown tags, so `--unsafe` is required to let it
  load custom tags without erroring.
- **`ruff-format` instead of `autopep8`/`black`**: `autopep8` depends on the `lib2to3` module,
  which was removed in Python 3.13+, so it crashes under modern interpreters. `ruff-format` is
  a drop-in, actively maintained replacement. It's scoped to `files: ^library/.*\.py$` (the
  custom Ansible modules) since that's the only Python code in this repo.
- **`flake8 --max-line-length=160`**: matches `ansible-lint`'s own default line-length profile.
  This avoids flagging long lines inside module `DOCUMENTATION`/`EXAMPLES`/`RETURN` docstrings
  and LLM prompt text in `library/llm_summarize.py` that shouldn't be mechanically reflowed
  (reflowing prompt text would change what's actually sent to the LLM).
- **`flake8 --extend-ignore=E402`**: Ansible modules intentionally import `AnsibleModule` and
  optional third-party deps (wrapped in `try/except ImportError`) *after* the
  `DOCUMENTATION`/`EXAMPLES`/`RETURN` string constants, which otherwise trips "module level
  import not at top of file".

## YAML / Ansible Conventions

- Use real booleans (`true`/`false`), not YAML 1.1 `yes`/`no`.
- Use `ansible.builtin.command`/`ansible.builtin.shell` with `changed_when:` set explicitly
  rather than relying on the default (always "changed") behavior.
- Tag lists use spaces after commas: `tags: [ai, pdf, never]`.

## Red Hat GraphQL API

Both playbooks fetch support cases via the `graphql_cases` custom module, which queries
`https://graphql.redhat.com` (configurable via `redhat_graphql_url`). The module handles:

- **Server-side filtering** — account numbers (`in`), last-modified date (`gt`),
  status, and product (supports `like` with `%` wildcard for starts-with matching).
- **Cursor-based pagination** — automatically follows `pageInfo.endCursor` until all
  pages are collected (max 200 records per page per API guidelines).
- **Field normalization** — maps GraphQL field names (e.g. `CaseNumber__c.value`,
  `Subject.value`) back to the legacy REST field names (`caseNumber`, `summary`, …)
  so templates and downstream tasks require no changes.

Authentication reuses the same SSO bearer token already exchanged from the Red Hat
offline token. Two additional headers (`apollographql-client-name`,
`apollographql-client-version`) are configurable in `group_vars/all/vars.yml`.

### Tracker incremental fetch

`track_support_cases.yml` calls `gsheet_tracker` with `state: read` **once, before the
per-account loop**, to retrieve every tracked account's `last_seen_timestamp` from the previous
run in a single API call. Each account's cutoff is looked up from that result (no per-account
read); it's used as the `last_modified_since` GraphQL filter so only recently changed cases are
pulled. A manual override is available via the `tracker_last_run_date` extra variable; when
unset, the module falls back to the sheet timestamp, then to `activity_date`. The GraphQL fetch
also passes `status_filter: "{{ tracker_status_filter }}"` (default `{ne: "Closed"}`) so closed
cases never re-enter the "active" set — a case that was active last run but is now excluded by
this filter is exactly what causes `gsheet_tracker`'s diff to report it under `closed_cases`.

### Tracker writes (single write per run, not per account)

`gsheet_tracker` is split into three explicit states so a multi-account run makes **exactly one**
read and **exactly one** write against the Google Sheets API, regardless of account count:

- `state: read` — one read for the whole tab; returns per-account previous state
  (`accounts[name].last_seen_timestamp`/`total_previous`) plus `other_rows` (raw rows for
  accounts *not* in this run, preserved verbatim — including `HYPERLINK` formulas, since the
  read uses `valueRenderOption=FORMULA`) and `existing_rows` (the full raw matrix, for `diff`).
- `state: diff` — pure local computation, no API calls. Computes the new/closed/updated diff
  for one account against `existing_rows` and builds that account's replacement rows.
- `state: write` — takes `other_rows + <every account's diff rows, accumulated>` and performs
  the single clear+rewrite for the whole tab.

`tasks/track_account.yml` calls `diff` per account and accumulates its `rows` into the
playbook-level `tracker_pending_rows` fact; `track_support_cases.yml` calls `write` once after
the account loop completes.

### Tracker table maintenance (`gsheet_table_name`)

`state: write` also maintains a Sheets API v4 "Table" object (`addTable`/`updateTable` via
`batchUpdate`) covering the tab's full data range, named `table_name` (defaults to `gsheet_sheet`
via the `gsheet_table_name` variable; set to `""` to skip). This is a Sheets API feature, not a
Drive API one — the Drive API (`v3`) only exposes file/folder metadata and permissions and has no
endpoint for spreadsheet cell data or tables, so it cannot do this. Table creation/resizing is
best-effort: a failure only emits an `ansible.builtin.debug`-visible module warning (`module.warn`),
since the row data itself has already been written successfully by that point.

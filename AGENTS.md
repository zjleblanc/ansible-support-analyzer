# AGENTS.md

Guidance for agents (and humans) working in this repository.

## Project Layout

- `analyze_support_cases.yml` / `track_support_cases.yml` — top-level playbooks.
- `tasks/` — included task files (`analyze_account.yml`, `track_account.yml`).
- `library/` — custom Ansible modules (Python): `gsheet_update.py`, `gsheet_tracker.py`, `llm_summarize.py`.
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

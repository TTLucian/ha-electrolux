# Agent Instructions

## Repository

- Upstream: `TTLucian/ha-electrolux`
- All PRs target upstream `main`

## Branching

- Never commit directly to `main`
- Branch prefixes: `fix/` for bugfixes, `feat/` for features, `analysis/` for research
- Rebase on latest `upstream/main` before pushing

## Pull Requests

- Always create PRs as **drafts** first
- One concern per PR — keep scope tight

## Testing

- Run `pytest` before marking any task done
- CI requires 70% coverage (`--cov-fail-under=70`)
- Fix test failures before pushing — no PRs with known failing tests
- Use `python -m venv` + `pip install -r requirements_test.txt` to set up test env

## Code style

- Run `ruff check custom_components/electrolux` and `black custom_components/electrolux` before pushing
- CI will fail on lint/format errors

## Files to never commit

- `*.log`
- `*.txt` (script outputs)
- `config_entry-*.json` (diagnostics)
- `.envrc`, `.subtask/`, `.claude/`

## Catalog entries (`catalog_ac.py` and siblings)

- Verify capability key names against live device data — do not guess
- Reported-state-only fields need `capability_info` defined to be picked up by the catalog loop
- Add `entity_registry_enabled_default=False` for diagnostic/advanced entries

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

- Run `uv run pytest` before marking any task done
- CI requires 70% coverage (`--cov-fail-under=70`)
- Fix test failures before pushing — no PRs with known failing tests
- Use `uv sync --group test` to set up the test env (CI does the same)

## Code style

- Run `uv run ruff check custom_components/electrolux` and `uv run black custom_components/electrolux` before pushing
- CI will fail on lint/format errors

## Pre-commit (optional)

A `.pre-commit-config.yaml` is included that mirrors CI checks (ruff, black, mypy on commit; pytest on push).

```bash
pip install pre-commit && pre-commit install
```

Not required — CI catches the same issues — but useful for fast local feedback.

## Files to never commit

- `*.log`
- `*.txt` (script outputs)
- `config_entry-*.json` (diagnostics)
- `.envrc`, `.subtask/`, `.claude/`

## Catalog entries (`catalog_ac.py` and siblings)

- Verify capability key names against live device data — do not guess
- Reported-state-only fields need `capability_info` defined to be picked up by the catalog loop
- Add `entity_registry_enabled_default=False` for diagnostic/advanced entries

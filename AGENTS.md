# Agent Instructions

## Repository

- Upstream: `TTLucian/ha-electrolux`
- All PRs target upstream `main`

## Branching

- Never commit directly to `main`
- Branch prefixes: `fix/` bugfixes, `feat/` features, `analysis/` research, `chore/` tooling and CI, `release/` version prep
- Rebase on latest `upstream/main` before pushing
- Confirm the branch before editing — `git rev-parse --abbrev-ref HEAD`. A `git checkout <branch> -- <paths>` in a compound command can leave you somewhere you did not intend.

## Pull Requests

- Always create PRs as **drafts** first
- One concern per PR — keep scope tight
- Draft → ready fires `ready_for_review`; CI is configured to run on it

## Testing

- Run `uv run pytest --cov=custom_components/electrolux --cov-fail-under=90` before marking any task done
- CI requires **90%** coverage. It was 70% against a ~96% actual, which let a regression down to 71% pass silently.
- Fix test failures before pushing — no PRs with known failing tests
- Use `uv sync --group test --locked` to set up the test env. `--locked` matches CI: the lockfile is committed and is what gets tested.

## Code style

- Run `uv run ruff check custom_components/electrolux tests` and `uv run ruff format --check custom_components/electrolux tests` before pushing
- CI checks both paths — not just the component
- CI will fail on lint/format errors

## Pre-commit (optional)

`.pre-commit-config.yaml` mirrors CI: ruff, ruff-format and mypy on commit; actionlint and pytest on push. Keep the pinned `rev`s equal to the tool versions in `pyproject.toml`/`uv.lock`, and the `files:` scope equal to what CI checks — a hook that checks less than CI reads as a passing check while checking nothing.

The actionlint hook is `actionlint-docker`, pinned to the same image CI uses. It needs Docker, and it needs Docker for a reason: plain actionlint silently skips every shellcheck rule when shellcheck is absent, which is how 8 unquoted `$GITHUB_OUTPUT` redirections reached CI.

The mypy hook needs `--explicit-package-bases`. Without it the hook fails outright with "Source file found twice under different module names", because it passes mypy individual file paths; CI dodges the same problem by running two separate invocations. The hook was in this broken state while claiming to mirror CI.

```bash
pip install pre-commit && pre-commit install
```

Verify workflows the way CI does — `actionlint` with shellcheck present — not just the bare binary.

## JSON files — edit, never re-serialize

Do not read a repo JSON file with `json.load`/`json.loads` and write it back with `json.dump`. The repo's files have hand-set formatting (4-space in `translations/*.json` and `manifest.json`, 2-space in `strings.json`, inline arrays in `manifest.json`) and a serializer round-trip rewrites all of it. Adding one key to 28 locale files this way produced a 44,159-line diff.

Edit the specific line with the editor tool or a targeted `sed`. If a bulk edit is genuinely needed, match each file's existing indent and verify with `git diff --stat` that the change is proportional — check the stat *before* committing, not after.

## Translations

- New UI strings go in `strings.json` **and** `translations/en.json` only.
- The other 28 locale files are owned by `custom_components/electrolux/translations/translate.py`. Do not hand-edit them and do not add English placeholders — run the script.
- Google is the default backend; it will rate-limit a given IP. `--backend mymemory` is the fallback and is noticeably weaker: it dropped "low" from "Rinse aid low" across ~21 locales and returned "dishwashing machine" for it in Russian. Prefer waiting for Google.
- Never `--force`: it re-translates every key with no review.
- A missing key falls back to English and reads correctly; a wrong key displays garbage. If a translation is doubtful, remove it rather than ship it.

## Releases

- A release needs `release_notes/RELEASE_NOTES_vX.Y.Z.md` or the release workflow creates nothing.
- Prerelease versions (containing `-`) are skipped by the workflow and published by hand via the API.
- Bump `manifest.json` by editing the one `version` line, then tag only after the release merge lands on `main`.

## Files to never commit

- `*.log`
- `*.txt` (script outputs)
- `config_entry-*.json` (diagnostics)
- `.envrc`, `.subtask/`, `.claude/`

## Catalog entries (`catalog_ac.py` and siblings)

- Verify capability key names against live device data — do not guess
- Reported-state-only fields need `capability_info` defined to be picked up by the catalog loop
- Add `entity_registry_enabled_default=False` for diagnostic/advanced entries

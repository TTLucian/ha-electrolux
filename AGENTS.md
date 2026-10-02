# Agent Instructions

## Repository

- Upstream: ``TTLucian/ha-electrolux``
- Component path: ``custom_components/electrolux/`` (underscore, not the dashed form)

## Branching

- Never commit directly to `main`
- Branch prefixes: `fix/` bugfixes, `feat/` features, `analysis/` research,
  `chore/` tooling and CI, `release/` version prep
- Rebase on latest `upstream/main` before pushing
- Confirm the branch before editing - `git rev-parse --abbrev-ref HEAD`. A
  `git checkout <branch> -- <paths>` in a compound command can leave you
  somewhere you did not intend.

## Pull Requests

- Always create PRs as **drafts** first
- One concern per PR - keep scope tight
- Draft -> ready fires `ready_for_review`; CI is configured to run on it

## Toolchain - uv, and the lockfile is the contract

`uv.lock` is the single source of truth. `--locked` matches CI: the committed
lockfile is exactly what gets tested.

```bash
uv sync --locked          # install
uv run ruff check .       # whole repository, not just the component
uv run ruff format --check .
uv run mypy --namespace-packages --explicit-package-bases \
  $(for d in custom_components tests scripts .github/scripts; do [ -d "$d" ] && printf '%s ' "$d"; done)
uv run pytest
```

- `mypy` reads `pyproject.toml`. There is no `mypy.ini`; the two used to coexist
  and `mypy.ini` silently won, leaving the `pyproject.toml` settings dead.
- Never pass `--follow-imports=skip` to mypy. It reports false
  `untyped-decorator` errors on `@pytest.mark.asyncio` because it cannot see
  pytest's own types. The flags above are the ones that work.
- Do not use **black**. `ruff format` is the configured formatter, and one
  formatter is easier to keep consistent than two.
  - An earlier version of this file claimed black "corrupts
    `except (A, B):` into `except A, B:`, which is a `SyntaxError`". That is
    **wrong**. `except A, B:` is PEP 758, valid on Python 3.14, and parses as a
    tuple with an AST identical to `except (A, B):`. This repository uses it
    deliberately.

## Testing

- There **is** a coverage floor: `fail_under` in `pyproject.toml` under `[tool.coverage.report]`, currently 90, with actual coverage around 96%. It is the one repository in this family where a gate holds, because the suite is large enough to support it.

- Fix test failures before pushing - no PRs with known failing tests
- CI runs `pytest -q --junitxml=junit.xml` and uploads the report as an artifact
- Do not add `--cov-fail-under` on the command line. The floor lives in
  `pyproject.toml` under `[tool.coverage.report]` so that CI, the pre-commit
  hook and a bare local run all enforce the same number. Spelling it out in
  several places is how they ended up disagreeing.

## Drift guards - run these, do not work around them

`tests/test_repo_consistency.py` fails when configuration that must agree stops
agreeing. It is the reason this repository is not quietly drifting:

- pre-commit hook revisions must equal the versions `uv.lock` resolves.
  **Dependabot does not edit `.pre-commit-config.yaml`**, so re-check the revs
  after merging any of its "uv" pull requests.
- the pre-commit mypy scope must cover every directory CI type-checks.
- CI must run ruff over the whole repository.
- the locked Home Assistant must not be a pre-release.

If one of these fires, fix the configuration it is pointing at. Do not delete
the test.

## Workflows

Two guards exist because a bad workflow reference fails *silently*:

- `.github/scripts/validate_workflow_actions.py` - fetches each SHA-pinned
  action's `action.yml` and fails on an unresolvable reference or a `with:` key
  the action does not declare. GitHub **ignores unknown `with:` keys**, so a
  typo there looks like a passing job.
- `.github/workflows/actionlint.yml` - syntax and expression checking, including
  shellcheck rules, via `run_actionlint.py`. No Docker: both tools are
  pinned ordinary dependencies so the check is available to everyone.

They are not redundant: one checks that the workflow parses, the other checks
that what it references exists.

When adding a workflow step, check the action's real input names - do not copy
them from `actions/setup-python` onto a different action.

## Pre-commit (optional)

`.pre-commit-config.yaml` mirrors CI: ruff, ruff-format, mypy and workflow lint on
commit, `uv lock --check` when the lockfile or `pyproject.toml` changes, and
pytest on pre-push. Its `files:` scope is expressed as directories rather than
by the integration name, so this file is byte-identical across repositories.

The workflow-lint hook runs `.github/scripts/run_actionlint.py`, the same script
CI runs, so a local run and a CI run check identically. Both tools are pinned:
shellcheck ships inside the venv via `shellcheck-py`, and the script fetches
actionlint at a fixed version.

**Do not run a bare `actionlint`.** Without shellcheck on PATH it does not warn
and does not fail - it checks less and exits 0. That silent degradation is how
an SC2086 (an unquoted variable in the mypy step) reached all three repositories
at once, because a local run looked clean while the rule that would have caught
it never executed. Use the script, which fails loudly when either tool is
missing.

```bash
uv sync --locked && uv run pre-commit install
```

## Line endings - everything is LF

Every tracked file uses LF, enforced by `.gitattributes`:

```
* text=auto eol=lf
```

`text=auto` lets git detect binaries, so images and archives are left alone.
**Do not add exceptions.** A single CRLF file makes line endings depend on the
machine doing the checkout, and flipping one turns a one-line change into a
whole-file diff.

If you inherit a file with CRLF, `git add --renormalize .` fixes it. That is
the correct use of the command - it is only wrong when applied to files that are
already correct. Never override `core.autocrlf` for a single `git add` to force
the opposite.

## JSON files - edit, never re-serialize

Do not read a repo JSON file with `json.load` and write it back with `json.dump`.
`manifest.json`, `strings.json` and `translations/en.json` use hand-set 2-space
indentation; a serializer round-trip rewrites every line, producing an enormous
diff for a one-key change.

Edit the specific line with the editor tool or a targeted `sed`. If a bulk edit
is genuinely needed, verify with `git diff --stat` that the change is
proportional - check the stat *before* committing, not after.

## Home Assistant version pinning

`uv.lock` pins Home Assistant to a **stable** release, which is what most users
run. Pre-releases are never pinned deliberately here.

You do not choose the Home Assistant version directly. In repositories that use
`pytest-homeassistant-custom-component`, that harness pins Home Assistant with
`==`, one harness release per Home Assistant release, so upgrading the harness
is an upgrade of Home Assistant in disguise - and the newest harness often pins a
*pre-release*. That is the trap that
`.github/scripts/check_dependency_freshness.py` exists to make visible.

`requires-python` must stay aligned with what the pinned Home Assistant
requires. A looser bound makes uv keep a second, much older homeassistant entry
in the lockfile for unsupported interpreter markers, which silently pins CI to a
version nobody runs.

CI derives the Python version from the locked Home Assistant rather than a
hard-coded number, so it follows Dependabot automatically. `.python-version`
covers local development; the two agree because both track the lock.

``.github/dependabot.yml` opens a weekly pull request for the `uv` ecosystem, so a newer stable release arrives as a reviewable diff rather than going stale unnoticed. Updates are split into groups (`runtime`, `framework`, `tooling`) because a single group puts a risky bump in the same PR as safe ones, and one blocked update stalls everything behind it. A 7-day cooldown is set because Home Assistant and its test harness pin each other exactly, so a build created the moment something publishes routinely resolves to a pair that will not install together.

The weekly `Dependency freshness` job (`.github/scripts/check_dependency_freshness.py`) is the backstop for when such a PR is never opened or never merged. It runs on schedule and manual dispatch only, not on every push.`

## Files to never commit

- `*.log`
- `*.txt` used as script output
- `junit.xml` (CI artifact)
- `__pycache__/`, `.ruff_cache/`, `.mypy_cache/`, `.pytest_cache/`, `.coverage`
- `pyrightconfig.local.json` - but `pyrightconfig.json` **is** tracked, because
  without an explicit `pythonVersion` Pylance falls back to an older
  interpreter and reports errors that do not exist
- `.vscode/` is **tracked** on purpose - see `.gitignore`. Only
  `.vscode/*.local.json` stays local.

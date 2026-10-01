"""Guards against configuration drift between the places that must agree.

Every check here corresponds to a real drift found in this repository:

* pre-commit pinned ruff v0.15.17 / mypy v2.1.0 while the project ran
  0.16.9 / 2.3.1, so the hooks could pass on things CI rejected.
* pre-commit scoped its python hooks to custom_components/electrolux/ alone
  while CI also checks tests/, so nothing in tests/ was checked locally.
* The coverage floor was written out in ci.yml, .pre-commit-config.yaml and
  AGENTS.md, and had already reached 70 in one place against 90 in another.

The pattern is one value living in several files with nothing comparing them.
These tests are that comparison.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
UV_LOCK = REPO_ROOT / "uv.lock"
PRE_COMMIT = REPO_ROOT / ".pre-commit-config.yaml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"
AGENTS = REPO_ROOT / "AGENTS.md"


def _load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _locked_versions() -> dict[str, str]:
    """Exact versions uv.lock resolves - the ones CI actually installs."""
    lock = _load_toml(UV_LOCK)
    return {pkg["name"]: pkg["version"] for pkg in lock.get("package", []) if "version" in pkg}


def _hooks_by_id() -> dict[str, dict]:
    """Map hook id -> {"rev": repo rev, **hook} (rev belongs to the repo, not the hook)."""
    config = _load_yaml(PRE_COMMIT)
    return {hook["id"]: {"rev": repo.get("rev"), **hook} for repo in config["repos"] for hook in repo["hooks"]}


def _ci_checked_paths() -> set[str]:
    """Path arguments CI passes to ruff/mypy, ignoring their own flags.

    Only the non-flag arguments are paths: `ruff format --check --diff <paths>`
    is two ruff paths, not four.
    """
    paths: set[str] = set()
    for line in CI_WORKFLOW.read_text(encoding="utf-8").splitlines():
        match = re.search(r"run: (?:ruff \w+|mypy)((?: [^\s]+)+)", line)
        if not match:
            continue
        paths.update(token for token in match.group(1).split() if not token.startswith("-"))
    return paths


class TestPreCommitMatchesLockedToolVersions:
    """A hook running a different tool version than CI is not a mirror."""

    @pytest.mark.parametrize(
        ("hook_id", "package"),
        [("ruff", "ruff"), ("mypy", "mypy")],
    )
    def test_hook_rev_matches_uv_lock(self, hook_id: str, package: str) -> None:
        locked = _locked_versions()[package]
        rev = _hooks_by_id()[hook_id]["rev"]

        assert rev == f"v{locked}", (
            f"pre-commit pins {hook_id} at {rev} but uv.lock resolves {package} {locked}. "
            f"Bump the rev in .pre-commit-config.yaml to v{locked}, or the hook will "
            f"check something CI never runs."
        )


class TestPreCommitScopeMatchesCI:
    """A hook that checks less than CI reads as a passing check while checking nothing."""

    def test_python_hooks_cover_every_path_ci_checks(self) -> None:
        ci_paths = _ci_checked_paths()
        assert ci_paths, "could not read the checked paths out of ci.yml; update this test"

        missing = []
        for hook_id in ("ruff", "ruff-format", "mypy"):
            pattern = _hooks_by_id()[hook_id].get("files", "")
            for path in sorted(ci_paths):
                if not re.search(pattern, path + "/"):
                    missing.append(f"{hook_id} would skip {path}/")

        assert not missing, "pre-commit hooks are scoped narrower than CI: " + "; ".join(sorted(set(missing)))


class TestCoverageFloorHasOneHome:
    """The floor lives in pyproject; copying it is how it drifts."""

    def test_pyproject_defines_the_floor(self) -> None:
        assert _load_toml(PYPROJECT)["tool"]["coverage"]["report"]["fail_under"] == 90

    @pytest.mark.parametrize("path", [CI_WORKFLOW, PRE_COMMIT], ids=["ci.yml", "pre-commit"])
    def test_no_copied_floor_elsewhere(self, path: Path) -> None:
        # Comments are allowed to mention it; a real argument is not.
        uncommented = "\n".join(
            line for line in path.read_text(encoding="utf-8").splitlines() if not line.lstrip().startswith("#")
        )
        assert "--cov-fail-under" not in uncommented, (
            f"{path.name} hardcodes a coverage floor. The single source is "
            "fail_under in pyproject.toml [tool.coverage.report]; passing the flag "
            "here overrides it and reintroduces the drift this prevents."
        )

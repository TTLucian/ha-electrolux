"""Guards against configuration drift between the places that must agree.

Every check here corresponds to a real drift found while aligning the three
repositories that share this tooling:

* pre-commit pinned ruff v0.15.17 / mypy v2.1.0 while the project ran
  0.16.9 / 2.3.1, so the hooks could pass on things CI rejected.
* pre-commit scoped its python hooks to the component directory alone while
  CI also checked tests/, so nothing in tests/ was checked locally.
* dependabot proposed a Home Assistant pre-release that the declared version
  range happily accepts.

The pattern is one value living in several files with nothing comparing them.
These tests are that comparison.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml
from packaging.version import Version

REPO_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT = REPO_ROOT / "pyproject.toml"
UV_LOCK = REPO_ROOT / "uv.lock"
PRE_COMMIT = REPO_ROOT / ".pre-commit-config.yaml"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def _load_toml(path: Path) -> dict:
    with path.open("rb") as handle:
        return tomllib.load(handle)


def _toml_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _load_yaml(path: Path) -> dict:
    # yaml.safe_load is typed Any; annotate so the return type is honest.
    with path.open(encoding="utf-8") as handle:
        data: dict = yaml.safe_load(handle)
    return data


def _locked_versions() -> dict[str, str]:
    """Exact versions uv.lock resolves - the ones CI actually installs."""
    lock = _load_toml(UV_LOCK)
    return {pkg["name"]: pkg["version"] for pkg in lock.get("package", []) if "version" in pkg}


def _hooks_by_id() -> dict[str, dict]:
    """Map hook id -> {"rev": repo rev, **hook} (rev belongs to the repo, not the hook)."""
    config = _load_yaml(PRE_COMMIT)
    return {hook["id"]: {"rev": repo.get("rev"), **hook} for repo in config["repos"] for hook in repo["hooks"]}


def _ci_text() -> str:
    return CI_WORKFLOW.read_text(encoding="utf-8")


def _ci_mypy_dirs() -> set[str]:
    """Directories CI passes to mypy.

    The mypy step is a shell loop rather than a fixed list so that one ci.yml
    can be byte-identical across repositories that do not all have the same
    top-level directories. mypy errors on a path that does not exist, so the
    loop filters to what is actually present.
    """
    dirs: set[str] = set()
    for match in re.finditer(r"for dir in ([a-zA-Z0-9_./ -]+); do", _ci_text()):
        dirs.update(match.group(1).split())
    return dirs


class TestCIRunsWholeRepository:
    """A scoped CI check looks thorough while skipping files the editor checks."""

    @pytest.mark.parametrize("tool", ["ruff check .", "ruff format --check ."])
    def test_ruff_covers_whole_repository(self, tool: str) -> None:
        assert tool in _ci_text(), (
            f"CI does not run `{tool}`. Scoping it to one directory leaves the "
            "rest of the repository unchecked in CI while the editor still "
            "reports errors in it."
        )


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
            f"check something CI never runs. Dependabot does not edit this file, "
            f"so re-check it after merging any dependabot bump."
        )


class TestPreCommitScopeMatchesCI:
    """A hook that checks less than CI reads as a passing check while checking nothing."""

    def test_mypy_hook_covers_every_directory_ci_checks(self) -> None:
        ci_dirs = _ci_mypy_dirs()
        assert ci_dirs, "could not read the mypy target list out of ci.yml; update this test"

        pattern = _hooks_by_id()["mypy"].get("files", "")
        missing = [d for d in sorted(ci_dirs) if not re.search(pattern, d.rstrip("/") + "/")]

        assert not missing, "the pre-commit mypy hook is scoped narrower than CI and would skip: " + ", ".join(missing)

    @pytest.mark.parametrize("hook_id", ["ruff", "ruff-format", "mypy"])
    def test_hook_scope_includes_the_whole_repository_shape(self, hook_id: str) -> None:
        pattern = _hooks_by_id()[hook_id].get("files", "")
        assert "custom_components/" in pattern, f"the {hook_id} hook does not cover custom_components/, which CI checks"
        assert "tests/" in pattern, f"the {hook_id} hook does not cover tests/, which CI checks"


class TestPythonRangeIsInternallyConsistent:
    """The declared range and .python-version have to agree with each other.

    Whether the range still covers what Home Assistant needs is a *live*
    question, answered by `.github/scripts/bump_python_if_needed.py` from the CI
    "Python floor" job. This test stays offline on purpose: the Home Assistant
    test harness patches socket DNS resolution and fails any test that tries
    to reach the network, which is a good default and not something to work
    around.
    """

    def test_requires_python_has_an_upper_bound(self) -> None:
        declared = re.search(r'requires-python\s*=\s*"([^"]+)"', _toml_text(PYPROJECT))
        assert declared, "pyproject.toml has no requires-python"

        assert re.search(r"<\s*\d+\.\d+", declared.group(1)), (
            f'requires-python is "{declared.group(1)}" with no upper bound. uv would '
            "then resolve for Python versions that do not exist yet, and the lockfile "
            "would grow a resolution branch per future release until some unrelated "
            "dependency stops having a compatible release for one of them."
        )

    def test_python_version_falls_inside_the_declared_range(self) -> None:
        declared = re.search(r'requires-python\s*=\s*"([^"]+)"', _toml_text(PYPROJECT))
        assert declared, "pyproject.toml has no requires-python"
        range_text = declared.group(1)

        version = (REPO_ROOT / ".python-version").read_text(encoding="utf-8").strip()
        match = re.fullmatch(r"(\d+)\.(\d+)", version)
        assert match, f".python-version is {version!r}; expected something like '3.14'"
        current = (int(match.group(1)), int(match.group(2)))

        floor = re.search(r">=\s*(\d+)\.(\d+)", range_text)
        ceiling = re.search(r"<\s*(\d+)\.(\d+)", range_text)
        assert floor and ceiling, f"could not read a bounded range out of {range_text!r}"

        low = (int(floor.group(1)), int(floor.group(2)))
        high = (int(ceiling.group(1)), int(ceiling.group(2)))
        assert low <= current < high, (
            f".python-version is {version} but requires-python is {range_text!r}. "
            "CI derives its Python from the locked Home Assistant, and local "
            "development should agree with it - otherwise `uv sync` resolves "
            "something different locally than CI tests."
        )


class TestHomeAssistantTracksStableOnly:
    """HA publishes a pre-release for every monthly release.

    A range such as ``homeassistant>=2026.9.4,<2027.0.0`` does not exclude
    them - a beta satisfies it. PEP 440 has no "no prerelease" clause, so
    dependabot would happily propose one and it would install.

    The intent is to track stable only, so assert it here rather than trusting
    the range to say what it cannot. This fails the dependabot PR that first
    proposes a beta, which is exactly when it is cheap to reject.
    """

    def test_locked_homeassistant_is_not_a_prerelease(self) -> None:
        locked = _locked_versions()["homeassistant"]

        assert not Version(locked).is_prerelease, (
            f"uv.lock resolves homeassistant {locked}, which is a prerelease. "
            f"This integration tracks stable only - reject the bump."
        )

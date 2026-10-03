"""Raise the declared Python range when Home Assistant needs a newer one.

Home Assistant raises its own Python floor over time, and it pins the
harness, which pins Home Assistant. So when a new Home Assistant release
needs a newer Python *minor* version, `requires-python` becomes the one thing
Dependabot cannot fix on its own: uv refuses to resolve a dependency outside
the declared range, so its pull request does not even build.

The `upper bound` in `requires-python` is deliberate. Without it uv starts
resolving for Python versions that do not exist yet, and the lockfile grows a
branch per future release until some unrelated dependency stops having a
compatible release for one of them. Bounding the range keeps the lockfile
small and the build deterministic.

This closes that gap instead of hand-bumping twice a year: it runs on a
schedule, and when the floor has genuinely moved it edits the two files that
declare it and exits non-zero. The calling workflow turns that into a pull
request, which goes through CI like any other change - so the new range is
proven before it lands.

Idempotent: exits 0 and changes nothing when the declaration is already
correct, which is the normal case.

Usage: uv run python .github/scripts/bump_python_if_needed.py [--check]
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from packaging.version import InvalidVersion, Version

REPO = Path(__file__).resolve().parent.parent.parent


def _set_output(name: str, value: str) -> None:
    """Publish a step output when running inside GitHub Actions."""
    target = os.environ.get("GITHUB_OUTPUT")
    if target:
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(f"{name}={value}\n")


PYPROJECT = REPO / "pyproject.toml"
PYTHON_VERSION = REPO / ".python-version"
UV_LOCK = REPO / "uv.lock"


def locked_homeassistant() -> str | None:
    """Highest homeassistant version in uv.lock - the one CI actually tests.

    uv.lock may hold more than one entry for the same package, split across
    resolution markers; the highest is the one a current interpreter gets.
    """
    text = UV_LOCK.read_text(encoding="utf-8")
    found = re.findall(r'\[\[package\]\]\nname = "homeassistant"\nversion = "([^"]+)"', text)
    parsed: list[Version] = []
    for raw in found:
        try:
            parsed.append(Version(raw))
        except InvalidVersion:
            continue
    return str(max(parsed)) if parsed else None


def required_python(version: str) -> str | None:
    """The `requires_python` string for a given Home Assistant release."""
    url = f"https://pypi.org/pypi/homeassistant/{version}/json"
    request = urllib.request.Request(url, headers={"User-Agent": "python-floor-check"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            data: dict[str, Any] = json.load(response)
    except urllib.error.URLError, urllib.error.HTTPError, TimeoutError:
        return None
    info: dict[str, Any] = data.get("info") or {}
    required = info.get("requires_python")
    return required if isinstance(required, str) else None


def as_minor(text: str) -> tuple[int, int] | None:
    match = re.search(r"(\d+)\.(\d+)", text)
    return (int(match.group(1)), int(match.group(2))) if match else None


def main() -> int:
    check_only = "--check" in sys.argv

    locked = locked_homeassistant()
    if locked is None:
        print("::warning::Could not find homeassistant in uv.lock")
        return 0

    requires = required_python(locked)
    need = as_minor(requires) if requires else None
    if need is None:
        print(f"::warning::Could not read Home Assistant {locked}'s Python requirement")
        return 0

    declared = re.search(r'requires-python\s*=\s*"([^"]+)"', PYPROJECT.read_text(encoding="utf-8"))
    if declared is None:
        print("::error::pyproject.toml has no requires-python")
        return 1

    ceiling_match = re.search(r"<\s*(\d+)\.(\d+)", declared.group(1))
    current_version_file = PYTHON_VERSION.read_text(encoding="utf-8").strip()

    print(f"homeassistant {locked} requires Python {requires} -> {need[0]}.{need[1]}")
    print(f"declared requires-python: {declared.group(1)}")
    print(f"declared .python-version: {current_version_file}")

    if ceiling_match is None:
        print("::warning::requires-python has no upper bound; nothing to raise")
        return 0

    ceiling = (int(ceiling_match.group(1)), int(ceiling_match.group(2)))
    wanted_minor = f"{need[0]}.{need[1]}"

    # The range is "< ceiling", so it already covers `need` only when
    # need < ceiling. When need >= ceiling the range *excludes* the Python
    # Home Assistant now needs, and uv would refuse to resolve it at all -
    # which is exactly what blocks the Dependabot pull request.
    declared_minor = as_minor(current_version_file)
    range_ok = need < ceiling
    version_file_ok = declared_minor is not None and declared_minor >= need

    if range_ok and version_file_ok:
        print("OK: the declared range and .python-version already cover the required Python.")
        _set_output("changed", "false")
        return 0

    # Only ever *raise* the ceiling. A range that is already wide enough is a
    # deliberate choice and must not be narrowed back down to the minimum.
    new_range = declared.group(1)
    if not range_ok:
        new_ceiling = f"{need[0]}.{need[1] + 1}"
        new_range = re.sub(r"<\s*\d+\.\d+", f"<{new_ceiling}", declared.group(1))
        print(
            f"\nThe range excludes the required Python: Home Assistant needs "
            f"{wanted_minor} but requires-python is {declared.group(1)}"
        )
    if not version_file_ok:
        print(f"\n.python-version is {current_version_file} but {wanted_minor} is needed")
    print(f'\nSetting requires-python = "{new_range}" and .python-version = {wanted_minor}')

    _set_output("changed", "true")

    if check_only:
        return 1

    text = PYPROJECT.read_text(encoding="utf-8")
    PYPROJECT.write_text(
        text.replace(f'requires-python = "{declared.group(1)}"', f'requires-python = "{new_range}"'),
        encoding="utf-8",
    )
    PYTHON_VERSION.write_text(f"{wanted_minor}\n", encoding="utf-8")
    print(f"\nUpdated pyproject.toml and .python-version to {wanted_minor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

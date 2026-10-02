"""Fail when uv.lock no longer pins the latest STABLE Home Assistant.

Home Assistant releases on its own schedule and users install the newest
stable, so a repository that keeps testing an older pin drifts away from what
people actually run without anything failing. This runs weekly and turns that
silent drift into a red job.

Why a script and not only Dependabot: Dependabot *proposes* the upgrade as a
pull request, and a proposal can sit unmerged for weeks. This is the backstop
that says "you are behind" even when no PR was opened.

Two deliberate rules, both learned the hard way:

  1. Stable only. Pre-releases are never an acceptable pin here. The newest
     test-harness release frequently pins a Home Assistant pre-release, so
     blindly taking the newest available thing moves CI *off* stable rather
     than onto it. The harness is therefore only advanced when the Home
     Assistant version it pins is itself stable.
  2. Home Assistant cannot be chosen directly. pytest-homeassistant-custom-
     component pins it with "==", one harness release per Home Assistant
     release. Moving Home Assistant means moving the harness. This script
     reports which Home Assistant a candidate harness would bring, so the
     trade-off is visible before the lockfile is touched.

Repositories that do not use the test harness are handled too: the harness
checks are skipped and only the Home Assistant pin is verified.

Usage: python .github/scripts/check_dependency_freshness.py
"""

from __future__ import annotations

import json
import re
import sys
import urllib.error
import urllib.request
from typing import Any

from packaging.version import InvalidVersion, Version

PYPI = "https://pypi.org/pypi/{package}/json"
HARNESS = "pytest-homeassistant-custom-component"


def _fetch(url: str, timeout: int = 30) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "freshness-check"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data: dict[str, Any] = json.load(response)
    return data


def latest_stable(package: str) -> str | None:
    """Return the newest non-prerelease version of ``package``."""
    data = _fetch(PYPI.format(package=package))
    candidates = []
    for raw in data["releases"]:
        try:
            ver = Version(raw)
        except InvalidVersion:
            continue
        if ver.is_prerelease or ver.is_devrelease:
            continue
        candidates.append(ver)
    return str(max(candidates)) if candidates else None


def locked_version(package: str) -> str | None:
    """Return the highest version of ``package`` present in uv.lock.

    uv.lock may hold more than one entry for the same package, split across
    resolution markers; the highest is the one a current interpreter gets.
    """
    with open("uv.lock", encoding="utf-8") as handle:
        lock = handle.read()

    versions = re.findall(rf'\[\[package\]\]\nname = "{re.escape(package)}"\nversion = "([^"]+)"', lock)
    parsed = []
    for raw in versions:
        try:
            parsed.append(Version(raw))
        except InvalidVersion:
            continue
    return str(max(parsed)) if parsed else None


def harness_pinned_homeassistant(harness: str) -> str | None:
    """Return the exact homeassistant version a harness release requires."""
    url = PYPI.format(package=HARNESS).replace("/json", f"/{harness}/json")
    try:
        data = _fetch(url)
    except urllib.error.URLError, urllib.error.HTTPError, TimeoutError:
        return None

    # json.load returns Any; annotate so mypy can type the loop under
    # warn_return_any, which some of the repositories sharing this file enable.
    info: dict[str, Any] = data.get("info") or {}
    requirements: list[str] = info.get("requires_dist") or []
    for requirement in requirements:
        name, _, spec = requirement.partition("==")
        if name.strip().lower() == "homeassistant" and spec:
            return spec.strip().split(";")[0].strip()
    return None


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []

    locked_ha = locked_version("homeassistant")
    latest_ha = latest_stable("homeassistant")

    print("homeassistant:")
    print(f"  locked in uv.lock : {locked_ha}")
    print(f"  latest stable     : {latest_ha}")

    if locked_ha is None or latest_ha is None:
        print("  -> could not compare; treating as a failure so it is not silent")
        problems.append("could not determine the Home Assistant version")
    else:
        locked_v, latest_v = Version(locked_ha), Version(latest_ha)
        if locked_v.is_prerelease:
            problems.append(f"uv.lock pins the pre-release {locked_ha}; this project pins stable only")
            print(f"  -> FAIL: pre-release pin; stable is {latest_ha}")
        elif latest_v > locked_v:
            problems.append(f"uv.lock pins {locked_ha}; stable {latest_ha} is available")
            print("  -> FAIL: behind the latest stable")
        else:
            print("  -> up to date with latest stable")

    # The harness only exists in repositories that use it. Where it does, a
    # newer release is only worth taking when it keeps Home Assistant stable.
    locked_harness = locked_version(HARNESS)
    if locked_harness is None:
        print(f"\n{HARNESS}: not used by this repository (skipped)")
    else:
        latest_harness = latest_stable(HARNESS)
        print(f"\n{HARNESS}:")
        print(f"  locked in uv.lock : {locked_harness}")
        print(f"  latest stable     : {latest_harness}")
        if latest_harness is None:
            print("  -> could not compare")
        elif Version(latest_harness) <= Version(locked_harness):
            print("  -> up to date")
        else:
            pinned = harness_pinned_homeassistant(latest_harness)
            print(f"  -> newer harness would pin homeassistant=={pinned}")
            if pinned is not None and Version(pinned).is_prerelease:
                notes.append(f"harness {latest_harness} is available but pins homeassistant=={pinned} (pre-release)")
                print("  -> not drift: taking it would move CI off stable Home Assistant")
            elif pinned is not None:
                problems.append(f"{HARNESS} {latest_harness} is available and pins stable homeassistant=={pinned}")
                print("  -> a newer stable Home Assistant is reachable; upgrade the harness")

    for note in notes:
        print(f"\nNote (not a failure):\n  * {note}")

    if problems:
        print("\nDependency drift detected:")
        for item in problems:
            print(f"  * {item}")
        print(
            "\nTo update:\n"
            "  1. If a newer stable Home Assistant is available, let the Dependabot\n"
            "     'uv' PR land; it updates pyproject.toml and uv.lock together.\n"
            "  2. If only the harness is behind, bump it to the release that ships\n"
            "     the Home Assistant version you want:\n"
            f"       uv lock --upgrade-package '{HARNESS}==<version>'\n"
            "  3. If Python itself must move, update .python-version and the\n"
            "     requires-python range in pyproject.toml, then re-lock."
        )
        return 1

    print("\nHome Assistant is pinned to the latest stable release.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

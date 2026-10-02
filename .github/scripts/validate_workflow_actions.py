"""Validate that every workflow `uses:` reference and `with:` input is real.

actionlint checks workflow *syntax* but never resolves action references, and
both failure modes are silent. A misspelled `with:` key is simply ignored by
GitHub, and an unresolvable `uses:` only fails once the job is scheduled. Both
have bitten this repository, so this check runs in CI and fetches each
action's own `action.yml` to confirm:

  * the reference resolves (and, when pinned by SHA, that the SHA exists)
  * every key under `with:` is a declared input of that action

Usage: python .github/scripts/validate_workflow_actions.py [workflow_dir]
"""

from __future__ import annotations

import re
import sys
import urllib.error
import urllib.request
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import yaml

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RAW = "https://raw.githubusercontent.com/{repo}/{ref}/{path}"
CANDIDATE_PATHS = ("action.yml", "action.yaml")


def fetch(url: str, timeout: int = 30) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "workflow-validator"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return str(response.read().decode("utf-8"))


def candidate_urls(path: str, ref: str) -> list[str]:
    """Return raw URLs to try for an action path such as owner/repo/subdir.

    An action may live at the repository root (hacs/action) or in a
    subdirectory (home-assistant/actions/hassfest). Both layouts are tried,
    subdirectory first because a 3-segment path is almost always a
    subdirectory action.
    """
    parts = path.split("/")
    urls: list[str] = []
    if len(parts) >= 3:
        urls.extend(
            RAW.format(repo="/".join(parts[:2]), ref=ref, path=f"{'/'.join(parts[2:])}/{name}")
            for name in CANDIDATE_PATHS
        )
    urls.extend(RAW.format(repo=path, ref=ref, path=name) for name in CANDIDATE_PATHS)
    return urls


def fetch_action_yml(path: str, ref: str) -> tuple[str | None, str | None]:
    """Return (action_yml_text, error). action_yml_text is None on failure.

    Only SHA-pinned references are fetched. A tag or branch is a valid
    reference by definition, and resolving one would add a network round trip
    per distinct ref for no benefit.
    """
    if not SHA_RE.match(ref):
        return None, None

    last_error = "no action.yml/action.yaml found"
    for url in candidate_urls(path, ref):
        try:
            return fetch(url), None
        except urllib.error.HTTPError as exc:
            last_error = f"HTTP {exc.code} for {url}"
        except urllib.error.URLError as exc:
            last_error = f"{exc.reason} for {url}"
    return None, last_error


def declared_inputs(text: str) -> set[str] | None:
    """Return the input names an action declares, or None if unparseable."""
    try:
        data: Any = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return None
    inputs = data.get("inputs") if isinstance(data, dict) else None
    if inputs is None:
        return set()
    return set(inputs) if isinstance(inputs, dict) else set()


def iter_steps(node: Any) -> Iterator[dict[str, Any]]:
    """Yield every step mapping found anywhere in the workflow tree."""
    if isinstance(node, dict):
        if isinstance(node.get("uses"), str):
            yield node
        for value in node.values():
            yield from iter_steps(value)
    elif isinstance(node, list):
        for item in node:
            yield from iter_steps(item)


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".github/workflows")
    problems: list[str] = []
    checked: set[tuple[str, str]] = set()

    for path in sorted(root.glob("*.y*ml")):
        try:
            workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            problems.append(f"{path.name}: YAML parse error: {exc}")
            continue

        for step in iter_steps(workflow):
            uses: str = step["uses"].strip()
            if uses.startswith(("./", "docker://")):
                continue

            if "@" not in uses:
                problems.append(f"{path.name}: malformed 'uses' (no @ref): {uses}")
                continue

            action_path, ref = uses.rsplit("@", 1)
            ref = ref.split("#", 1)[0].strip()
            if "/" not in action_path or not ref:
                problems.append(f"{path.name}: malformed 'uses': {uses}")
                continue

            key = (action_path, ref)
            with_block = step.get("with") or {}
            cached = checked.__contains__(key)
            checked.add(key)

            text, err = fetch_action_yml(action_path, ref)
            if err:
                problems.append(f"{path.name}: cannot resolve {action_path}@{ref}: {err}")
                continue
            if text is None:
                continue

            inputs = declared_inputs(text)
            if inputs is None:
                problems.append(f"{path.name}: unparseable action.yml for {action_path}@{ref}")
                continue

            if not cached and isinstance(with_block, dict):
                unknown = sorted(set(with_block) - inputs)
                if unknown:
                    problems.append(f"{path.name}: {action_path}@{ref} has no input(s): {', '.join(unknown)}")

    print(f"Checked {len(checked)} distinct action reference(s) in {root}")
    if problems:
        print("\nProblems found:")
        for item in problems:
            print(f"  * {item}")
        return 1

    print("All action references and inputs are valid.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

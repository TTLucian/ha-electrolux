"""Make the editor re-run mypy after a file changed on disk behind its back.

The mypy editor extension (ms-python.mypy-type-checker) re-analyses a document
when you type, when you save, or when one of its *tracked settings* changes. It
has no file watcher for Python sources, so an edit made from outside the editor -
a formatter, sed, or an agent tool - leaves stale diagnostics in the Problems
panel. That is worse than no checking: the panel can show errors that were fixed
minutes ago while the code is fine.

This nudges the extension through the third trigger. It briefly flips a tracked
setting and puts it back, which produces a genuine configuration change, which
makes the extension re-run mypy on every open document.

`mypy-type-checker.showNotifications` is used because it is cosmetic: toggling
it changes no checking behaviour, and the original value is restored before this
returns, so the repository is left exactly as it was found and git stays clean.

Safe to run at any time; it never edits source.

Usage: python .github/scripts/refresh_editor_types.py
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
SETTINGS = REPO / ".vscode" / "settings.json"

SETTING = '"mypy-type-checker.showNotifications"'


def _parse(text: str) -> dict:
    """Parse JSONC (VS Code settings allow // comments).

    json.loads is typed Any; annotate so the return type is honest.
    """
    data: dict = json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.M))
    return data


def main() -> int:
    if not SETTINGS.exists():
        print(f"::error::no editor settings at {SETTINGS}", file=sys.stderr)
        return 1

    original = SETTINGS.read_text(encoding="utf-8")
    try:
        settings = _parse(original)
    except json.JSONDecodeError as exc:
        print(f"::error::could not parse {SETTINGS.name}: {exc}", file=sys.stderr)
        return 1

    if SETTING not in original:
        print(
            f"::error::{SETTING} is not declared in {SETTINGS.name}, so there is "
            "nothing to nudge and the editor would not be prompted to re-check. "
            "Add the setting to the file, or run 'Mypy: Restart Server' instead.",
            file=sys.stderr,
        )
        return 1

    current = str(settings.get("mypy-type-checker.showNotifications", "off"))
    toggled = "always" if current != "always" else "off"

    # A real value change, so onDidChangeConfiguration actually fires. If the
    # rewrite does not change the bytes, nothing would happen - so refuse rather
    # than report success for a no-op.
    nudged = re.sub(
        rf"({SETTING}\s*:\s*)\"{re.escape(current)}\"",
        rf'\g<1>"{toggled}"',
        original,
    )
    if nudged == original:
        print(
            f"::error::could not rewrite {SETTING}; refusing to claim a re-check that never happened",
            file=sys.stderr,
        )
        return 1

    SETTINGS.write_text(nudged, encoding="utf-8")

    # Give the extension time to observe the change before restoring it, so the
    # two events cannot be coalesced into "no change at all".
    time.sleep(2.0)

    SETTINGS.write_text(original, encoding="utf-8")

    print(
        f"Nudged {SETTING} {current} -> {toggled} and restored it. The editor should now re-run mypy on open documents."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Run actionlint with shellcheck, or fail loudly.

actionlint checks workflow syntax on its own. Its shell-script rules need a
separate program, shellcheck, and when that program is absent actionlint does
not warn and does not fail - it simply checks less and exits 0. That silent
degradation is how an SC2086 (unquoted `$TARGETS` in the mypy step) reached all
three repositories: a local run looked clean because the rule that would have
caught it never executed.

The original setup ran actionlint from a Docker image so the two could never
be separated. That works, but it makes the check unavailable to anyone without
Docker, which is the same silent-degradation problem wearing a different hat.
Here both tools are pinned ordinary dependencies - shellcheck ships inside the
venv via shellcheck-py, actionlint is fetched at a fixed version - so every
caller gets the same complete check, and a missing tool is an error rather
than a weaker result.

Used by CI, by the pre-commit hook and by the editor task, so a local run and a
CI run check exactly the same thing.

Usage: uv run python .github/scripts/run_actionlint.py [workflow_dir]
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.request
from pathlib import Path
from typing import NoReturn

ACTIONLINT_VERSION = "1.7.12"
REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / ".git" / "actionlint"

# actionlint publishes per-platform archives; map this machine onto one.
ASSET = {
    ("Linux", "x86_64"): f"actionlint_{ACTIONLINT_VERSION}_linux_amd64.tar.gz",
    ("Linux", "aarch64"): f"actionlint_{ACTIONLINT_VERSION}_linux_arm64.tar.gz",
    ("Darwin", "x86_64"): f"actionlint_{ACTIONLINT_VERSION}_darwin_amd64.tar.gz",
    ("Darwin", "arm64"): f"actionlint_{ACTIONLINT_VERSION}_darwin_arm64.tar.gz",
}


def die(message: str) -> NoReturn:
    """Fail loudly. A weaker check that still reports success is worse than none."""
    print(f"::error::{message}", file=sys.stderr)
    raise SystemExit(1)


def find_shellcheck() -> str:
    """Locate shellcheck, preferring the pinned copy inside the venv.

    shellcheck-py installs the binary into the venv, so `uv sync` is all it
    takes to have the same version CI uses.
    """
    venv = REPO / ".venv" / "bin" / "shellcheck"
    if venv.exists():
        return str(venv)
    found = shutil.which("shellcheck")
    if found:
        return found
    die(
        "shellcheck was not found, so the workflow shell scripts would not be "
        "checked at all. Run `uv sync --locked` to install the pinned copy that "
        "shellcheck-py provides, or install shellcheck on PATH."
    )


def install_actionlint() -> Path:
    """Return a pinned actionlint, downloading it once into .git/actionlint."""
    key = (platform.system(), platform.machine())
    if key not in ASSET:
        die(f"no pinned actionlint build for {key[0]}/{key[1]}; install actionlint and put it on PATH")

    CACHE.mkdir(parents=True, exist_ok=True)
    binary = CACHE / "actionlint"
    if binary.exists():
        return binary

    asset = ASSET[key]
    url = f"https://github.com/rhysd/actionlint/releases/download/v{ACTIONLINT_VERSION}/{asset}"
    print(f"Fetching actionlint v{ACTIONLINT_VERSION} -> {CACHE}")
    try:
        with urllib.request.urlopen(url, timeout=120) as response:  # noqa: S310
            payload = response.read()
    except OSError as exc:
        die(f"could not download actionlint from {url}: {exc}")

    archive = CACHE / asset
    archive.write_bytes(payload)
    try:
        with tarfile.open(archive) as tar:
            extracted = tar.extractfile("actionlint")
            if extracted is None:
                die(f"the downloaded archive did not contain an actionlint binary: {url}")
            with extracted, binary.open("wb") as dst:
                shutil.copyfileobj(extracted, dst)
    finally:
        archive.unlink(missing_ok=True)
    binary.chmod(0o755)
    return binary


def main() -> int:
    target = sys.argv[1] if len(sys.argv) > 1 else ".github/workflows"

    shellcheck = find_shellcheck()
    actionlint = install_actionlint()

    env = dict(os.environ)
    env["SHELLCHECK_PATH"] = shellcheck
    # Put it on PATH too: actionlint shells out and some code paths ignore
    # SHELLCHECK_PATH.
    env["PATH"] = f"{Path(shellcheck).parent}{os.pathsep}{env.get('PATH', '')}"

    print(f"actionlint v{ACTIONLINT_VERSION}  shellcheck {shellcheck}")
    # actionlint takes file paths, not a directory, so expand the target here.
    root = REPO / target
    if root.is_dir():
        files = sorted(p for p in root.glob("*.y*ml"))
        if not files:
            print(f"No workflow files found in {target}")
            return 0
    else:
        files = [root]

    result = subprocess.run(  # noqa: S603
        [str(actionlint), *(str(f) for f in files)],
        check=False,
        env=env,
        cwd=REPO,
    )
    if result.returncode == 0:
        print("Workflow lint clean (syntax and shell scripts).")
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

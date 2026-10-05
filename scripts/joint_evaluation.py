#!/usr/bin/env python3
"""Isolated Python entry point for the reviewed joint controller."""

import sys

if not (
    sys.flags.isolated
    and sys.flags.dont_write_bytecode
    and sys.pycache_prefix == "/dev/null"
):
    raise SystemExit("Use python -I -B -X pycache_prefix=/dev/null for admission")

import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
git_env = {
    "PATH": os.defpath,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
}


def git(*args):
    return subprocess.check_output(["git", "-C", str(root), *args], env=git_env)


# This must precede any import from the checkout: an untracked native module
# could otherwise shadow the validator itself. Existing timestamp bytecode
# cannot execute under the mandatory cache-prefix flags checked above.
if git("diff", "--name-only", "HEAD").strip():
    raise SystemExit("source checkout changed before controller import")
extras = git("ls-files", "--others", "--exclude-standard", "-z") + git(
    "ls-files", "--others", "--ignored", "--exclude-standard", "-z"
)
for raw in extras.split(b"\0"):
    path = Path(os.fsdecode(raw))
    if path.suffix in (".py", ".pyc", ".pth", ".so", ".dylib", ".pyd", ".pyw") and not (
        path.suffix == ".pyc" and "__pycache__" in path.parts
    ):
        raise SystemExit("untracked importable source refused before controller import")

sys.path.insert(0, str(root))
from tests.joint_evaluation import main  # noqa: E402 - validate before checkout imports

if __name__ == "__main__":
    raise SystemExit(main())

"""Fail when tracked files contain unresolved git merge markers."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

EXCLUDED_PATHS = ("frontend/node_modules/**",)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=".",
        help="Repository root to scan. Defaults to current directory.",
    )
    args = parser.parse_args()

    repo_root = Path(args.root).resolve()
    grep_cmd = [
        "git",
        "-C",
        str(repo_root),
        "grep",
        "-n",
        "--no-color",
        "-I",
        "-E",
        r"^(<<<<<<< .+|=======|>>>>>>> .+)$",
        "--",
        ".",
    ]
    grep_cmd.extend(f":(exclude){path}" for path in EXCLUDED_PATHS)

    result = subprocess.run(
        grep_cmd,
        capture_output=True,
        text=True,
        check=False,
    )

    # git grep returns:
    # 0 when matches exist, 1 when no matches, >1 on errors.
    if result.returncode == 0:
        print("unresolved merge markers detected:")
        for line in result.stdout.splitlines():
            print(f"  {line}")
        return 1
    if result.returncode == 1:
        print("no unresolved merge markers detected")
        return 0

    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    print("merge-marker scan failed", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

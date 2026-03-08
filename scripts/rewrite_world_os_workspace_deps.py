#!/usr/bin/env python3
"""Rewrite @world-os package ranges to workspace:* for CI fallback installs."""

from __future__ import annotations

import argparse
import glob
import json
from pathlib import Path


DEFAULT_PATTERNS = [
    "apps/*/package.json",
    "packages/*/package.json",
    "ui/**/package.json",
    "api/**/package.json",
    "tools/**/package.json",
]


def rewrite(root: Path, patterns: list[str]) -> int:
    changed = 0
    for pattern in patterns:
        for rel_path in glob.glob(pattern, root_dir=str(root), recursive=True):
            path = root / rel_path
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                continue

            dirty = False
            for section in (
                "dependencies",
                "devDependencies",
                "optionalDependencies",
                "peerDependencies",
            ):
                deps = data.get(section)
                if not isinstance(deps, dict):
                    continue
                for name, version in list(deps.items()):
                    if name.startswith("@world-os/") and not str(version).startswith(
                        "workspace:"
                    ):
                        deps[name] = "workspace:*"
                        dirty = True

            if dirty:
                path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                changed += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--patterns", nargs="+", default=DEFAULT_PATTERNS)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    changed = rewrite(repo_root, args.patterns)
    print(f"Updated {changed} package manifest(s) for @world-os workspace fallback.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

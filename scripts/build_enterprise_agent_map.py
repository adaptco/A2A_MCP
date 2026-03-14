#!/usr/bin/env python3
"""Compile enterprise agent map XML into runtime JSON artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from a2a_mcp.blackmamba.enterprise_map import compile_enterprise_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map-path", default=str(REPO_ROOT / "specs" / "enterprise_agent_map.xml"))
    parser.add_argument("--root-path", default="C:\\")
    parser.add_argument("--agents-memory")
    parser.add_argument("--skills-memory")
    parser.add_argument("--antigravity-root", default=str(REPO_ROOT.parents[2] / ".antigravity"))
    parser.add_argument("--org-github-root", default=str(REPO_ROOT.parent / ".github"))
    parser.add_argument("--skip-external-sync", action="store_true")
    args = parser.parse_args()

    result = compile_enterprise_artifacts(
        map_path=args.map_path,
        repo_root=REPO_ROOT,
        root_path=args.root_path,
        agents_memory_path=args.agents_memory,
        skills_memory_path=args.skills_memory,
        antigravity_root=args.antigravity_root,
        org_github_root=args.org_github_root,
        skip_external_sync=args.skip_external_sync,
    )

    print(json.dumps(result["generated_paths"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

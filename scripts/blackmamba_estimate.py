#!/usr/bin/env python3
"""Emit a BlackMamba task estimate from the canonical enterprise map."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from a2a_mcp.blackmamba.planner import AgentBlackMamba


def _csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--objective", required=True)
    parser.add_argument("--complexity", type=float, default=0.55)
    parser.add_argument("--risk", type=float, default=0.4)
    parser.add_argument("--interfaces", default="frontier-registry,github-actions-control,antigravity-hitl")
    parser.add_argument("--dependencies", default="")
    parser.add_argument("--root-path", default="C:\\")
    parser.add_argument("--map-path", default=str(REPO_ROOT / "specs" / "enterprise_agent_map.xml"))
    parser.add_argument("--output")
    args = parser.parse_args()

    planner = AgentBlackMamba(
        repo_root=REPO_ROOT,
        root_path=args.root_path,
        enterprise_map_path=args.map_path,
    )
    estimate = planner.estimate_task(
        objective=args.objective,
        complexity=args.complexity,
        risk=args.risk,
        interfaces=_csv_list(args.interfaces),
        dependencies=_csv_list(args.dependencies),
    ).to_dict()

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(estimate, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(estimate, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

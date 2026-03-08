"""Generate deterministic entropy/enthalpy route decisions for coding agents."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from agent_style_entropy import build_style_temperature_plan


def _parse_skills(raw: str) -> Sequence[str]:
    values = [item.strip() for item in raw.split(",")]
    return [value for value in values if value]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prompt", required=True, help="Task description to route.")
    parser.add_argument(
        "--risk-profile",
        default="medium",
        choices=("low", "medium", "high"),
        help="Risk profile used in enthalpy tuning.",
    )
    parser.add_argument(
        "--changed-path-count",
        type=int,
        default=1,
        help="Approximate number of changed paths used for pressure estimation.",
    )
    parser.add_argument(
        "--api-skills",
        default="",
        help="Optional comma-separated override for API skill names.",
    )
    args = parser.parse_args()

    api_skills = _parse_skills(args.api_skills) if args.api_skills else ()
    kwargs = {
        "prompt": args.prompt,
        "risk_profile": args.risk_profile,
        "changed_path_count": max(1, args.changed_path_count),
    }
    if api_skills:
        kwargs["api_skills"] = api_skills
    payload = build_style_temperature_plan(**kwargs)
    print(json.dumps(payload, indent=2, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

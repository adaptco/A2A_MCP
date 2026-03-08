"""CLI entrypoint to build a multimodal worldline block artifact."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.multimodal_worldline import build_worldline_block, serialize_worldline_block


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Qube multimodal worldline block")
    parser.add_argument("--prompt", required=True, help="Root prompt for worldline generation")
    parser.add_argument("--repository", required=True, help="Repository identifier (owner/repo)")
    parser.add_argument("--commit-sha", required=True, help="Commit SHA")
    parser.add_argument("--actor", default="github-actions", help="Actor initiating the run")
    parser.add_argument("--cluster-count", type=int, default=4, help="Number of artifact clusters")
    parser.add_argument("--output", default="worldline_block.json", help="Output JSON path")
    args = parser.parse_args()

    block = build_worldline_block(
        prompt=args.prompt,
        repository=args.repository,
        commit_sha=args.commit_sha,
        actor=args.actor,
        cluster_count=args.cluster_count,
    )

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialize_worldline_block(block), encoding="utf-8")
    print(f"Worldline block written to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

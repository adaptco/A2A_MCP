"""CLI entrypoint to execute the full end-to-end worldline orchestration."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.end_to_end_orchestration import EndToEndOrchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description="Run end-to-end worldline orchestration")
    parser.add_argument("--prompt", required=True, help="Prompt to orchestrate")
    parser.add_argument("--repository", required=True, help="Repository identifier")
    parser.add_argument("--commit-sha", required=True, help="Commit SHA")
    parser.add_argument("--actor", default="github-actions", help="Initiator actor")
    parser.add_argument("--cluster-count", type=int, default=4, help="Artifact cluster count")
    parser.add_argument("--authorization", default="Bearer valid-token", help="Auth token header value")
    parser.add_argument("--mcp-api-url", default=None, help="Optional remote MCP API URL")
    parser.add_argument("--output-block", default="worldline_block.json", help="Worldline block output path")
    parser.add_argument(
        "--output-result",
        default="orchestration_result.json",
        help="Orchestration result output path",
    )
    args = parser.parse_args()

    orchestrator = EndToEndOrchestrator(
        prompt=args.prompt,
        repository=args.repository,
        commit_sha=args.commit_sha,
        actor=args.actor,
        cluster_count=args.cluster_count,
        authorization=args.authorization,
        mcp_api_url=args.mcp_api_url,
        output_block_path=args.output_block,
        output_result_path=args.output_result,
    )
    result = orchestrator.run()
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

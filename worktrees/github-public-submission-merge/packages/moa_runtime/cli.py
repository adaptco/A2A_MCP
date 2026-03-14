import argparse
import json
from typing import List

from .state_machine import run_moa
from .types import RunContext


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="MoA runtime CLI")
    parser.add_argument("--registry", required=True, help="Path to agent registry JSON")
    parser.add_argument("--policy", required=True, help="Path to routing policy JSON")
    parser.add_argument("--manifest", required=True, help="Path to index manifest JSON")
    parser.add_argument("--pg-dsn", required=True, help="Postgres DSN for pgvector store")
    parser.add_argument("--project", required=True, help="Project ID")
    parser.add_argument("--vertical", required=True, help="Vertical ID")
    parser.add_argument("--intent", required=True, help="Intent string")
    parser.add_argument("--query", required=True, help="User query")
    parser.add_argument("--expert-catalog", default="registry/experts/expert_catalog.v1.json", help="Path to expert catalog")
    parser.add_argument("--query-embedding-json", help="Optional query embedding JSON array override")
    parser.add_argument(
        "--preamble",
        default="docs/prompt/system_preamble.md",
        help="Path to system preamble markdown",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    query_embedding: List[float] = json.loads(args.query_embedding_json) if args.query_embedding_json else None

    ctx = RunContext(
        project_id=args.project,
        vertical_id=args.vertical,
        intent=args.intent,
        query=args.query,
        registry_ref=args.registry,
    )

    result = run_moa(
        ctx=ctx,
        registry_path=args.registry,
        routing_policy_path=args.policy,
        expert_catalog_path=args.expert_catalog,
        preamble_path=args.preamble,
        manifest_path=args.manifest,
        pg_dsn=args.pg_dsn,
        query_embedding=query_embedding,
    )

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

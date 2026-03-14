"""Build CI/CD multimodal RAG workflow artifacts for GitHub Actions."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.multimodal_rag_workflow import (  # noqa: E402
    build_workflow_bundle,
    serialize_json,
    validate_bundle,
)
from orchestrator.multimodal_worldline import (  # noqa: E402
    build_worldline_block,
    serialize_worldline_block,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build multimodal RAG CI/CD logic-tree workflow bundle",
    )
    parser.add_argument("--prompt", required=True, help="Worldline prompt")
    parser.add_argument("--repository", required=True, help="Repository owner/name")
    parser.add_argument("--commit-sha", required=True, help="Commit SHA")
    parser.add_argument("--actor", default="github-actions", help="Initiator actor")
    parser.add_argument("--cluster-count", type=int, default=4, help="Cluster count")
    parser.add_argument("--top-k", type=int, default=3, help="Token matches per node")
    parser.add_argument(
        "--min-similarity",
        type=float,
        default=0.10,
        help="Gate-open cosine similarity threshold",
    )
    parser.add_argument(
        "--output-dir",
        default="build/multimodal_rag",
        help="Output directory for JSON artifacts",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any node gate remains closed",
    )
    return parser.parse_args()


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(serialize_json(payload), encoding="utf-8")


def main() -> int:
    args = parse_args()

    worldline = build_worldline_block(
        prompt=args.prompt,
        repository=args.repository,
        commit_sha=args.commit_sha,
        actor=args.actor,
        cluster_count=args.cluster_count,
    )
    bundle = build_workflow_bundle(
        worldline,
        top_k=args.top_k,
        min_similarity=args.min_similarity,
    )
    validation_errors = validate_bundle(bundle)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Keep a first-class worldline artifact for interoperability with existing jobs.
    (out_dir / "worldline_block.json").write_text(
        serialize_worldline_block(worldline),
        encoding="utf-8",
    )
    write_json(out_dir / "multimodal_rag_logic_tree.json", {"logic_tree": bundle["logic_tree"]})
    write_json(out_dir / "token_reconstruction.json", bundle["token_reconstruction"])
    write_json(out_dir / "workflow_actions.json", {"workflow_actions": bundle["workflow_actions"]})
    write_json(
        out_dir / "multimodal_rag_workflow_bundle.json",
        {
            "bundle": bundle,
            "validation_errors": validation_errors,
            "strict_mode": args.strict,
        },
    )

    print(f"Artifacts written to {out_dir}")
    print(f"Nodes: {len(bundle['logic_tree'])}")
    print(f"Vector store size: {bundle['token_reconstruction']['vector_store_size']}")
    print(f"Validation errors: {len(validation_errors)}")
    if validation_errors:
        for error in validation_errors:
            print(f" - {error}")

    if args.strict and validation_errors:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

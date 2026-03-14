import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def _canonical_json(data: Dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def _read_json(path: Optional[str]) -> Optional[Dict]:
    if not path:
        return None
    json_path = Path(path)
    if not json_path.exists():
        return None
    return json.loads(json_path.read_text(encoding="utf-8"))


def _collect_threads(chunk_set: Path) -> List[Dict]:
    return [json.loads(line) for line in chunk_set.read_text(encoding="utf-8").splitlines() if line.strip()]


def _compute_contract_hash(manifest: Dict, agent_path: Optional[str], policy_path: Optional[str], expert_path: Optional[str]) -> Optional[str]:
    agent = _read_json(agent_path)
    policy = _read_json(policy_path)
    expert = _read_json(expert_path)
    if not agent or not policy or not expert:
        return None
    manifest_copy = dict(manifest)
    manifest_copy.pop("contract_hash", None)
    material = _canonical_json(agent) + _canonical_json(policy) + _canonical_json(expert) + _canonical_json(manifest_copy)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_manifest(project_id: str, vertical_id: str, corpus_id: str, chunk_set: Path, agent_path: Optional[str], policy_path: Optional[str], expert_path: Optional[str]) -> Dict:
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    manifest_id = f"manifest:rag:{project_id}:{vertical_id}:{timestamp}"
    threads = _collect_threads(chunk_set)
    source_hashes = sorted({t.get("source_hash", "") for t in threads if t.get("source_hash")})
    manifest: Dict = {
        "manifest_id": manifest_id,
        "version": "v1",
        "created_at": datetime.utcnow().isoformat() + "Z",
        "source_snapshot_ref": f"local:ssot:data/corpus/threads/{project_id}/{vertical_id}",
        "chunk_set_ref": str(chunk_set),
        "embedding": {
            "model": "local.hash-embed.v1",
            "dimension": 1536,
            "normalize": True
        },
        "vector_index": {
            "provider": "pgvector",
            "collection": "thread_embeddings",
            "distance": "cosine"
        },
        "retrieval": {
            "top_k": 8,
            "min_score": 0.25,
            "metric": "cosine"
        },
        "eval_profile": {
            "name": "rag_standard",
            "passed_gates": [
                "schema_valid",
                "retrieval_smoke"
            ]
        },
        "provenance": {
            "source_hashes": source_hashes,
            "build_id": timestamp
        },
        "corpus_id": corpus_id,
        "project_id": project_id,
        "vertical_id": vertical_id,
        "chunk_set": {
            "count": len(threads),
            "thread_ids_sample": [t["thread_id"] for t in threads[:3]]
        }
    }
    manifest["contract_hash"] = _compute_contract_hash(manifest, agent_path, policy_path, expert_path)
    return manifest


def write_manifest(manifest: Dict, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp_path = output_dir / f"{manifest['manifest_id'].split(':')[-1]}.json"
    with timestamp_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    current_path = output_dir / "CURRENT.json"
    current_path.write_text(timestamp_path.read_text(encoding="utf-8"), encoding="utf-8")
    return current_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build RAG manifest")
    parser.add_argument("--project", required=True, help="Project ID")
    parser.add_argument("--vertical", required=True, help="Vertical ID")
    parser.add_argument("--corpus", required=True, help="Corpus ID")
    parser.add_argument("--chunk-set", required=True, help="Path to threads JSONL")
    parser.add_argument(
        "--output-dir",
        default="manifests/rag/qube_core/simulation",
        help="Output directory for manifest",
    )
    parser.add_argument("--agent-registry-path", help="Path to agent registry for contract hash")
    parser.add_argument("--routing-policy-path", help="Path to routing policy for contract hash")
    parser.add_argument("--expert-catalog-path", help="Path to expert catalog for contract hash")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = build_manifest(
        args.project,
        args.vertical,
        args.corpus,
        Path(args.chunk_set),
        args.agent_registry_path,
        args.routing_policy_path,
        args.expert_catalog_path,
    )
    write_manifest(manifest, Path(args.output_dir))


if __name__ == "__main__":
    main()

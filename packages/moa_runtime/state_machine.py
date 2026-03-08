from typing import Any, Dict, List, Optional

from . import manifest_loader, registry_loader, retriever, router
from .contracts import compute_contract_hash
from .prompt_bundle import assemble_prompt
from .types import ContextBundle, RunContext


def run_moa(
    ctx: RunContext,
    registry_path: str,
    routing_policy_path: str,
    expert_catalog_path: str,
    preamble_path: str,
    manifest_path: str,
    pg_dsn: str,
    query_embedding: Optional[List[float]] = None,
) -> Dict[str, Any]:
    registry = registry_loader.load_registry(registry_path)
    agent = registry_loader.select_agent(registry, ctx.project_id, ctx.vertical_id)
    if not agent:
        raise ValueError("No agent found for provided project/vertical")

    routing_policy = registry_loader.load_registry(routing_policy_path)
    expert_catalog = registry_loader.load_registry(expert_catalog_path)
    manifest = manifest_loader.load_manifest(manifest_path)

    expected_hash = manifest.get("contract_hash")
    computed_hash = compute_contract_hash(registry, routing_policy, expert_catalog, manifest)
    if expected_hash and expected_hash != computed_hash:
        raise ValueError("Contract hash mismatch; manifest does not match registry/routing/experts")

    if query_embedding is not None:
        manifest["query_embedding"] = query_embedding

    retrieval_cfg = manifest.get("retrieval", {})
    top_k = retrieval_cfg.get("top_k", 5)
    min_score = retrieval_cfg.get("min_score", float("inf"))

    bundle: ContextBundle = retriever.retrieve(
        pg_dsn=pg_dsn,
        manifest=manifest,
        query=ctx.query,
        top_k=top_k,
        min_score=min_score,
    )

    experts = router.route_experts(routing_policy, ctx.intent)
    if not bundle.chunks:
        return {
            "agent_id": agent["agent_id"],
            "manifest_id": manifest.get("manifest_id"),
            "experts": experts,
            "status": "INSUFFICIENT_CONTEXT",
            "prompt": "",
            "retrieved_thread_ids": [],
        }

    prompt = assemble_prompt(
        ctx=ctx,
        preamble_path=preamble_path,
        bundle=bundle,
        output_contract=agent["prompt_contract"]["output_contract"],
    )

    return {
        "agent_id": agent["agent_id"],
        "manifest_id": manifest.get("manifest_id"),
        "experts": experts,
        "prompt": prompt,
        "retrieved_thread_ids": [chunk.thread_id for chunk in bundle.chunks],
        "status": "OK",
    }

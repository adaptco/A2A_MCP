"""CI/CD logic-tree orchestration for multimodal RAG token reconstruction."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List

from orchestrator.multimodal_worldline import deterministic_embedding


@dataclass(frozen=True)
class LogicTreeNode:
    """A CI/CD node that consumes reconstructed token context."""

    node_id: str
    phase: str
    query: str
    allowed_actions: List[str]


@dataclass(frozen=True)
class VectorTokenMatch:
    """Semantic match between a query and a token indexed in the vector store."""

    token_id: str
    token: str
    score: float
    cluster: str


class MultimodalVectorStore:
    """
    Deterministic local vector index for token reconstruction.

    This adapter keeps CI workflows hermetic by reconstructing token context from
    the worldline payload without external vector database dependencies.
    """

    def __init__(self, dimensions: int = 32) -> None:
        self.dimensions = int(dimensions)
        self._points: Dict[str, Dict[str, Any]] = {}

    def upsert(self, *, token_id: str, token: str, cluster: str) -> None:
        self._points[token_id] = {
            "token_id": token_id,
            "token": token,
            "cluster": cluster,
            "vector": deterministic_embedding(token, dimensions=self.dimensions),
        }

    def query(self, *, text: str, top_k: int = 3) -> List[VectorTokenMatch]:
        query_vector = deterministic_embedding(text, dimensions=self.dimensions)
        scored: List[VectorTokenMatch] = []

        for point in self._points.values():
            score = _cosine_similarity(query_vector, point["vector"])
            scored.append(
                VectorTokenMatch(
                    token_id=point["token_id"],
                    token=point["token"],
                    score=score,
                    cluster=point["cluster"],
                )
            )

        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[: max(1, int(top_k))]

    @property
    def size(self) -> int:
        return len(self._points)

    @classmethod
    def from_worldline_block(
        cls,
        worldline_block: Dict[str, Any],
        dimensions: int = 32,
    ) -> "MultimodalVectorStore":
        store = cls(dimensions=dimensions)
        infra = worldline_block.get("infrastructure_agent", {})
        token_stream = infra.get("token_stream", [])
        cluster_map = _token_cluster_map(infra.get("artifact_clusters", {}))

        for entry in token_stream:
            token = str(entry.get("token", "")).strip()
            token_id = str(entry.get("token_id", "")).strip()
            if not token or not token_id:
                continue
            store.upsert(
                token_id=token_id,
                token=token,
                cluster=cluster_map.get(token, "cluster_unassigned"),
            )

        return store


def build_cicd_logic_tree(worldline_block: Dict[str, Any]) -> List[LogicTreeNode]:
    """Build a deterministic CI/CD logic tree for multimodal RAG artifacts."""
    prompt = str(worldline_block.get("prompt", "")).strip()
    repository = str(worldline_block.get("repository", "unknown/repo")).strip()

    return [
        LogicTreeNode(
            node_id="N0_INGRESS",
            phase="idle_to_scheduled",
            query=f"{prompt} intake token normalization for {repository}",
            allowed_actions=["validate_intake_token", "hold_in_idle"],
        ),
        LogicTreeNode(
            node_id="N1_PLANNING",
            phase="scheduled_to_executing",
            query=f"{prompt} skill routing and blueprint planning",
            allowed_actions=["dispatch_planning_artifacts", "retry_dispatch"],
        ),
        LogicTreeNode(
            node_id="N2_RAG_CONTEXT",
            phase="executing_context_reconstruction",
            query=f"{prompt} reconstruct multimodal rag context from vector tokens",
            allowed_actions=["hydrate_runtime_context", "retry_vector_lookup"],
        ),
        LogicTreeNode(
            node_id="N3_EXECUTION",
            phase="executing_to_evaluating",
            query=f"{prompt} coder execution with grounded context",
            allowed_actions=["execute_kernel_action", "retry_dispatch"],
        ),
        LogicTreeNode(
            node_id="N4_VALIDATION",
            phase="evaluating",
            query=f"{prompt} tester validation and decision scoring",
            allowed_actions=["score_and_commit_verdict", "retry_dispatch"],
        ),
        LogicTreeNode(
            node_id="N5_RELEASE",
            phase="evaluating_to_terminated",
            query=f"{prompt} release bundle and ledger traceability",
            allowed_actions=["publish_release_bundle", "escalate_manual_review"],
        ),
    ]


def reconstruct_tokens_for_nodes(
    worldline_block: Dict[str, Any],
    *,
    top_k: int = 3,
    min_similarity: float = 0.10,
) -> Dict[str, Any]:
    """
    Reconstruct token context at each CI/CD logic-tree node using vector search.
    """
    store = MultimodalVectorStore.from_worldline_block(worldline_block)
    nodes = build_cicd_logic_tree(worldline_block)

    node_results: List[Dict[str, Any]] = []
    for node in nodes:
        matches = store.query(text=node.query, top_k=top_k) if store.size else []
        gate_open = bool(matches) and matches[0].score >= min_similarity
        selected_action = _select_action(node.allowed_actions, gate_open)

        node_results.append(
            {
                "node_id": node.node_id,
                "phase": node.phase,
                "query": node.query,
                "gate_open": gate_open,
                "selected_action": selected_action,
                "matches": [
                    {
                        "token_id": match.token_id,
                        "token": match.token,
                        "cluster": match.cluster,
                        "score": round(match.score, 6),
                    }
                    for match in matches
                ],
            }
        )

    return {
        "pipeline": "multimodal-rag-cicd-logic-tree",
        "repository": worldline_block.get("repository"),
        "commit_sha": worldline_block.get("commit_sha"),
        "vector_store_size": store.size,
        "min_similarity": float(min_similarity),
        "top_k": int(top_k),
        "nodes": node_results,
    }


def build_workflow_bundle(
    worldline_block: Dict[str, Any],
    *,
    top_k: int = 3,
    min_similarity: float = 0.10,
) -> Dict[str, Any]:
    """Build a full CI/CD bundle for GitHub Actions artifact publishing."""
    logic_tree = build_cicd_logic_tree(worldline_block)
    reconstruction = reconstruct_tokens_for_nodes(
        worldline_block,
        top_k=top_k,
        min_similarity=min_similarity,
    )

    workflow_actions = [
        {
            "node_id": node["node_id"],
            "phase": node["phase"],
            "action": node["selected_action"],
            "gate_open": node["gate_open"],
        }
        for node in reconstruction["nodes"]
    ]

    return {
        "worldline": worldline_block,
        "logic_tree": [
            {
                "node_id": node.node_id,
                "phase": node.phase,
                "query": node.query,
                "allowed_actions": node.allowed_actions,
            }
            for node in logic_tree
        ],
        "token_reconstruction": reconstruction,
        "workflow_actions": workflow_actions,
    }


def validate_bundle(bundle: Dict[str, Any]) -> List[str]:
    """Return validation errors for bundle completeness; empty list means valid."""
    errors: List[str] = []
    reconstruction = bundle.get("token_reconstruction", {})
    nodes = reconstruction.get("nodes", [])
    if not nodes:
        errors.append("token_reconstruction.nodes is empty")
        return errors

    for node in nodes:
        if not node.get("gate_open"):
            errors.append(
                f"node {node.get('node_id')} gate is closed; action={node.get('selected_action')}"
            )
        if not node.get("selected_action"):
            errors.append(f"node {node.get('node_id')} missing selected_action")

    return errors


def serialize_json(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=True)


def _token_cluster_map(artifact_clusters: Dict[str, Iterable[str]]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for cluster, artifacts in artifact_clusters.items():
        for artifact in artifacts:
            value = str(artifact)
            if value.startswith("artifact::"):
                token = value.split("artifact::", 1)[1]
            else:
                token = value
            mapping[token] = cluster
    return mapping


def _select_action(allowed_actions: List[str], gate_open: bool) -> str:
    if not allowed_actions:
        return "no_action_defined"
    if gate_open:
        return allowed_actions[0]
    if len(allowed_actions) > 1:
        return allowed_actions[1]
    return "escalate_manual_review"


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

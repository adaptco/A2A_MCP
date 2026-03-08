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
class AgenticPhaseStage:
    """Stage template for routing query->plan->execution across control layers."""

    stage_id: str
    from_phase: str
    to_phase: str
    control_layer: str
    owner_agent: str
    objective: str
    node_id: str


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
            "vector": _normalize_vector(
                deterministic_embedding(token, dimensions=self.dimensions)
            ),
        }

    def query(self, *, text: str, top_k: int = 3) -> List[VectorTokenMatch]:
        query_vector = _normalize_vector(
            deterministic_embedding(text, dimensions=self.dimensions)
        )
        scored: List[VectorTokenMatch] = []

        for point in self._points.values():
            score = _normalized_dot_product(query_vector, point["vector"])
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


def build_agentic_phase_stages() -> List[AgenticPhaseStage]:
    """
    Canonical phase loop for query processing through the agentic control layer.

    The stages map query intent into managing/orchestration/coding flow, then
    into runtime validation where tokens are treated as physical objects.
    """
    return [
        AgenticPhaseStage(
            stage_id="S0_QUERY_INGRESS",
            from_phase="IDLE",
            to_phase="SCHEDULED",
            control_layer="query_processor",
            owner_agent="ManagingAgent",
            objective="Parse query and extract planning intent.",
            node_id="N0_INGRESS",
        ),
        AgenticPhaseStage(
            stage_id="S1_PLAN_HANDOFF",
            from_phase="SCHEDULED",
            to_phase="EXECUTING",
            control_layer="agentic_control_layer",
            owner_agent="ManagingAgent",
            objective="Dispatch project plan for orchestration oversight.",
            node_id="N1_PLANNING",
        ),
        AgenticPhaseStage(
            stage_id="S2_ORCHESTRATION_MAPPING",
            from_phase="EXECUTING",
            to_phase="EXECUTING",
            control_layer="orchestration_layer",
            owner_agent="OrchestrationAgent",
            objective="Map plan steps to executable orchestrator actions.",
            node_id="N2_RAG_CONTEXT",
        ),
        AgenticPhaseStage(
            stage_id="S3_CICD_INFRA_BUILD",
            from_phase="EXECUTING",
            to_phase="EVALUATING",
            control_layer="coding_layer",
            owner_agent="CoderAgent",
            objective="Build CI/CD infrastructure artifacts for tokenized workloads.",
            node_id="N3_EXECUTION",
        ),
        AgenticPhaseStage(
            stage_id="S4_TOKEN_PHYSICS_SIM",
            from_phase="EVALUATING",
            to_phase="EVALUATING",
            control_layer="game_runtime_layer",
            owner_agent="GameRuntimeAgent",
            objective="Project tokens as physical objects in the simulated runtime.",
            node_id="N4_VALIDATION",
        ),
        AgenticPhaseStage(
            stage_id="S5_RELEASE_HANDOFF",
            from_phase="EVALUATING",
            to_phase="TERMINATED_SUCCESS",
            control_layer="release_layer",
            owner_agent="OrchestrationAgent",
            objective="Commit release handoff for runtime deployment.",
            node_id="N5_RELEASE",
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


def model_agentic_phase_loop(
    worldline_block: Dict[str, Any],
    *,
    top_k: int = 3,
    min_similarity: float = 0.10,
) -> Dict[str, Any]:
    """
    Build a staged loop with explicit phase changes and control-layer ownership.

    This loop is designed for runtime handoff payloads where each stage can
    route token context to the responsible agent and surface game-physics token
    objects for simulation-aware execution.
    """
    reconstruction = reconstruct_tokens_for_nodes(
        worldline_block,
        top_k=top_k,
        min_similarity=min_similarity,
    )
    stage_templates = build_agentic_phase_stages()
    node_by_id = {node["node_id"]: node for node in reconstruction["nodes"]}

    stage_rows: List[Dict[str, Any]] = []
    blocked_stages: List[str] = []

    for idx, stage in enumerate(stage_templates, start=1):
        node = node_by_id.get(stage.node_id, {})
        gate_open = bool(node.get("gate_open"))
        if not gate_open:
            blocked_stages.append(stage.stage_id)

        matches = node.get("matches", [])
        runtime_objects = [
            _token_match_to_runtime_object(
                match=match,
                stage_index=idx,
                object_index=object_index,
            )
            for object_index, match in enumerate(matches, start=1)
        ]

        stage_rows.append(
            {
                "step": idx,
                "stage_id": stage.stage_id,
                "phase_change": {
                    "from": stage.from_phase,
                    "to": stage.to_phase,
                },
                "control_layer": stage.control_layer,
                "owner_agent": stage.owner_agent,
                "objective": stage.objective,
                "node_id": stage.node_id,
                "gate_open": gate_open,
                "selected_action": node.get("selected_action", "escalate_manual_review"),
                "plan_message": _build_plan_message(stage=stage, gate_open=gate_open),
                "token_objects": runtime_objects,
            }
        )

    exit_phase = "TERMINATED_SUCCESS" if not blocked_stages else "TERMINATED_FAIL"
    return {
        "loop_id": "agentic-phase-loop.v1",
        "entry_phase": "IDLE",
        "exit_phase": exit_phase,
        "blocked_stages": blocked_stages,
        "stages": stage_rows,
        "vector_store_size": reconstruction["vector_store_size"],
        "repository": reconstruction["repository"],
        "commit_sha": reconstruction["commit_sha"],
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
    phase_loop = model_agentic_phase_loop(
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
        "agentic_phase_loop": phase_loop,
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


def _build_plan_message(stage: AgenticPhaseStage, gate_open: bool) -> str:
    state = "ready" if gate_open else "blocked"
    return (
        f"{stage.owner_agent} in {stage.control_layer} is {state} to "
        f"{stage.objective.lower()}"
    )


def _token_match_to_runtime_object(
    *,
    match: Dict[str, Any],
    stage_index: int,
    object_index: int,
) -> Dict[str, Any]:
    token_id = str(match.get("token_id", "tok-unknown"))
    token = str(match.get("token", "")).strip()
    cluster = str(match.get("cluster", "cluster_unassigned"))
    score = float(match.get("score", 0.0))
    seed = _stable_seed(token_id, token)

    mass = round(0.75 + (len(token) % 8) * 0.2, 3)
    friction = round(0.1 + (seed % 25) / 100.0, 3)
    restitution = round(0.1 + (seed % 30) / 100.0, 3)
    drag = round(0.05 + (seed % 15) / 100.0, 3)
    runtime_backend = "unity" if score >= 0.5 else "threejs"

    return {
        "object_id": f"obj::{token_id}",
        "token_id": token_id,
        "token": token,
        "cluster": cluster,
        "score": round(score, 6),
        "runtime_backend": runtime_backend,
        "physics": {
            "mass": mass,
            "friction": friction,
            "restitution": restitution,
            "drag": drag,
        },
        "transform": {
            "x": round(stage_index * 2.0 + object_index * 0.35, 3),
            "y": round(0.5 + (seed % 12) * 0.1, 3),
            "z": round(object_index * 0.75, 3),
        },
    }


def _stable_seed(token_id: str, token: str) -> int:
    value = f"{token_id}:{token}".encode("utf-8")
    return sum((idx + 1) * byte for idx, byte in enumerate(value))


def _select_action(allowed_actions: List[str], gate_open: bool) -> str:
    if not allowed_actions:
        return "no_action_defined"
    if gate_open:
        return allowed_actions[0]
    if len(allowed_actions) > 1:
        return allowed_actions[1]
    return "escalate_manual_review"


def _normalize_vector(values: List[float]) -> List[float]:
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0.0:
        return [0.0 for _ in values]
    return [value / norm for value in values]


def _normalized_dot_product(a: List[float], b: List[float]) -> float:
    a_norm = _normalize_vector(a)
    b_norm = _normalize_vector(b)
    return sum(x * y for x, y in zip(a_norm, b_norm))


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

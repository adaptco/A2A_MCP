"""Runtime bridge helpers for orchestration MCP -> runtime MCP handoff."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from orchestrator.multimodal_rag_workflow import build_workflow_bundle
from orchestrator.multimodal_worldline import (
    build_worldline_block,
    cluster_artifacts,
    deterministic_embedding,
    lora_attention_weights,
    token_to_id,
    tokenize_prompt,
)
from schemas.agent_artifacts import MCPArtifact
from schemas.model_artifact import AgentLifecycleState, LoRAConfig, ModelArtifact
from schemas.runtime_bridge import (
    KernelVectorControlModel,
    RuntimeAssignmentV1,
    RuntimeBridgeMetadata,
    RuntimeWorkerAssignment,
)


class MCPHandshakeConfig(BaseModel):
    provider: str = Field(default="github-mcp")
    tool_name: str = Field(default="ingest_worldline_block")
    api_key: Optional[str] = Field(default=None)
    endpoint: Optional[str] = Field(default=None)


class AgentOnboardingSpec(BaseModel):
    agent_name: str
    model_id: str = Field(default="gpt-4o-mini")
    embedding_dim: int = Field(default=32, ge=8)
    fidelity: Literal["auto", "high", "low"] = Field(default="auto")
    role: str = Field(default="worker")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RuntimeHandshakeSpec(BaseModel):
    wasm_shell: bool = Field(default=True)
    engine: str = Field(default="WASD GameEngine")
    unity_profile: str = Field(default="unity_lora_worker")
    three_profile: str = Field(default="threejs_compact_worker")


class HandshakeInitRequest(BaseModel):
    prompt: str
    repository: str
    commit_sha: str
    actor: str = Field(default="api_user")
    plan_id: Optional[str] = Field(default=None)
    cluster_count: int = Field(default=4, ge=1)
    top_k: int = Field(default=3, ge=1)
    min_similarity: float = Field(default=0.10, ge=0.0, le=1.0)
    token_stream: List[Dict[str, Any]] = Field(default_factory=list)
    agent_specs: List[AgentOnboardingSpec] = Field(default_factory=list)
    mcp: MCPHandshakeConfig
    runtime: RuntimeHandshakeSpec = Field(default_factory=RuntimeHandshakeSpec)


def fingerprint_secret(secret: str) -> str:
    digest = hashlib.sha256(secret.encode("utf-8")).hexdigest()
    return digest[:16]


def _resolve_fidelity(spec: AgentOnboardingSpec) -> Literal["high", "low"]:
    if spec.fidelity == "high":
        return "high"
    if spec.fidelity == "low":
        return "low"
    return "high" if spec.embedding_dim >= 256 else "low"


def _default_agent_specs() -> List[AgentOnboardingSpec]:
    return [
        AgentOnboardingSpec(
            agent_name="OrchestrationAgent",
            model_id="gpt-4o-mini",
            embedding_dim=128,
            fidelity="auto",
            role="manager",
        ),
        AgentOnboardingSpec(
            agent_name="GameRuntimeAgent",
            model_id="threejs-compact-model",
            embedding_dim=32,
            fidelity="auto",
            role="worker",
        ),
    ]


def _normalize_token_stream(
    prompt: str, raw_stream: List[Dict[str, Any]]
) -> List[Dict[str, str]]:
    normalized: List[Dict[str, str]] = []
    seen: set[str] = set()

    source_tokens: List[Dict[str, Any]]
    if raw_stream:
        source_tokens = raw_stream
    else:
        source_tokens = [{"token": token} for token in tokenize_prompt(prompt)]

    for idx, entry in enumerate(source_tokens):
        raw_value = str(entry.get("token") or entry.get("value") or "").strip().lower()
        token = " ".join(raw_value.split())
        if not token or token in seen:
            continue
        seen.add(token)

        token_id = str(entry.get("token_id") or "").strip()
        if not token_id:
            token_id = token_to_id(token, idx)

        normalized.append({"token": token, "token_id": token_id})

    if not normalized:
        fallback = tokenize_prompt(prompt) or ["default"]
        for idx, token in enumerate(fallback):
            normalized.append({"token": token, "token_id": token_to_id(token, idx)})

    return normalized


def _hydrate_worldline_with_tokens(
    worldline: Dict[str, Any],
    token_stream: List[Dict[str, str]],
    cluster_count: int,
) -> None:
    infra = worldline.setdefault("infrastructure_agent", {})
    infra["token_stream"] = token_stream

    artifacts = [f"artifact::{entry['token']}" for entry in token_stream]
    clusters = cluster_artifacts(artifacts, cluster_count=cluster_count)
    infra["artifact_clusters"] = clusters
    infra["lora_attention_weights"] = lora_attention_weights(clusters)

    token_text = " ".join(entry["token"] for entry in token_stream)
    infra["embedding_vector"] = deterministic_embedding(
        token_text or worldline.get("prompt", ""),
        dimensions=32,
    )


def _build_worker_assignments(
    specs: List[AgentOnboardingSpec],
    runtime: RuntimeHandshakeSpec,
    mcp: MCPHandshakeConfig,
    api_key_fingerprint: str,
) -> List[RuntimeWorkerAssignment]:
    workers: List[RuntimeWorkerAssignment] = []
    for idx, spec in enumerate(specs, start=1):
        fidelity = _resolve_fidelity(spec)
        if fidelity == "high":
            runtime_target = runtime.unity_profile
            render_backend = "unity"
            deployment_mode = "lora_training"
        else:
            runtime_target = runtime.three_profile
            render_backend = "threejs"
            deployment_mode = "compact_runtime"

        workers.append(
            RuntimeWorkerAssignment(
                worker_id=f"worker-{idx:02d}-{spec.agent_name.lower()}",
                agent_name=spec.agent_name,
                role=spec.role,
                fidelity=fidelity,
                runtime_target=runtime_target,
                deployment_mode=deployment_mode,
                render_backend=render_backend,
                runtime_shell="wasm",
                metadata=spec.metadata,
                mcp={
                    "provider": mcp.provider,
                    "tool_name": mcp.tool_name,
                    "endpoint": mcp.endpoint,
                    "api_key_fingerprint": api_key_fingerprint,
                },
            )
        )
    return workers


def _onboard_agents_as_stateful_artifacts(
    *,
    db_manager: Any,
    plan_id: str,
    commit_sha: str,
    token_stream: List[Dict[str, str]],
    workers: List[RuntimeWorkerAssignment],
    specs: List[AgentOnboardingSpec],
) -> List[Dict[str, Any]]:
    onboarded: List[Dict[str, Any]] = []

    for spec, worker in zip(specs, workers):
        fidelity = _resolve_fidelity(spec)
        lora_config = None
        if fidelity == "high":
            lora_config = LoRAConfig(
                rank=16,
                alpha=32.0,
                target_modules=["q_proj", "k_proj", "v_proj"],
                training_samples=max(16, len(token_stream) * 8),
            )

        weights_hash = hashlib.sha256(
            f"{spec.model_id}:{commit_sha}:{spec.embedding_dim}".encode("utf-8")
        ).hexdigest()

        init_artifact = ModelArtifact(
            artifact_id=f"model-{uuid.uuid4().hex[:10]}",
            model_id=spec.model_id,
            weights_hash=f"sha256:{weights_hash}",
            embedding_dim=spec.embedding_dim,
            state=AgentLifecycleState.INIT,
            agent_name=spec.agent_name,
            lora_config=lora_config,
            content=json.dumps(
                {
                    "plan_id": plan_id,
                    "worker_id": worker.worker_id,
                    "runtime_target": worker.runtime_target,
                    "token_stream_size": len(token_stream),
                },
                ensure_ascii=True,
            ),
            metadata={
                "role": spec.role,
                "fidelity": fidelity,
                "runtime_shell": worker.runtime_shell,
                "deployment_mode": worker.deployment_mode,
            },
        )
        embedding_artifact = init_artifact.transition(AgentLifecycleState.EMBEDDING)

        db_manager.save_artifact(init_artifact)
        db_manager.save_artifact(embedding_artifact)

        onboarded.append(
            {
                "agent_name": spec.agent_name,
                "worker_id": worker.worker_id,
                "init_artifact_id": init_artifact.artifact_id,
                "embedding_artifact_id": embedding_artifact.artifact_id,
                "runtime_target": worker.runtime_target,
                "fidelity": fidelity,
            }
        )

    return onboarded


def _build_runtime_state(runtime: RuntimeHandshakeSpec) -> Dict[str, Any]:
    return {
        "wasm_shell": {
            "enabled": runtime.wasm_shell,
            "entrypoint": "wasm://a2a/wasd-game-engine",
            "engine": runtime.engine,
        },
        "unity": {
            "profile": runtime.unity_profile,
            "purpose": "high_fidelity_lora_training",
        },
        "threejs": {
            "profile": runtime.three_profile,
            "purpose": "low_dimensional_runtime_compaction",
        },
    }


def _build_kernel_model(
    *,
    plan_id: str,
    token_stream: List[Dict[str, str]],
) -> KernelVectorControlModel:
    return KernelVectorControlModel(
        kernel_id=f"kernel-{plan_id}",
        vector_namespace=f"a2a.manifold.{plan_id}",
        release_channel="stable",
        api_token_env_var="A2A_MCP_API_TOKEN",
        release_control={
            "required_phase": "ready_for_release",
            "token_stream_normalized": True,
            "minimum_token_count": max(1, len(token_stream)),
        },
        spec_refs=[
            "INDEX.md",
            "KERNEL_MODEL_SPEC.md",
            "MANIFOLD_VECTOR_RELEASE_SPEC.md",
        ],
    )


def _build_runtime_assignment(
    *,
    payload: HandshakeInitRequest,
    handshake_id: str,
    plan_id: str,
    runtime_state: Dict[str, Any],
    workers: List[RuntimeWorkerAssignment],
    token_stream: List[Dict[str, str]],
    workflow_actions: List[Dict[str, Any]],
    onboarded_artifacts: List[Dict[str, Any]],
    api_key_fingerprint: str,
    kernel_model: KernelVectorControlModel,
    runtime_bridge_metadata: RuntimeBridgeMetadata,
) -> RuntimeAssignmentV1:
    token_stream_stats = {
        "count": len(token_stream),
        "unique_count": len({entry.get("token") for entry in token_stream}),
        "normalized": True,
    }
    orchestration_state = {
        "phase": "scheduled",
        "selected_actions": workflow_actions,
        "handshake_ready": True,
    }
    return RuntimeAssignmentV1(
        assignment_id=f"rtassign-{uuid.uuid4().hex[:12]}",
        handshake_id=handshake_id,
        plan_id=plan_id,
        repository=payload.repository,
        commit_sha=payload.commit_sha,
        actor=payload.actor,
        prompt=payload.prompt,
        runtime=runtime_state,
        workers=workers,
        token_stream=token_stream,
        token_stream_stats=token_stream_stats,
        stateful_artifacts=onboarded_artifacts,
        orchestration_state=orchestration_state,
        kernel_model=kernel_model,
        runtime_bridge_metadata=runtime_bridge_metadata,
        mcp={
            "provider": payload.mcp.provider,
            "tool_name": payload.mcp.tool_name,
            "endpoint": payload.mcp.endpoint,
            "api_key_fingerprint": api_key_fingerprint,
        },
    )


def _build_runtime_bridge_metadata(
    *,
    plan_id: str,
    handshake_id: str,
    workers: List[RuntimeWorkerAssignment],
    token_stream: List[Dict[str, str]],
    kernel_model: KernelVectorControlModel,
) -> RuntimeBridgeMetadata:
    return RuntimeBridgeMetadata(
        handshake_id=handshake_id,
        plan_id=plan_id,
        token_stream_normalized=bool(token_stream),
        runtime_workers_ready=len(workers),
        kernel_model_written=True,
        release_channel=kernel_model.release_channel,
    )


def build_handshake_bundle(
    *,
    db_manager: Any,
    payload: HandshakeInitRequest,
    plan_id: str,
    handshake_id: str,
    api_key_fingerprint: str,
) -> Dict[str, Any]:
    """Build runtime handshake payload and persist bridge artifacts."""
    specs = payload.agent_specs or _default_agent_specs()
    normalized_tokens = _normalize_token_stream(payload.prompt, payload.token_stream)

    worldline_block = build_worldline_block(
        prompt=payload.prompt,
        repository=payload.repository,
        commit_sha=payload.commit_sha,
        actor=payload.actor,
        cluster_count=payload.cluster_count,
    )
    _hydrate_worldline_with_tokens(
        worldline_block,
        token_stream=normalized_tokens,
        cluster_count=payload.cluster_count,
    )

    workflow_bundle = build_workflow_bundle(
        worldline_block,
        top_k=payload.top_k,
        min_similarity=payload.min_similarity,
    )
    workers = _build_worker_assignments(
        specs,
        runtime=payload.runtime,
        mcp=payload.mcp,
        api_key_fingerprint=api_key_fingerprint,
    )
    onboarded = _onboard_agents_as_stateful_artifacts(
        db_manager=db_manager,
        plan_id=plan_id,
        commit_sha=payload.commit_sha,
        token_stream=normalized_tokens,
        workers=workers,
        specs=specs,
    )

    runtime_state = _build_runtime_state(payload.runtime)
    kernel_model = _build_kernel_model(
        plan_id=plan_id,
        token_stream=normalized_tokens,
    )
    runtime_bridge_metadata = _build_runtime_bridge_metadata(
        plan_id=plan_id,
        handshake_id=handshake_id,
        workers=workers,
        token_stream=normalized_tokens,
        kernel_model=kernel_model,
    )
    runtime_assignment = _build_runtime_assignment(
        payload=payload,
        handshake_id=handshake_id,
        plan_id=plan_id,
        runtime_state=runtime_state,
        workers=workers,
        token_stream=normalized_tokens,
        workflow_actions=workflow_bundle["workflow_actions"],
        onboarded_artifacts=onboarded,
        api_key_fingerprint=api_key_fingerprint,
        kernel_model=kernel_model,
        runtime_bridge_metadata=runtime_bridge_metadata,
    )
    runtime_assignment_artifact = MCPArtifact(
        artifact_id=f"bridge-{uuid.uuid4().hex[:12]}",
        parent_artifact_id=plan_id,
        agent_name="OrchestrationAgent",
        type="runtime.assignment.v1",
        content=runtime_assignment.model_dump(mode="json"),
        metadata=runtime_bridge_metadata.model_dump(mode="json"),
    )
    db_manager.save_artifact(runtime_assignment_artifact)

    return {
        "normalized_token_stream": normalized_tokens,
        "workers": [worker.model_dump(mode="json") for worker in workers],
        "onboarded_artifacts": onboarded,
        "runtime": runtime_state,
        "mcp": {
            "provider": payload.mcp.provider,
            "tool_name": payload.mcp.tool_name,
            "endpoint": payload.mcp.endpoint,
            "api_key_fingerprint": api_key_fingerprint,
        },
        "token_reconstruction": workflow_bundle["token_reconstruction"],
        "workflow_actions": workflow_bundle["workflow_actions"],
        "kernel_model": kernel_model.model_dump(mode="json"),
        "runtime_bridge_metadata": runtime_bridge_metadata.model_dump(mode="json"),
        "worldline_block": worldline_block,
        "runtime_assignment_artifact": runtime_assignment_artifact.model_dump(mode="json"),
    }

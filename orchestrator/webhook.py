from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException, Body, Header
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
from orchestrator.stateflow import StateMachine
from orchestrator.utils import extract_plan_id_from_path
from orchestrator.storage import save_plan_state
from orchestrator.storage import DBManager
from orchestrator.intent_engine import IntentEngine
from schemas.model_artifact import AgentLifecycleState, LoRAConfig, ModelArtifact

app = FastAPI(title="A2A MCP Webhook")

# in-memory map (replace with DB-backed persistence or plan state store in prod)
PLAN_STATE_MACHINES = {}


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

def persistence_callback(plan_id: str, state_dict: dict) -> None:
    """Callback to persist FSM state to database."""
    try:
        save_plan_state(plan_id, state_dict)
    except Exception as e:
        print(f"Warning: Failed to persist plan state for {plan_id}: {e}")


def _fingerprint_secret(secret: str) -> str:
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


def _normalize_token_stream(prompt: str, raw_stream: List[Dict[str, Any]]) -> List[Dict[str, str]]:
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
    infra["embedding_vector"] = deterministic_embedding(token_text or worldline.get("prompt", ""), dimensions=32)


def _build_worker_assignments(
    specs: List[AgentOnboardingSpec],
    runtime: RuntimeHandshakeSpec,
    mcp: MCPHandshakeConfig,
    api_key_fingerprint: str,
) -> List[Dict[str, Any]]:
    workers: List[Dict[str, Any]] = []
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
            {
                "worker_id": f"worker-{idx:02d}-{spec.agent_name.lower()}",
                "agent_name": spec.agent_name,
                "role": spec.role,
                "fidelity": fidelity,
                "runtime_target": runtime_target,
                "deployment_mode": deployment_mode,
                "render_backend": render_backend,
                "runtime_shell": "wasm",
                "mcp": {
                    "provider": mcp.provider,
                    "tool_name": mcp.tool_name,
                    "endpoint": mcp.endpoint,
                    "api_key_fingerprint": api_key_fingerprint,
                },
            }
        )
    return workers


def _onboard_agents_as_stateful_artifacts(
    *,
    plan_id: str,
    commit_sha: str,
    token_stream: List[Dict[str, str]],
    workers: List[Dict[str, Any]],
    specs: List[AgentOnboardingSpec],
) -> List[Dict[str, Any]]:
    db = DBManager()
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
                    "worker_id": worker["worker_id"],
                    "runtime_target": worker["runtime_target"],
                    "token_stream_size": len(token_stream),
                },
                ensure_ascii=True,
            ),
            metadata={
                "role": spec.role,
                "fidelity": fidelity,
                "runtime_shell": worker["runtime_shell"],
                "deployment_mode": worker["deployment_mode"],
            },
        )
        embedding_artifact = init_artifact.transition(AgentLifecycleState.EMBEDDING)

        db.save_artifact(init_artifact)
        db.save_artifact(embedding_artifact)

        onboarded.append(
            {
                "agent_name": spec.agent_name,
                "worker_id": worker["worker_id"],
                "init_artifact_id": init_artifact.artifact_id,
                "embedding_artifact_id": embedding_artifact.artifact_id,
                "runtime_target": worker["runtime_target"],
                "fidelity": fidelity,
            }
        )

    return onboarded


def _resolve_plan_id(path_plan_id: str | None, payload: dict) -> str | None:
    if path_plan_id:
        return path_plan_id.strip()

    plan_id = payload.get("plan_id")
    if plan_id:
        return str(plan_id).strip()

    plan_file_path = payload.get("plan_file_path", "")
    extracted = extract_plan_id_from_path(plan_file_path)
    return extracted.strip() if extracted else None


async def _plan_ingress_impl(path_plan_id: str | None, payload: dict):
    """
    Accepts either:
      - /plans/ingress with JSON body: {"plan_id": "..."} or {"plan_file_path": "..."}
      - /plans/{plan_id}/ingress with optional JSON body
    """
    plan_id = _resolve_plan_id(path_plan_id, payload or {})
    if not plan_id:
        raise HTTPException(status_code=400, detail="Unable to determine plan_id; provide plan_id or plan_file_path")

    sm = PLAN_STATE_MACHINES.get(plan_id)
    if not sm:
        sm = StateMachine(max_retries=3, persistence_callback=persistence_callback)
        sm.plan_id = plan_id
        PLAN_STATE_MACHINES[plan_id] = sm

    rec = sm.trigger("OBJECTIVE_INGRESS")
    return {"status": "scheduled", "plan_id": plan_id, "transition": rec.to_dict()}


@app.post("/plans/ingress")
async def plan_ingress(payload: dict = Body(...)):
    return await _plan_ingress_impl(None, payload)


@app.post("/plans/{plan_id}/ingress")
async def plan_ingress_by_id(plan_id: str, payload: dict = Body(default={})):
    return await _plan_ingress_impl(plan_id, payload)


@app.post("/handshake/init")
async def initialize_handshake(
    payload: HandshakeInitRequest = Body(...),
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Initialize MCP handshake with full state payload and worker/runtime onboarding.

    This endpoint:
    1. Initializes stateflow handshake state.
    2. Normalizes CI/CD token stream at orchestration layer.
    3. Reconstructs node token context from vector store logic tree.
    4. Onboards agents as stateful embedding artifacts.
    5. Assigns WASM-shell workers for Unity/Three.js runtime targets.
    """
    api_key = (x_api_key or payload.mcp.api_key or "").strip()
    if not api_key:
        raise HTTPException(status_code=401, detail="API key required for MCP handshake initialization")

    api_key_fingerprint = _fingerprint_secret(api_key)
    specs = payload.agent_specs or _default_agent_specs()

    plan_id = (payload.plan_id or "").strip() or f"plan-{uuid.uuid4().hex[:10]}"
    handshake_id = f"hs-{uuid.uuid4().hex[:12]}"

    sm = PLAN_STATE_MACHINES.get(plan_id)
    if not sm:
        sm = StateMachine(max_retries=3, persistence_callback=persistence_callback)
        sm.plan_id = plan_id
        PLAN_STATE_MACHINES[plan_id] = sm

    transition = None
    if sm.current_state().value == "IDLE":
        transition = sm.trigger(
            "OBJECTIVE_INGRESS",
            actor=payload.actor,
            handshake_id=handshake_id,
        ).to_dict()

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
        plan_id=plan_id,
        commit_sha=payload.commit_sha,
        token_stream=normalized_tokens,
        workers=workers,
        specs=specs,
    )

    runtime_state = {
        "wasm_shell": {
            "enabled": payload.runtime.wasm_shell,
            "entrypoint": "wasm://a2a/wasd-game-engine",
            "engine": payload.runtime.engine,
        },
        "unity": {
            "profile": payload.runtime.unity_profile,
            "purpose": "high_fidelity_lora_training",
        },
        "threejs": {
            "profile": payload.runtime.three_profile,
            "purpose": "low_dimensional_runtime_compaction",
        },
    }

    state_payload = {
        "handshake_id": handshake_id,
        "plan_id": plan_id,
        "state_machine": sm.to_dict(),
        "transition": transition,
        "normalized_token_stream": normalized_tokens,
        "workers": workers,
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
        "worldline_block": worldline_block,
    }

    return {
        "status": "handshake_initialized",
        "message": "Agents onboarded as stateful embedding artifacts.",
        "state_payload": state_payload,
    }


@app.post("/orchestrate")
async def orchestrate(user_query: str):
    """
    Triggers the full A2A pipeline (Managing->Orchestration->Architecture->Coder->Tester).
    Matches the contract expected by mcp_server.py.
    """
    engine = IntentEngine()
    # Run the pipeline in background or wait?
    # For MVP synchronous wait is acceptable, though blocking.
    # The mcp_server.py expects a response.
    
    try:
        result = await engine.run_full_pipeline(description=user_query, requester="api_user")
        
        # Summarize results
        summary = {
            "status": "A2A Workflow Complete",
            "success": result.success,
            "pipeline_results": {
                "plan_id": result.plan.plan_id,
                "blueprint_id": result.blueprint.plan_id,
                "code_artifacts": [a.artifact_id for a in result.code_artifacts],
            },
            # Return last code artifact content as 'final_code' for the MCP tool
            "final_code": result.code_artifacts[-1].content if result.code_artifacts else None,
            "test_summary": f"Passed: {sum(1 for v in result.test_verdicts if v['status'] == 'PASS')}/{len(result.test_verdicts)}"
        }
        return summary
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

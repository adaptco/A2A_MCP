from __future__ import annotations

from functools import lru_cache
from typing import Any

import numpy as np
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.mcp_tooling import TELEMETRY
from app.security.oidc import RejectionReason, validate_ingestion_claims
from multi_client_router import (
    ClientNotFound,
    ContaminationError,
    InMemoryEventStore,
    MultiClientMCPRouter,
    QuotaExceededError,
)
from runtime_scenario_service import RuntimeScenarioService

app = FastAPI(title="A2A MCP Multi-Client API")


class StreamRequest(BaseModel):
    tokens: list[float] = Field(default_factory=list)
    runtime_hints: dict[str, Any] = Field(default_factory=dict)
    execution_id: str | None = None
    avatar_id: str = Field(default="unknown")
    oidc_claims: dict[str, Any] = Field(default_factory=dict)


class RagContextRequest(BaseModel):
    top_k: int = Field(default=5, ge=1, le=20)
    query_tokens: list[float] = Field(default_factory=list)


class LoRADatasetRequest(BaseModel):
    pvalue_threshold: float = Field(default=0.10, gt=0.0, lt=1.0)
    candidate_tokens: list[float] = Field(default_factory=list)


@lru_cache(maxsize=1)
def get_router() -> MultiClientMCPRouter:
    return MultiClientMCPRouter(store=InMemoryEventStore())


@lru_cache(maxsize=1)
def get_runtime_service() -> RuntimeScenarioService:
    return RuntimeScenarioService()


@app.post("/mcp/register")
async def register_client(api_key: str, quota: int = 1_000_000, router: MultiClientMCPRouter = Depends(get_router)) -> dict[str, str]:
    tenant_id = await router.register_client(api_key=api_key, quota=quota)
    client_key = next(k for k, p in router.pipelines.items() if p.ctx.tenant_id == tenant_id)
    return {"tenant_id": tenant_id, "client_key": client_key}


@app.post("/mcp/{client_id}/baseline")
async def set_baseline(
    client_id: str,
    request: StreamRequest,
    router: MultiClientMCPRouter = Depends(get_router),
) -> dict[str, str]:
    try:
        await router.set_client_baseline(client_id, np.asarray(request.tokens, dtype=float))
        return {"status": "baseline_set", "client_id": client_id}
    except ClientNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/mcp/{client_id}/stream")
async def stream_orchestration(
    client_id: str,
    request: StreamRequest,
    router: MultiClientMCPRouter = Depends(get_router),
    runtime_service: RuntimeScenarioService = Depends(get_runtime_service),
) -> dict[str, object]:
    timer = TELEMETRY.start_timer()
    avatar_id = request.avatar_id or "unknown"
    client_pipe = router.pipelines.get(client_id)
    quota = client_pipe.ctx.token_quota if client_pipe else 0
    projected_total = (client_pipe._tokens_processed if client_pipe else 0) + len(request.tokens)

    validation = validate_ingestion_claims(
        client_id=client_id,
        avatar_id=avatar_id,
        claims=request.oidc_claims,
        token_vector=request.tokens,
        projected_token_total=projected_total,
        quota=quota,
    )

    if not validation.accepted:
        reason = validation.reason or RejectionReason.MISSING_FIELD
        TELEMETRY.record_request_outcome(
            avatar_id=avatar_id,
            client_id=client_id,
            outcome="rejected",
            rejection_reason=reason.value,
        )
        raise HTTPException(status_code=401, detail={"reason": reason.value})

    try:
        result = await router.process_request(client_id, np.asarray(request.tokens, dtype=float))
        envelope = runtime_service.create_scenario(
            tenant_id=result["client_ctx"].tenant_id,
            client_id=client_id,
            tokens=np.asarray(result["result"], dtype=float),
            runtime_hints=request.runtime_hints,
            execution_id=request.execution_id,
        )
        TELEMETRY.record_request_outcome(
            avatar_id=avatar_id,
            client_id=client_id,
            outcome="accepted",
            rejection_reason=None,
        )
        TELEMETRY.observe_protected_ingestion_latency(timer, client_id=client_id)
        return {
            "tenant_id": result["client_ctx"].tenant_id,
            "drift": result["drift"],
            "sovereignty_hash": result["sovereignty_hash"],
            "result": result["result"].tolist(),
            "execution_id": envelope.execution_id,
            "envelope_hash": envelope.hash_current,
            "embedding_dim": envelope.embedding_dim,
        }
    except ContaminationError as exc:
        TELEMETRY.record_request_outcome(
            avatar_id=avatar_id,
            client_id=client_id,
            outcome="rejected",
            rejection_reason=RejectionReason.CLAIM_MISMATCH.value,
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ClientNotFound as exc:
        TELEMETRY.record_request_outcome(
            avatar_id=avatar_id,
            client_id=client_id,
            outcome="rejected",
            rejection_reason=RejectionReason.MISSING_FIELD.value,
        )
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except QuotaExceededError as exc:
        TELEMETRY.record_request_outcome(
            avatar_id=avatar_id,
            client_id=client_id,
            outcome="rejected",
            rejection_reason=RejectionReason.QUOTA_EXCEEDED.value,
        )
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@app.post("/a2a/runtime/{client_id}/scenario")
async def build_runtime_scenario(
    client_id: str,
    request: StreamRequest,
    router: MultiClientMCPRouter = Depends(get_router),
    runtime_service: RuntimeScenarioService = Depends(get_runtime_service),
) -> dict[str, Any]:
    try:
        result = await router.process_request(client_id, np.asarray(request.tokens, dtype=float))
        envelope = runtime_service.create_scenario(
            tenant_id=result["client_ctx"].tenant_id,
            client_id=client_id,
            tokens=np.asarray(result["result"], dtype=float),
            runtime_hints=request.runtime_hints,
            execution_id=request.execution_id,
        )
        return envelope.model_dump(mode="json")
    except ContaminationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ClientNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except QuotaExceededError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/a2a/scenario/{execution_id}/rag-context")
async def build_rag_context(
    execution_id: str,
    request: RagContextRequest,
    runtime_service: RuntimeScenarioService = Depends(get_runtime_service),
) -> dict[str, Any]:
    try:
        envelope = runtime_service.build_rag_context(
            execution_id=execution_id,
            top_k=request.top_k,
            query_tokens=(
                np.asarray(request.query_tokens, dtype=float)
                if request.query_tokens
                else None
            ),
        )
        return envelope.model_dump(mode="json")
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/a2a/scenario/{execution_id}/lora-dataset")
async def build_lora_dataset(
    execution_id: str,
    request: LoRADatasetRequest,
    runtime_service: RuntimeScenarioService = Depends(get_runtime_service),
) -> dict[str, Any]:
    try:
        return runtime_service.build_lora_dataset(
            execution_id=execution_id,
            pvalue_threshold=request.pvalue_threshold,
            candidate_tokens=(
                np.asarray(request.candidate_tokens, dtype=float)
                if request.candidate_tokens
                else None
            ),
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        code = 409 if "Drift gate failed" in str(exc) else 400
        raise HTTPException(status_code=code, detail=str(exc)) from exc


@app.get("/a2a/executions/{execution_id}/verify")
async def verify_execution_lineage(
    execution_id: str,
    runtime_service: RuntimeScenarioService = Depends(get_runtime_service),
) -> dict[str, Any]:
    try:
        verification = runtime_service.verify_execution(execution_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if not verification.get("valid", False):
        raise HTTPException(status_code=409, detail=verification)
    return verification

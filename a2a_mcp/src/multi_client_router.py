from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Dict, Protocol
from uuid import uuid4

import numpy as np
import torch
from app.mcp_tooling import TELEMETRY

from drift_suite.drift_metrics import ks_statistic
from mcp_core import MCPCore, MCPResult


class ClientNotFound(KeyError):
    """Raised when a client key has no registered token pipeline."""


class ContaminationError(RuntimeError):
    """Raised when drift check indicates possible cross-client contamination."""


class QuotaExceededError(RuntimeError):
    """Raised when a client exceeds its configured token quota."""


@dataclass(frozen=True)
class ClientContext:
    """Per-client isolation boundary."""

    tenant_id: str
    api_key_hash: str
    token_quota: int
    embedding_namespace: str


class EventStore(Protocol):
    """Minimal store contract used by the multi-client router."""

    async def append_event(
        self,
        tenant_id: str,
        execution_id: str,
        state: str,
        payload: dict[str, Any],
    ) -> None: ...

    async def get_execution(self, tenant_id: str, execution_id: str) -> list[dict[str, Any]]: ...


class InMemoryEventStore:
    """Simple async-compatible event store for local execution and tests."""

    def __init__(self) -> None:
        self._events: dict[tuple[str, str], list[dict[str, Any]]] = {}

    async def append_event(
        self,
        tenant_id: str,
        execution_id: str,
        state: str,
        payload: dict[str, Any],
    ) -> None:
        key = (tenant_id, execution_id)
        self._events.setdefault(key, []).append({"state": state, "payload": payload})

    async def get_execution(self, tenant_id: str, execution_id: str) -> list[dict[str, Any]]:
        return list(self._events.get((tenant_id, execution_id), []))


class ClientTokenPipe:
    """Bifurcated pipeline that isolates token transformations per tenant."""

    CONTAMINATION_THRESHOLD = 0.10

    def __init__(self, store: EventStore, ctx: ClientContext) -> None:
        self.store = store
        self.ctx = ctx
        self._tokens_processed = 0
        self._seen_hash_fingerprints: dict[str, tuple[int, float]] = {}

    async def ingress(self, raw_tokens: np.ndarray) -> np.ndarray:
        raw_tokens = np.asarray(raw_tokens, dtype=float)
        self._enforce_quota(raw_tokens.size)
        namespaced = self._namespace_embedding(raw_tokens)
        embedding_hash = _array_hash(namespaced)
        TELEMETRY.record_token_shaping_stage(
            stage="namespace_projection",
            tenant_id=self.ctx.tenant_id,
            token_count=int(raw_tokens.size),
            embedding_hash=embedding_hash,
        )
        self._check_hash_anomaly(stage="namespace_projection", embedding=namespaced, embedding_hash=embedding_hash)

        await self.store.append_event(
            tenant_id=self.ctx.tenant_id,
            execution_id=f"ingress-{uuid4()}",
            state="TOKEN_INGRESS",
            payload={"embedding_hash": embedding_hash, "token_count": int(raw_tokens.size)},
        )
        return namespaced

    async def egress(self, mcp_result: MCPResult) -> Dict[str, Any]:
        """Client-specific formatting + contamination verification"""
        processed_embedding_np = mcp_result.processed_embedding.squeeze(0).detach().cpu().numpy()
        embedding_hash = _array_hash(processed_embedding_np)

        TELEMETRY.record_token_shaping_stage(
            stage="drift_gate",
            tenant_id=self.ctx.tenant_id,
            token_count=int(processed_embedding_np.size),
            embedding_hash=embedding_hash,
        )

        # 1. DRIFT VERIFICATION (client baseline)
        baseline = await self._load_client_baseline()
        drift = self._compute_drift(baseline, processed_embedding_np)

        if drift > ClientTokenPipe.CONTAMINATION_THRESHOLD:
            await self._quarantine_pipeline(drift)
            raise ContaminationError(f"Drift violation: {drift:.4f}")

        # 2. WITNESSING AND SIGNING
        witness_hash = await self._witness_result(processed_embedding_np)

        # 3. CLIENT-SPECIFIC FORMATING
        client_result = {
            "client_ctx": self.ctx,
            "tenant_id": self.ctx.tenant_id,
            "result": processed_embedding_np,
            "mcp_tensor": processed_embedding_np.tolist(),
            "middleware_roles": mcp_result.arbitration_scores.topk(5).indices.tolist() if hasattr(mcp_result.arbitration_scores, 'topk') else [],
            "protocol_features": mcp_result.protocol_features,
            "drift": drift,
            "sovereignty_hash": witness_hash,
        }

        # 4. EVENT STORE COMMIT (client namespace)
        await self.store.append_event(
            tenant_id=self.ctx.tenant_id,
            execution_id=f"mcp-{uuid4().hex[:8]}",
            state="MCP_PROCESSED",
            payload={
                "mcp_result_hash": mcp_result.execution_hash,
                "drift_score": float(drift),
                "witness_hash": witness_hash,
            },
        )

        return client_result

    def _namespace_embedding(self, embedding: np.ndarray) -> np.ndarray:
        projection = _tenant_projection(self.ctx.tenant_id, embedding.shape)
        return embedding * projection

    def _enforce_quota(self, new_tokens: int) -> None:
        projected_total = self._tokens_processed + new_tokens
        if projected_total > self.ctx.token_quota:
            raise QuotaExceededError(
                f"Client {self.ctx.tenant_id} exceeded quota: {projected_total}>{self.ctx.token_quota}"
            )
        self._tokens_processed = projected_total

    async def _load_client_baseline(self) -> np.ndarray:
        events = await self.store.get_execution(self.ctx.tenant_id, "baseline")
        if not events:
            return np.zeros(1, dtype=float)

        baseline = events[-1]["payload"].get("embedding", [0.0])
        return np.asarray(baseline, dtype=float)

    def _compute_drift(self, baseline: np.ndarray, current: np.ndarray) -> float:
        baseline = np.asarray(baseline, dtype=float).ravel()
        current = np.asarray(current, dtype=float).ravel()

        if baseline.size == 0:
            baseline = np.zeros(1, dtype=float)
        if current.size == 0:
            current = np.zeros(1, dtype=float)

        return ks_statistic(baseline, current)

    async def _witness_result(self, result: np.ndarray) -> str:
        message = result.astype(float).tobytes()
        key = self.ctx.api_key_hash.encode("utf-8")
        digest = hmac.new(key=key, msg=message, digestmod=hashlib.sha256).hexdigest()
        TELEMETRY.record_token_shaping_stage(
            stage="witness_signing",
            tenant_id=self.ctx.tenant_id,
            token_count=int(result.size),
            embedding_hash=digest[:16],
        )
        await self.store.append_event(
            tenant_id=self.ctx.tenant_id,
            execution_id="witness",
            state="RESULT_WITNESSED",
            payload={"witness_hash": digest},
        )
        return digest

    async def _quarantine_pipeline(self, drift: float) -> None:
        # Placeholder for quarantine logic
        print(f"QUARANTINE TRIGGERED for tenant {self.ctx.tenant_id} with drift {drift}")

    def _check_hash_anomaly(self, *, stage: str, embedding: np.ndarray, embedding_hash: str) -> None:
        if not np.all(np.isfinite(embedding)):
            TELEMETRY.record_hash_anomaly(
                tenant_id=self.ctx.tenant_id,
                stage=stage,
                embedding_hash=embedding_hash,
                anomaly="non_finite_output",
            )
            return

        fingerprint = (int(embedding.size), float(np.sum(embedding)))
        existing = self._seen_hash_fingerprints.get(embedding_hash)
        if existing is not None and existing != fingerprint:
            TELEMETRY.record_hash_anomaly(
                tenant_id=self.ctx.tenant_id,
                stage=stage,
                embedding_hash=embedding_hash,
                anomaly="hash_collision_suspected",
            )
        else:
            self._seen_hash_fingerprints[embedding_hash] = fingerprint


class MultiClientMCPRouter:
    """Routes client-specific ingress/egress around a shared MCP core."""

    def __init__(self, store: EventStore) -> None:
        self.store = store
        self.pipelines: dict[str, ClientTokenPipe] = {}
        self.mcp_core = MCPCore()

    async def register_client(self, api_key: str, quota: int = 1_000_000) -> str:
        api_digest = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        short = api_digest[:16]

        ctx = ClientContext(
            tenant_id=f"client-{api_digest[:12]}",
            api_key_hash=short,
            token_quota=quota,
            embedding_namespace=f"client_{api_digest[:8]}_ns",
        )

        self.pipelines[ctx.api_key_hash] = ClientTokenPipe(self.store, ctx)
        return ctx.tenant_id

    async def set_client_baseline(self, client_key: str, baseline: np.ndarray) -> None:
        pipe = self.pipelines.get(client_key)
        if pipe is None:
            raise ClientNotFound(f"Client {client_key} not registered")

        await self.store.append_event(
            tenant_id=pipe.ctx.tenant_id,
            execution_id="baseline",
            state="BASELINE_SET",
            payload={"embedding": np.asarray(baseline, dtype=float).ravel().tolist()},
        )

    async def process_request(self, client_key: str, tokens: np.ndarray) -> dict[str, Any]:
        pipe = self.pipelines.get(client_key)
        if pipe is None:
            raise ClientNotFound(f"Client {client_key} not registered")

        mcp_token = await pipe.ingress(np.asarray(tokens, dtype=float))
        
        # Reshape to (1, 4096) for the MCPCore model
        mcp_token_tensor = torch.from_numpy(mcp_token.reshape(1, -1)).float()
        mcp_result = self.mcp_core(mcp_token_tensor)
        return await pipe.egress(mcp_result)


def _tenant_projection(tenant_id: str, shape: tuple[int, ...]) -> np.ndarray:
    seed = int(hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    return rng.uniform(0.95, 1.05, size=shape)


def _array_hash(arr: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(arr, dtype=float).tobytes()).hexdigest()[:16]

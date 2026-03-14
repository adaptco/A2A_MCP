from __future__ import annotations

import os
import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Dict, Protocol
from uuid import uuid4

import numpy as np
from app.mcp_tooling import TELEMETRY

from drift_suite.drift_metrics import ks_statistic

<<<<<<< HEAD

@dataclass
class LightweightMCPResult:
    processed_embedding: np.ndarray
    arbitration_scores: np.ndarray
    protocol_features: Dict[str, Any]
    execution_hash: str


class DeterministicMCPCore:
    """Cheap fallback MCP core for API/runtime flows that should not depend on torch."""

    hidden_dim = 128
    n_roles = 32

    def __call__(self, namespaced_embedding: np.ndarray) -> LightweightMCPResult:
        source = np.asarray(namespaced_embedding, dtype=float).ravel()
        if source.size == 0:
            source = np.zeros(1, dtype=float)

        expanded = np.resize(source, self.hidden_dim * 8)
        features = expanded.reshape(self.hidden_dim, 8).mean(axis=1)
        norm = np.linalg.norm(features)
        if norm > 0:
            features = features / norm

        role_logits = np.resize(features, self.n_roles * 4).reshape(self.n_roles, 4).mean(axis=1)
        role_logits = role_logits - np.max(role_logits)
        role_exp = np.exp(role_logits)
        arbitration_scores = role_exp / np.clip(np.sum(role_exp), 1e-12, None)

        execution_hash = hashlib.sha256(features.tobytes()).hexdigest()
        return LightweightMCPResult(
            processed_embedding=features.reshape(1, -1),
            arbitration_scores=arbitration_scores,
            protocol_features={
                "similarity_features": np.resize(features, 64).tolist(),
                "feature_norm": float(np.linalg.norm(source)),
            },
            execution_hash=execution_hash,
        )
=======
try:  # pragma: no cover - import guarded for lightweight test environments
    import torch
except ModuleNotFoundError:  # pragma: no cover
    torch = None
>>>>>>> origin/main


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

    async def egress(self, mcp_result: Any) -> Dict[str, Any]:
        """Client-specific formatting + contamination verification"""
        processed_embedding_np = _to_numpy(mcp_result.processed_embedding).reshape(-1)
        embedding_hash = _array_hash(processed_embedding_np)

        TELEMETRY.record_token_shaping_stage(
            stage="drift_gate",
            tenant_id=self.ctx.tenant_id,
            token_count=int(processed_embedding_np.size),
            embedding_hash=embedding_hash,
        )

        arbitration_scores_np = _to_numpy(mcp_result.arbitration_scores).reshape(-1)
        top_roles = (
            np.argsort(arbitration_scores_np)[-5:][::-1].tolist()
            if arbitration_scores_np.size
            else []
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
            "middleware_roles": top_roles,
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
        self.handshake_registry: dict[str, dict[str, Any]] = {}
        self.mcp_core: Any | None = None

    def _get_mcp_core(self) -> Any:
        if self.mcp_core is None:
<<<<<<< HEAD
            if os.getenv("A2A_ROUTER_CORE", "numpy").strip().lower() == "torch":
                import torch
                from mcp_core import MCPCore

                self.mcp_core = ("torch", torch, MCPCore())
            else:
                self.mcp_core = ("numpy", None, DeterministicMCPCore())
=======
            from mcp_core import MCPCore

            self.mcp_core = MCPCore()
>>>>>>> origin/main
        return self.mcp_core

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
        if torch is None:
            raise RuntimeError("torch is required to process MCP requests in multi-client router")

        mcp_token = await pipe.ingress(np.asarray(tokens, dtype=float))
<<<<<<< HEAD
        core_kind, torch_module, core = self._get_mcp_core()

        if core_kind == "torch":
            mcp_token_tensor = torch_module.from_numpy(_project_to_core_width(mcp_token)).float()
            mcp_result = core(mcp_token_tensor)
        else:
            mcp_result = core(mcp_token)
=======
        mcp_core = self._get_mcp_core()

        # Reshape to (1, 4096) for the MCPCore model
        mcp_token_tensor = torch.from_numpy(mcp_token.reshape(1, -1)).float()
        mcp_result = mcp_core(mcp_token_tensor)
>>>>>>> origin/main
        return await pipe.egress(mcp_result)

    def register_handshake(
        self,
        *,
        handshake_id: str,
        client_id: str,
        tenant_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Track handshake state in the router layer for API routing visibility."""

        self.handshake_registry[handshake_id] = {
            "handshake_id": handshake_id,
            "client_id": client_id,
            "tenant_id": tenant_id,
            "status": status,
            "metadata": dict(metadata or {}),
        }

    def update_handshake_status(
        self,
        *,
        handshake_id: str,
        status: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if handshake_id not in self.handshake_registry:
            raise ClientNotFound(f"Handshake {handshake_id} not registered")
        entry = self.handshake_registry[handshake_id]
        entry["status"] = status
        if metadata:
            entry["metadata"] = {**entry.get("metadata", {}), **metadata}

    def get_handshake(self, handshake_id: str) -> dict[str, Any]:
        if handshake_id not in self.handshake_registry:
            raise ClientNotFound(f"Handshake {handshake_id} not registered")
        return dict(self.handshake_registry[handshake_id])


def _tenant_projection(tenant_id: str, shape: tuple[int, ...]) -> np.ndarray:
    seed = int(hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    return rng.uniform(0.95, 1.05, size=shape)


def _array_hash(arr: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(arr, dtype=float).tobytes()).hexdigest()[:16]


def _project_to_core_width(arr: np.ndarray, width: int = 4096) -> np.ndarray:
    source = np.asarray(arr, dtype=float).ravel()
    if source.size == 0:
        source = np.zeros(1, dtype=float)
    return np.resize(source, width).reshape(1, width)


def _to_numpy(value: Any) -> np.ndarray:
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    return np.asarray(value, dtype=float)

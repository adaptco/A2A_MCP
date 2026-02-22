from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any, Protocol
from uuid import uuid4

import numpy as np

from drift_suite.drift_metrics import ks_statistic


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

    def __init__(self, store: EventStore, ctx: ClientContext, drift_threshold: float = 0.10) -> None:
        self.store = store
        self.ctx = ctx
        self.drift_threshold = drift_threshold
        self._tokens_processed = 0

    async def ingress(self, raw_tokens: np.ndarray) -> np.ndarray:
        raw_tokens = np.asarray(raw_tokens, dtype=float)
        self._enforce_quota(raw_tokens.size)
        namespaced = self._namespace_embedding(raw_tokens)

        await self.store.append_event(
            tenant_id=self.ctx.tenant_id,
            execution_id=f"ingress-{uuid4()}",
            state="TOKEN_INGRESS",
            payload={"embedding_hash": _array_hash(namespaced), "token_count": int(raw_tokens.size)},
        )
        return namespaced

    async def egress(self, mcp_result: np.ndarray) -> dict[str, Any]:
        mcp_result = np.asarray(mcp_result, dtype=float)
        baseline = await self._load_client_baseline()
        drift = self._compute_drift(baseline, mcp_result)
        if drift > self.drift_threshold:
            raise ContaminationError(
                f"Drift {drift:.3f} > threshold {self.drift_threshold:.3f} for tenant {self.ctx.tenant_id}"
            )

        witness_hash = await self._witness_result(mcp_result)
        return {
            "client_ctx": self.ctx,
            "result": mcp_result,
            "drift": drift,
            "sovereignty_hash": witness_hash,
        }

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
        await self.store.append_event(
            tenant_id=self.ctx.tenant_id,
            execution_id="witness",
            state="RESULT_WITNESSED",
            payload={"witness_hash": digest},
        )
        return digest


class MultiClientMCPRouter:
    """Routes client-specific ingress/egress around a shared MCP core."""

    def __init__(self, store: EventStore) -> None:
        self.store = store
        self.pipelines: dict[str, ClientTokenPipe] = {}

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
        mcp_result = await self._mcp_core(mcp_token)
        return await pipe.egress(mcp_result)

    async def _mcp_core(self, token: np.ndarray) -> np.ndarray:
        # Shared MCP core placeholder: deterministic normalization + tanh activation.
        scale = max(float(np.linalg.norm(token)), 1.0)
        normalized = token / scale
        return np.tanh(normalized)


def _tenant_projection(tenant_id: str, shape: tuple[int, ...]) -> np.ndarray:
    seed = int(hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)
    return rng.uniform(0.95, 1.05, size=shape)


def _array_hash(arr: np.ndarray) -> str:
    return hashlib.sha256(np.asarray(arr, dtype=float).tobytes()).hexdigest()[:16]

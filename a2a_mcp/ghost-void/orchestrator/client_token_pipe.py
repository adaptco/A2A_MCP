"""Tenant-scoped MCP egress pipe with contamination protection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, Protocol
from uuid import uuid4

import torch
import torch.nn.functional as F

from orchestrator.mcp_core import MCPCore, MCPResult


class ContaminationError(RuntimeError):
    """Raised when drift exceeds the allowed contamination threshold."""


class EventStoreProtocol(Protocol):
    async def append_event(
        self, tenant_id: str, execution_id: str, state: str, payload: Dict[str, Any]
    ) -> None:
        ...


class InMemoryEventStore:
    """Simple async event store for integration tests and local runs."""

    def __init__(self) -> None:
        self.events: list[Dict[str, Any]] = []

    async def append_event(
        self, tenant_id: str, execution_id: str, state: str, payload: Dict[str, Any]
    ) -> None:
        self.events.append(
            {
                "tenant_id": tenant_id,
                "execution_id": execution_id,
                "state": state,
                "payload": payload,
            }
        )


@dataclass
class ClientTokenContext:
    tenant_id: str
    tenant_vector: torch.Tensor | None = None


class ClientTokenPipe:
    """Client-specific formatting + contamination verification."""

    CONTAMINATION_THRESHOLD = 0.10

    def __init__(
        self,
        ctx: ClientTokenContext,
        store: EventStoreProtocol,
        core: MCPCore | None = None,
        baseline_loader: Callable[[], Awaitable[torch.Tensor]] | None = None,
        contamination_threshold: float | None = None,
    ) -> None:
        self.ctx = ctx
        self.store = store
        self.core = core or MCPCore()
        self._baseline_loader = baseline_loader
        self.quarantined = False
        self._baseline: torch.Tensor | None = None
        self.threshold = (
            float(contamination_threshold)
            if contamination_threshold is not None
            else self.CONTAMINATION_THRESHOLD
        )

    async def _load_client_baseline(self) -> torch.Tensor | None:
        if self._baseline_loader is None:
            return self._baseline

        baseline = await self._baseline_loader()
        if baseline.dim() == 1:
            baseline = baseline.unsqueeze(0)
        if baseline.dim() != 2 or baseline.shape[0] != 1:
            raise ValueError("Baseline tensor must have shape [1, D] or [D]")
        return baseline.float()

    def _compute_drift(self, baseline: torch.Tensor, embedding: torch.Tensor) -> float:
        if baseline.shape != embedding.shape:
            raise ValueError(
                f"Baseline shape {tuple(baseline.shape)} must match embedding shape {tuple(embedding.shape)}"
            )
        similarity = F.cosine_similarity(baseline, embedding, dim=-1)
        return float(1.0 - similarity.mean().item())

    async def _quarantine_pipeline(self, drift: float) -> None:
        self.quarantined = True
        await self.store.append_event(
            tenant_id=self.ctx.tenant_id,
            execution_id=f"mcp-{uuid4().hex[:8]}",
            state="MCP_QUARANTINED",
            payload={"drift_score": float(drift)},
        )

    @property
    def is_quarantined(self) -> bool:
        return self.quarantined

    def _namespace_projection(self, raw_embedding: torch.Tensor) -> torch.Tensor:
        if raw_embedding.dim() == 1:
            raw_embedding = raw_embedding.unsqueeze(0)
        if raw_embedding.dim() != 2 or raw_embedding.shape[0] != 1:
            raise ValueError("raw_embedding must have shape [1, D] or [D]")

        tenant_vector = self.ctx.tenant_vector
        if tenant_vector is None:
            return raw_embedding.float()

        tenant_vector = tenant_vector.float()
        if tenant_vector.dim() == 2 and tenant_vector.shape[0] == 1:
            tenant_vector = tenant_vector.squeeze(0)
        if tenant_vector.dim() != 1:
            raise ValueError("tenant_vector must have shape [D] or [1, D]")
        if tenant_vector.shape[0] != raw_embedding.shape[1]:
            raise ValueError(
                f"tenant_vector width {tenant_vector.shape[0]} must match embedding width {raw_embedding.shape[1]}"
            )
        return raw_embedding.float() * F.normalize(tenant_vector, dim=0).unsqueeze(0)

    async def process(self, raw_embedding: torch.Tensor) -> Dict[str, Any]:
        """Run namespace projection + MCPCore + tenant-safe egress formatting."""
        if self.quarantined:
            raise ContaminationError("Pipeline is quarantined")
        namespaced_embedding = self._namespace_projection(raw_embedding)
        return await self.egress(self.core(namespaced_embedding))

    async def egress(self, mcp_result: MCPResult) -> Dict[str, Any]:
        """Client-specific formatting + contamination verification."""
        baseline = await self._load_client_baseline()
        if baseline is None:
            baseline = mcp_result.processed_embedding.detach().clone()
            self._baseline = baseline
        drift = self._compute_drift(baseline, mcp_result.processed_embedding)

        if drift > self.threshold:
            await self._quarantine_pipeline(drift)
            raise ContaminationError(f"Drift violation: {drift:.4f}")

        top_k = min(5, int(mcp_result.arbitration_scores.shape[-1]))
        top_roles = (
            torch.topk(mcp_result.arbitration_scores, k=top_k).indices.detach().cpu().tolist()
        )

        client_result = {
            "tenant_id": self.ctx.tenant_id,
            "mcp_tensor": mcp_result.processed_embedding.squeeze(0).detach().cpu().tolist(),
            "middleware_roles": top_roles,
            "protocol_features": mcp_result.protocol_features,
            "sovereignty_hash": mcp_result.execution_hash[:16],
        }

        await self.store.append_event(
            tenant_id=self.ctx.tenant_id,
            execution_id=f"mcp-{uuid4().hex[:8]}",
            state="MCP_PROCESSED",
            payload={
                "mcp_result_hash": mcp_result.execution_hash,
                "drift_score": float(drift),
                "arbitration_top_roles": client_result["middleware_roles"],
            },
        )

        return client_result

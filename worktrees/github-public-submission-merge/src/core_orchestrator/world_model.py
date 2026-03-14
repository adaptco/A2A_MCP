"""World-model ingress and gating primitives for agent routing.

This module lets the core orchestrator act as an ingress node for a world
model. Incoming events are embedded into deterministic vectors and compared to
registered agent vectors via normalized dot product (cosine similarity).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

import numpy as np

from .router import Event


def normalize_vector(vector: Sequence[float]) -> tuple[float, ...]:
    """Return an L2-normalized copy of ``vector``."""

    if not vector:
        raise ValueError("vector must not be empty")
    arr = np.asarray(vector, dtype=float)
    norm = np.linalg.norm(arr)
    if norm <= 0.0:
        raise ValueError("vector norm must be positive")
    return tuple((arr / norm).tolist())


def normalized_dot_product(lhs: Sequence[float], rhs: Sequence[float]) -> float:
    """Return cosine similarity between two vectors."""

    if len(lhs) != len(rhs):
        raise ValueError("vectors must have equal dimensions")

    arr_lhs = np.asarray(lhs, dtype=float)
    arr_rhs = np.asarray(rhs, dtype=float)

    norm_lhs = np.linalg.norm(arr_lhs)
    norm_rhs = np.linalg.norm(arr_rhs)

    if norm_lhs <= 0.0 or norm_rhs <= 0.0:
        # Maintain original behavior: normalize_vector raises if norm is non-positive
        raise ValueError("vector norm must be positive")

    return float(np.dot(arr_lhs, arr_rhs) / (norm_lhs * norm_rhs))


@dataclass(frozen=True, slots=True)
class GateScore:
    """Score assigned to one agent during ingress gating."""

    agent_id: str
    score: float
    accepted: bool


@dataclass(frozen=True, slots=True)
class IngressDecision:
    """Result produced by the world-model ingress for one event."""

    event_embedding: tuple[float, ...]
    scores: tuple[GateScore, ...]

    @property
    def routed_agent_ids(self) -> tuple[str, ...]:
        return tuple(score.agent_id for score in self.scores if score.accepted)


class WorldModelIngress:
    """Embedding and gating node for routing events to world-model agents."""

    def __init__(
        self,
        agent_vectors: Mapping[str, Sequence[float]],
        *,
        threshold: float = 0.5,
        dimensions: int = 16,
    ) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        if not agent_vectors:
            raise ValueError("agent_vectors must not be empty")
        self._dimensions = dimensions
        self._threshold = float(threshold)
        self._agents = {agent_id: normalize_vector(vector) for agent_id, vector in agent_vectors.items()}
        expected_dim = None
        for vector in self._agents.values():
            expected_dim = expected_dim or len(vector)
            if len(vector) != expected_dim:
                raise ValueError("all agent vectors must have equal dimensions")
        if expected_dim != self._dimensions:
            raise ValueError("dimensions must match the registered agent vector size")

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def threshold(self) -> float:
        return self._threshold

    def embed(self, payload: Mapping[str, Any]) -> tuple[float, ...]:
        """Build a deterministic embedding for ``payload``."""

        serialized = json.dumps(
            _canonicalize_payload(payload),
            sort_keys=True,
            separators=(",", ":"),
        )
        tokens = [token for token in serialized.lower().replace('"', " ").split() if token]
        if not tokens:
            tokens = ["empty"]

        raw = [0.0] * self._dimensions
        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self._dimensions
            sign = -1.0 if digest[4] % 2 else 1.0
            magnitude = 1.0 + (digest[5] / 255.0)
            raw[index] += sign * magnitude

        return normalize_vector(raw)

    def gate_event(self, event: Event) -> IngressDecision:
        """Compute world-model scores for ``event`` and select accepted agents."""

        embedding = self.embed(event.payload)
        scores = []
        for agent_id, vector in self._agents.items():
            score = normalized_dot_product(embedding, vector)
            scores.append(GateScore(agent_id=agent_id, score=score, accepted=score >= self._threshold))

        ordered = tuple(sorted(scores, key=lambda item: item.score, reverse=True))
        return IngressDecision(event_embedding=embedding, scores=ordered)


def _canonicalize_payload(value: Any) -> Any:
    """Convert opaque payload values into deterministic JSON-compatible data."""

    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Mapping):
        return {
            str(key): _canonicalize_payload(item)
            for key, item in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_canonicalize_payload(item) for item in value]
    if isinstance(value, (set, frozenset)):
        canonical_items = [_canonicalize_payload(item) for item in value]
        return sorted(canonical_items, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
    if isinstance(value, bytes):
        return {"__type__": "bytes", "value": value.hex()}
    if isinstance(value, (datetime, date, time)):
        return {"__type__": type(value).__name__, "value": value.isoformat()}
    return {
        "__type__": f"{type(value).__module__}.{type(value).__qualname__}",
        "value": str(value),
    }


__all__ = [
    "GateScore",
    "IngressDecision",
    "WorldModelIngress",
    "normalize_vector",
    "normalized_dot_product",
]

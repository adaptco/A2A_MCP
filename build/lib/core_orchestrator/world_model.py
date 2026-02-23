"""World-model ingress and gating primitives for agent routing.

This module lets the core orchestrator act as an ingress node for a world
model. Incoming events are embedded into deterministic vectors and compared to
registered agent vectors via normalized dot product (cosine similarity).
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from .router import Event


def normalize_vector(vector: Sequence[float]) -> tuple[float, ...]:
    """Return an L2-normalized copy of ``vector``."""

    if not vector:
        raise ValueError("vector must not be empty")
    norm = math.sqrt(sum(float(value) * float(value) for value in vector))
    if norm <= 0.0:
        raise ValueError("vector norm must be positive")
    return tuple(float(value) / norm for value in vector)


def normalized_dot_product(lhs: Sequence[float], rhs: Sequence[float]) -> float:
    """Return cosine similarity between two vectors."""

    if len(lhs) != len(rhs):
        raise ValueError("vectors must have equal dimensions")
    left = normalize_vector(lhs)
    right = normalize_vector(rhs)
    return sum(a * b for a, b in zip(left, right))


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

        serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
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


__all__ = [
    "GateScore",
    "IngressDecision",
    "WorldModelIngress",
    "normalize_vector",
    "normalized_dot_product",
]

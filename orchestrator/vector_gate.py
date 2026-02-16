"""Vector token retrieval and gating for model context injection."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import List, Sequence

from schemas.world_model import WorldModel


@dataclass
class VectorMatch:
    """A single semantic match between query and a world-model token."""

    token_id: str
    source_artifact_id: str
    score: float
    text: str


@dataclass
class VectorGateDecision:
    """Gate output for a single pipeline breakpoint."""

    node: str
    is_open: bool
    query: str
    threshold: float
    top_score: float = 0.0
    matches: List[VectorMatch] = field(default_factory=list)


class VectorGate:
    """Deterministic semantic retrieval over PINN WorldModel tokens."""

    def __init__(self, min_similarity: float = 0.20, top_k: int = 3) -> None:
        self.min_similarity = float(min_similarity)
        self.top_k = int(top_k)

    def evaluate(self, *, node: str, query: str, world_model: WorldModel) -> VectorGateDecision:
        """Evaluate retrieval and return a gate decision for a node."""
        tokens = list(world_model.vector_tokens.values())
        if not tokens:
            return VectorGateDecision(
                node=node,
                is_open=False,
                query=query,
                threshold=self.min_similarity,
            )

        dimensions = len(tokens[0].vector)
        query_vector = self._deterministic_embedding(query, dimensions=dimensions)

        matches: List[VectorMatch] = []
        for token in tokens:
            if len(token.vector) != dimensions:
                # Skip malformed or incompatible vectors rather than breaking execution.
                continue
            score = self._cosine_similarity(query_vector, token.vector)
            matches.append(
                VectorMatch(
                    token_id=token.token_id,
                    source_artifact_id=token.source_artifact_id,
                    score=score,
                    text=token.text,
                )
            )

        matches.sort(key=lambda m: m.score, reverse=True)
        top_matches = matches[: self.top_k]
        top_score = top_matches[0].score if top_matches else 0.0

        return VectorGateDecision(
            node=node,
            is_open=bool(top_matches) and top_score >= self.min_similarity,
            query=query,
            threshold=self.min_similarity,
            top_score=top_score,
            matches=top_matches,
        )

    def format_prompt_context(self, decision: VectorGateDecision, max_chars: int = 1200) -> str:
        """Format retrieved vector context for downstream prompt injection."""
        state = "OPEN" if decision.is_open else "CLOSED"
        header = (
            f"[VECTOR_GATE node={decision.node} state={state} "
            f"threshold={decision.threshold:.2f} top_score={decision.top_score:.3f}]"
        )

        if not decision.matches:
            return f"{header}\nNo vector tokens available."

        lines = [header]
        remaining = max_chars

        for idx, match in enumerate(decision.matches, start=1):
            snippet = " ".join(match.text.split())
            if len(snippet) > 220:
                snippet = snippet[:217] + "..."

            line = (
                f"{idx}. score={match.score:.3f} "
                f"token={match.token_id} source={match.source_artifact_id} "
                f"text={snippet}"
            )
            if len(line) <= remaining:
                lines.append(line)
                remaining -= len(line)
            else:
                break

        return "\n".join(lines)

    @staticmethod
    def _deterministic_embedding(text: str, dimensions: int = 16) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: List[float] = []
        for i in range(dimensions):
            byte = digest[i % len(digest)]
            values.append((byte / 255.0) * 2.0 - 1.0)
        return values

    @staticmethod
    def _cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)

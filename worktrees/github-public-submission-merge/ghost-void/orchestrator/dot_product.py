# A2A_MCP/orchestrator/dot_product.py
"""
Dot-product utilities for the ADAPTCO fast path.

Provides normal dot-product and cosine-similarity computations between
VectorToken embeddings so the orchestrator can quickly match intents to
agent capabilities.
"""
from __future__ import annotations

import math
from typing import List, Sequence, Tuple


def dot_product(a: Sequence[float], b: Sequence[float]) -> float:
    """Compute the standard inner product of two equal-length float vectors."""
    if len(a) != len(b):
        raise ValueError(
            f"Vector length mismatch: len(a)={len(a)}, len(b)={len(b)}"
        )
    return sum(x * y for x, y in zip(a, b))


def magnitude(v: Sequence[float]) -> float:
    """Euclidean norm (L2) of a vector."""
    return math.sqrt(sum(x * x for x in v))


def cosine_similarity(a: Sequence[float], b: Sequence[float]) -> float:
    """
    Normalised dot product.

    Returns 0.0 when either vector has zero magnitude to avoid division
    by zero.
    """
    mag_a = magnitude(a)
    mag_b = magnitude(b)
    if mag_a == 0.0 or mag_b == 0.0:
        return 0.0
    return dot_product(a, b) / (mag_a * mag_b)


def rank_candidates(
    query_vec: Sequence[float],
    candidates: List[Tuple[str, Sequence[float]]],
) -> List[Tuple[str, float]]:
    """
    Rank a list of ``(label, vector)`` candidates by cosine similarity
    to *query_vec*.

    Returns a list of ``(label, score)`` tuples sorted descending by score.
    """
    scored = [
        (label, cosine_similarity(query_vec, vec))
        for label, vec in candidates
    ]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored

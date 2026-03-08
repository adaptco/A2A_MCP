# adaptco/normalizer.py
"""
IngressNormalizer — the dot-product CI/CD gate.

Normalises raw ingress vectors to unit length (L2 norm) and applies a
cosine-similarity gate that rejects vectors below a configurable
threshold before they reach the OrchestrationAgent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

from orchestrator.dot_product import cosine_similarity, magnitude, rank_candidates
from adaptco.config import AdaptcoConfig, DEFAULT_CONFIG


@dataclass
class NormalizedEntry:
    """A single ingress vector after L2 normalisation + gate evaluation."""

    label: str
    raw_vector: Tuple[float, ...]
    normalized_vector: Tuple[float, ...]
    similarity_score: float
    passed_gate: bool


class IngressNormalizer:
    """
    CI/CD gate that transforms raw ingress data into unit-sphere vectors
    and filters by cosine similarity before handing off to the orchestrator.

    Usage::

        normalizer = IngressNormalizer(config)
        accepted = normalizer.normalize_and_gate(candidates)
        # *accepted* contains only entries that meet the threshold
    """

    def __init__(self, config: AdaptcoConfig | None = None) -> None:
        self.config = config or DEFAULT_CONFIG

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def l2_normalize(self, vec: Sequence[float]) -> Tuple[float, ...]:
        """
        Project *vec* onto the unit sphere (L2 normalisation).

        Returns the zero vector unchanged to avoid division by zero.
        """
        mag = magnitude(vec)
        if mag == 0.0:
            return tuple(vec)
        return tuple(x / mag for x in vec)

    def cosine_gate(
        self,
        vec: Sequence[float],
        reference: Sequence[float] | None = None,
    ) -> float:
        """
        Evaluate *vec* against the reference embedding.

        Returns the cosine-similarity score.  If no reference is
        configured (or passed), returns ``1.0`` (open gate).
        """
        ref = reference or self.config.reference_vector
        if not ref:
            return 1.0  # open gate — no reference to compare against
        return cosine_similarity(vec, ref)

    def normalize_and_gate(
        self,
        candidates: List[Tuple[str, Sequence[float]]],
        reference: Sequence[float] | None = None,
    ) -> List[NormalizedEntry]:
        """
        Full CI/CD normalisation pass:

        1. L2-normalise every candidate vector.
        2. Score each against the reference embedding (cosine gate).
        3. Return only entries that meet the similarity threshold.

        Candidates are ``(label, raw_vector)`` pairs.
        """
        results: List[NormalizedEntry] = []
        for label, raw in candidates:
            normed = self.l2_normalize(raw)
            score = self.cosine_gate(normed, reference)
            passed = score >= self.config.similarity_threshold

            results.append(
                NormalizedEntry(
                    label=label,
                    raw_vector=tuple(raw),
                    normalized_vector=normed,
                    similarity_score=score,
                    passed_gate=passed,
                )
            )

        return results

    def accepted(
        self,
        candidates: List[Tuple[str, Sequence[float]]],
        reference: Sequence[float] | None = None,
    ) -> List[NormalizedEntry]:
        """Convenience — returns only entries that passed the gate."""
        return [
            e
            for e in self.normalize_and_gate(candidates, reference)
            if e.passed_gate
        ]

    def rank(
        self,
        query_vec: Sequence[float],
        candidates: List[Tuple[str, Sequence[float]]],
    ) -> List[Tuple[str, float]]:
        """
        Rank candidates by cosine similarity to *query_vec*, using the
        core-orchestrator's ``rank_candidates`` utility.  Both query and
        candidate vectors are L2-normalised before comparison.
        """
        normed_query = self.l2_normalize(query_vec)
        normed_candidates = [
            (label, self.l2_normalize(vec)) for label, vec in candidates
        ]
        return rank_candidates(normed_query, normed_candidates)

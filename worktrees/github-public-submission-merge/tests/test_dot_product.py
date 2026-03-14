# tests/test_dot_product.py
"""Unit tests for the dot-product / cosine-similarity utilities."""
import math

import pytest

from orchestrator.dot_product import (
    cosine_similarity,
    dot_product,
    magnitude,
    rank_candidates,
)


class TestDotProduct:
    """Core vector operations."""

    def test_dot_product_basic(self):
        assert dot_product([1, 2, 3], [4, 5, 6]) == 32  # 4+10+18

    def test_dot_product_zero_vector(self):
        assert dot_product([0, 0], [5, 5]) == 0.0

    def test_dot_product_length_mismatch_raises(self):
        with pytest.raises(ValueError, match="length mismatch"):
            dot_product([1, 2], [3])

    def test_magnitude(self):
        assert magnitude([3, 4]) == pytest.approx(5.0)

    def test_magnitude_zero(self):
        assert magnitude([0, 0, 0]) == 0.0


class TestCosineSimilarity:
    """Normalised dot product."""

    def test_identical_vectors(self):
        v = [1.0, 2.0, 3.0]
        assert cosine_similarity(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        assert cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_opposite_vectors(self):
        assert cosine_similarity([1, 0], [-1, 0]) == pytest.approx(-1.0)

    def test_zero_vector_returns_zero(self):
        assert cosine_similarity([0, 0], [1, 2]) == 0.0


class TestRankCandidates:
    """Candidate ranking by cosine similarity."""

    def test_ranking_order(self):
        query = [1.0, 0.0]
        candidates = [
            ("orthogonal", [0.0, 1.0]),
            ("aligned", [1.0, 0.0]),
            ("partial", [0.5, 0.5]),
        ]
        ranked = rank_candidates(query, candidates)

        labels = [r[0] for r in ranked]
        assert labels[0] == "aligned"
        assert labels[-1] == "orthogonal"

    def test_ranking_returns_all_candidates(self):
        query = [1.0, 1.0]
        candidates = [("a", [1, 0]), ("b", [0, 1])]
        ranked = rank_candidates(query, candidates)
        assert len(ranked) == 2

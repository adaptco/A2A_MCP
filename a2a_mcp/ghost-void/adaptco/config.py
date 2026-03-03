# adaptco/config.py
"""
ADAPTCO configuration — thresholds and tunables for the normalised
dot-product CI/CD gate and the downstream agent pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AdaptcoConfig:
    """Immutable configuration for an ADAPTCO pipeline run."""

    # ── Normalizer tunables ─────────────────────────────────────────
    similarity_threshold: float = 0.70
    """Minimum cosine-similarity score for ingress vectors to pass the gate."""

    embedding_dim: int = 1536
    """Expected dimensionality of ingress embeddings (matches OpenAI ada-002)."""

    # ── Pipeline tunables ───────────────────────────────────────────
    max_healing_retries: int = 3
    """Max Coder→Tester self-healing iterations per blueprint action."""

    requester: str = "adaptco-ci"
    """Default requester tag stamped on all artefacts."""

    # ── Reference embedding ─────────────────────────────────────────
    reference_vector: tuple[float, ...] = field(default_factory=tuple)
    """
    Optional reference embedding for the cosine gate.  When non-empty,
    every ingress vector must score ≥ *similarity_threshold* against this
    vector to be admitted.  When empty the gate is open (all vectors pass).
    """


# Sensible defaults for local development
DEFAULT_CONFIG = AdaptcoConfig()

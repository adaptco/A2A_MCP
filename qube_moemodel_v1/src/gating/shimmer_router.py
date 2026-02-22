"""Token dispatch via Spark Test compliance."""

from typing import Dict, List


class ShimmerRouter:
    """Routes token embeddings to experts based on shimmer scores."""

    def __init__(self, resonance_threshold: float) -> None:
        self.resonance_threshold = resonance_threshold

    def route(self, shimmer_scores: List[float]) -> Dict[str, List[int]]:
        """Return token indices partitioned by resonance status."""
        high = [i for i, score in enumerate(shimmer_scores) if score >= self.resonance_threshold]
        low = [i for i, score in enumerate(shimmer_scores) if score < self.resonance_threshold]
        return {"high_resonance": high, "low_resonance": low}

"""Posture expert tuned to gesture fidelity."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class PostureExpert:
    """Evaluates capsule posture streams for fidelity."""

    posture_threshold: float = 0.9

    def assess(self, posture_signal: Dict[str, Any]) -> bool:
        """Return ``True`` when posture signal integrity meets the threshold."""
        confidence = float(posture_signal.get("confidence", 0.0))
        return confidence >= self.posture_threshold

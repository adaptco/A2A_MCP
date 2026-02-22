"""HUD shimmer renderer for timestamp and emotional hue."""

from datetime import UTC, datetime
from typing import Dict


class ShimmerRenderer:
    """Formats shimmer trace entries for display."""

    def render(self, trace: Dict[str, float]) -> str:
        """Return a human-readable shimmer trace line."""
        timestamp = trace.get("timestamp", datetime.now(UTC).timestamp())
        hue = trace.get("emotional_hue", 0.0)
        return f"[{timestamp:.3f}] hue={hue:.2f}"

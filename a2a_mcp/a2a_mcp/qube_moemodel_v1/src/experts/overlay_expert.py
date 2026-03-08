"""Validates CiCi's persona overlay layer."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class OverlayExpert:
    """Checks whether persona overlays stay inside allowed bounds."""

    persona: str = "CiCi"

    def validate(self, overlay_signal: Dict[str, Any]) -> bool:
        """Return ``True`` if the overlay matches the configured persona."""
        return overlay_signal.get("persona") == self.persona

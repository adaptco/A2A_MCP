"""Handles rupture scripting for contract-bound refusals."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class RefusalExpert:
    """Crafts refusal narratives when prompts exceed contract bounds."""

    boundary_tag: str = "contract_boundary"

    def should_refuse(self, prompt: Dict[str, Any]) -> bool:
        """Detect whether a refusal response must be triggered."""
        return self.boundary_tag in prompt.get("violation_tags", [])

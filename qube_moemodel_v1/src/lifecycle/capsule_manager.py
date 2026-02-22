"""Capsule lifecycle management utilities."""

from dataclasses import dataclass, field
from typing import List


@dataclass
class CapsuleManager:
    """Coordinates freeze, braid bind, and feedback loops for capsules."""

    frozen_capsules: List[str] = field(default_factory=list)

    def freeze(self, capsule_id: str) -> None:
        """Register a capsule as frozen."""
        if capsule_id not in self.frozen_capsules:
            self.frozen_capsules.append(capsule_id)

    def is_frozen(self, capsule_id: str) -> bool:
        """Return ``True`` when the capsule is already frozen."""
        return capsule_id in self.frozen_capsules

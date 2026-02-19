from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SovereigntyEvent:
    sequence: int
    event_type: str
    state: str
    payload: dict[str, Any]
    prev_hash: str

    def canonical_payload(self) -> dict[str, Any]:
        return {
            "sequence": self.sequence,
            "event_type": self.event_type,
            "state": self.state,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
        }

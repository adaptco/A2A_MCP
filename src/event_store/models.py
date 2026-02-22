from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional

@dataclass
class Event:
    execution_id: str
    event_type: str
    state: str
    hash_current: str
    timestamp: datetime
    payload: Dict[str, Any] = field(default_factory=dict)

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class RunContext:
    project_id: str
    vertical_id: str
    intent: str
    query: str
    registry_ref: str


@dataclass
class RetrievedChunk:
    thread_id: str
    content: str
    score: float
    metadata: Dict[str, Any]


@dataclass
class ContextBundle:
    chunks: List[RetrievedChunk]

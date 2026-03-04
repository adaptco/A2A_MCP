"""Canonical runtime contracts for orchestrator-mediated events and intents."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class ContractVersion(str, Enum):
    """Supported runtime contract versions."""

    V1 = "v1"
    V2 = "v2"


class ToolRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]


class EventPayload(BaseModel):
    content: Any
    tool_request: Optional[ToolRequest] = None
    status: str
    provider: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class RuntimeIntent(BaseModel):
    """Canonical command submitted to the orchestrator control-plane."""

    intent_id: str = Field(default_factory=lambda: f"intent_{uuid4().hex}")
    actor: str = Field(..., min_length=1)
    intent: str = Field(..., min_length=1)
    artifact_id: str | None = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    schema_version: ContractVersion = ContractVersion.V1
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RuntimeEvent(BaseModel):
    """Append-only event emitted for every meaningful state transition."""

    event_id: str = Field(default_factory=lambda: f"evt_{uuid4().hex}")
    trace_id: str = Field(..., min_length=1)
    span_id: str = Field(default_factory=lambda: uuid4().hex)
    parent_span_id: Optional[str] = None
    actor: str = Field(..., min_length=1)
    intent: str = Field(..., min_length=1)
    artifact_id: str | None = None
    event_type: str = Field(..., min_length=1)
    schema_version: ContractVersion = ContractVersion.V1
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    phase: Literal["control_plane", "data_plane", "gate"]
    attributes: Dict[str, Any] = Field(default_factory=dict)
    content: EventPayload

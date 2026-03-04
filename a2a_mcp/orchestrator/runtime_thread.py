"""Runtime thread blueprint: orchestrator composition root with event-first flow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Protocol
from uuid import uuid4

from schemas.runtime_event import RuntimeEvent, RuntimeIntent


class EventStore(Protocol):
    """Append-only event persistence interface."""

    def append(self, event: RuntimeEvent) -> None: ...

    def list_events(self, trace_id: str) -> List[RuntimeEvent]: ...


@dataclass
class InMemoryEventStore:
    """Reference event store for deterministic tests and local development."""

    events: List[RuntimeEvent] = field(default_factory=list)

    def append(self, event: RuntimeEvent) -> None:
        self.events.append(event)

    def list_events(self, trace_id: str) -> List[RuntimeEvent]:
        return [event for event in self.events if event.trace_id == trace_id]


class RuntimeThread:
    """Control-plane orchestration that emits canonical events end-to-end."""

    def __init__(self, event_store: EventStore):
        self._event_store = event_store

    def process_intent(self, intent: RuntimeIntent) -> str:
        """Route one intent through control-plane, data-plane, and gate phases."""
        trace_id = uuid4().hex

        self._emit(trace_id, intent, "intent.received", "control_plane")
        self._emit(trace_id, intent, "dataplane.dispatched", "data_plane")
        self._emit(trace_id, intent, "gate.schema_validated", "gate")
        self._emit(trace_id, intent, "gate.policy_validated", "gate")
        self._emit(trace_id, intent, "artifact.delivered", "control_plane")

        return trace_id

    def _emit(self, trace_id: str, intent: RuntimeIntent, event_type: str, phase: str) -> None:
        event = RuntimeEvent(
            trace_id=trace_id,
            actor=intent.actor,
            intent=intent.intent,
            artifact_id=intent.artifact_id,
            event_type=event_type,
            phase=phase,  # type: ignore[arg-type]
            schema_version=intent.schema_version,
        )
        self._event_store.append(event)

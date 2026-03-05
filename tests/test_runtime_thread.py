from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

from schemas.runtime_event import RuntimeIntent


_runtime_thread_path = Path(__file__).resolve().parents[1] / "orchestrator" / "runtime_thread.py"
_spec = spec_from_file_location("runtime_thread", _runtime_thread_path)
_runtime_thread = module_from_spec(_spec)
assert _spec and _spec.loader
sys.modules[_spec.name] = _runtime_thread
_spec.loader.exec_module(_runtime_thread)

InMemoryEventStore = _runtime_thread.InMemoryEventStore
RuntimeThread = _runtime_thread.RuntimeThread


def test_runtime_thread_emits_canonical_event_sequence() -> None:
    store = InMemoryEventStore()
    runtime = RuntimeThread(store)

    trace_id = runtime.process_intent(
        RuntimeIntent(actor="orchestrator", intent="artifact.generate", artifact_id="art_001")
    )

    events = store.list_events(trace_id)
    assert [event.event_type for event in events] == [
        "intent.received",
        "dataplane.dispatched",
        "gate.schema_validated",
        "gate.policy_validated",
        "artifact.delivered",
    ]
    assert all(event.trace_id == trace_id for event in events)
    assert all(event.actor == "orchestrator" for event in events)

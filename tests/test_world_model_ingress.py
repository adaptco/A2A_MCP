from __future__ import annotations

from core_orchestrator.router import Event, Router
from core_orchestrator.world_model import WorldModelIngress, normalize_vector, normalized_dot_product


class RecordingParser:
    name = "recording"

    def __init__(self, events):
        self._events = list(events)

    def fetch_events(self):
        return iter(self._events)


class RecordingSink:
    name = "recording"

    def __init__(self):
        self.events = []

    def handles(self, event: Event) -> bool:
        return True

    def send(self, event: Event):
        self.events.append(event)
        return event


def test_normalized_dot_product_matches_cosine_expectations():
    assert normalized_dot_product([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert normalized_dot_product([1.0, 0.0], [-1.0, 0.0]) == -1.0


def test_ingress_embedding_is_normalized_and_deterministic():
    ingress = WorldModelIngress({"agent": normalize_vector([1.0] + [0.0] * 15)}, dimensions=16)
    payload = {"content": "route this event", "channel": "ops"}

    first = ingress.embed(payload)
    second = ingress.embed(payload)

    assert len(first) == 16
    assert first == second
    assert abs(sum(v * v for v in first) - 1.0) < 1e-9


def test_router_attaches_world_model_gating_metadata():
    ingress = WorldModelIngress(
        {
            "agent-alpha": normalize_vector([1.0] + [0.0] * 15),
            "agent-beta": normalize_vector([0.0, 1.0] + [0.0] * 14),
        },
        threshold=0.0,
        dimensions=16,
    )
    sink = RecordingSink()
    event = Event(source="discord", type="message.created", payload={"content": "alpha"})

    router = Router(parsers=[RecordingParser([event])], sinks=[sink], ingress=ingress)
    processed = router.dispatch()

    assert processed == 1
    assert len(sink.events) == 1
    delivered = sink.events[0]
    assert delivered.raw is not None
    assert "world_model" in delivered.raw
    wm = delivered.raw["world_model"]
    assert len(wm["embedding"]) == 16
    assert len(wm["scores"]) == 2
    assert set(wm["routed_agent_ids"]) == {"agent-alpha", "agent-beta"}

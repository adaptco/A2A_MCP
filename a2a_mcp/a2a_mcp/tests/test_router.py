from __future__ import annotations

import json
from datetime import UTC, datetime

from core_orchestrator.databases import OrganizeSentinel

from core_orchestrator.parsers import DiscordParser
from core_orchestrator.router import Router
from core_orchestrator.sinks import BaseSink, GoogleCalendarSink, NotionSink, ShopifySink


class RecordingSink(BaseSink):
    name = "recording"

    def __init__(self) -> None:
        super().__init__(supported_event_types=("message.created", "task.created"), dry_run=True)
        self.events = []

    def _send(self, event):
        self.events.append(event)
        return event


def build_messages():
    now = datetime(2023, 8, 1, 12, tzinfo=UTC)
    return [
        {
            "id": "1",
            "content": "Kickoff with client",
            "author": "Alice",
            "channel": "sales",
            "created_at": now.isoformat(),
            "scheduled_for": now.replace(hour=15).isoformat(),
            "duration_minutes": 45,
            "priority": "high",
        },
        {
            "id": "2",
            "content": "Create marketing brief",
            "author": "Bob",
            "channel": "marketing",
            "created_at": now.isoformat(),
            "event_type": "task.created",
        },
    ]


def test_router_delivers_events_to_all_sinks():
    parser = DiscordParser(build_messages())
    router = Router([parser], [RecordingSink(), RecordingSink()])

    processed = router.dispatch()

    assert processed == 2
    for sink in router.sinks:
        assert isinstance(sink, RecordingSink)
        assert len(sink.events) == 2


def test_channel_filtering():
    parser = DiscordParser(build_messages(), channel_whitelist=["sales"])
    events = list(parser.fetch_events())

    assert len(events) == 1
    assert events[0].payload["channel"] == "sales"


def test_notion_payload_shape():
    parser = DiscordParser(build_messages(), channel_whitelist=["sales"])
    event = next(iter(parser.fetch_events()))

    sink = NotionSink(database_id="db", dry_run=True)
    payload = sink.build_payload(event)

    assert payload["parent"]["database_id"] == "db"
    assert payload["properties"]["Name"]["title"][0]["text"]["content"]
    assert payload["children"][0]["type"] == "paragraph"


def test_google_calendar_payload():
    parser = DiscordParser(build_messages(), channel_whitelist=["sales"])
    event = next(iter(parser.fetch_events()))

    sink = GoogleCalendarSink(calendar_id="cal", dry_run=True)
    payload = sink.build_event(event)

    assert payload["start"]["dateTime"].endswith("+00:00")
    assert payload["end"]["dateTime"].endswith("+00:00")


def test_shopify_payload_contains_metadata():
    parser = DiscordParser(build_messages(), channel_whitelist=["marketing"])
    event = next(iter(parser.fetch_events()))

    sink = ShopifySink(store_domain="demo.myshopify.com", dry_run=True)
    note = sink.build_payload(event)

    assert note["summary"].startswith("Create marketing")
    assert note["metadata"]


def test_router_records_events_in_ssot(tmp_path):
    parser = DiscordParser(build_messages())
    sentinel = OrganizeSentinel(repo_path=tmp_path, relative_path="events.json")
    router = Router([parser], [RecordingSink()], sentinel=sentinel)

    processed = router.dispatch()

    assert processed == 2
    payload = json.loads((tmp_path / "events.json").read_text())
    assert payload["metadata"]["count"] == 2
    keys = [event["key"] for event in payload["events"]]
    assert len(keys) == len(set(keys))


def test_sentinel_upsert_overwrites_existing_records(tmp_path):
    parser = DiscordParser(build_messages(), channel_whitelist=["sales"])
    event = next(iter(parser.fetch_events()))
    sentinel = OrganizeSentinel(repo_path=tmp_path, relative_path="events.json")

    sentinel.record(event)
    updated = event.copy(payload={**event.payload, "content": "Kickoff with client (updated)"})
    sentinel.record(updated)

    payload = json.loads((tmp_path / "events.json").read_text())
    assert payload["metadata"]["count"] == 1
    stored = payload["events"][0]
    assert stored["payload"]["content"].endswith("(updated)")

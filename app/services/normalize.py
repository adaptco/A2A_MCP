from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from ..schemas.task import CanonicalTask

STATUS_MAP = {
    "Not Started": "todo",
    "Planned": "todo",
    "Working on it": "doing",
    "Stuck": "blocked",
    "Blocked": "blocked",
    "Done": "done",
    "Canceled": "canceled",
}


def normalize_monday_item(item: Dict[str, Any]) -> CanonicalTask:
    columns = {c["id"]: c for c in item.get("column_values", [])}
    status = columns.get("status", {}).get("text") or "todo"
    status = STATUS_MAP.get(status, "todo")
    timeline_raw = columns.get("timeline", {}).get("value")
    start_date = None
    due_date = None
    if timeline_raw:
        value = timeline_raw
        if isinstance(value, str):
            import json

            value = json.loads(value)
        start = value.get("start")
        end = value.get("end")
        if start:
            start_date = datetime.fromisoformat(start).date()
        if end:
            due_date = datetime.fromisoformat(end).date()
    assignees = []
    people = columns.get("people", {}).get("value")
    if people:
        if isinstance(people, str):
            import json

            people = json.loads(people)
        assignees = [
            p.get("email") or str(p.get("id"))
            for p in people.get("personsAndTeams", [])
        ]
    return CanonicalTask(
        source="monday",
        board_id=item.get("board_id"),
        item_id=item.get("id"),
        name=item.get("name"),
        status=status,
        assignees=assignees,
        start_date=start_date,
        due_date=due_date,
        raw=item,
    )


def normalize_airtable_record(record: Dict[str, Any]) -> CanonicalTask:
    fields = record.get("fields", {})
    return CanonicalTask(
        source="airtable",
        item_id=fields.get("item_id"),
        name=fields.get("name", ""),
        status=fields.get("status", "todo"),
        assignees=fields.get("assignees", []),
        start_date=fields.get("start_date"),
        due_date=fields.get("due_date"),
        external_ids={"airtable": record.get("id")},
        raw=record,
    )

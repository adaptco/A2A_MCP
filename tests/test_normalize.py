from datetime import date

from app.services.normalize import normalize_monday_item, normalize_airtable_record


def test_normalize_monday_item():
    item = {
        "id": "1",
        "name": "Task",
        "board_id": "b1",
        "column_values": [
            {"id": "status", "text": "Working on it"},
            {"id": "timeline", "value": {"start": "2023-01-01", "end": "2023-01-10"}},
            {
                "id": "people",
                "value": {"personsAndTeams": [{"email": "a@example.com"}]},
            },
        ],
    }
    task = normalize_monday_item(item)
    assert task.status == "doing"
    assert task.start_date == date(2023, 1, 1)
    assert task.due_date == date(2023, 1, 10)
    assert task.assignees == ["a@example.com"]


def test_normalize_airtable_record():
    record = {
        "id": "rec1",
        "fields": {"item_id": "1", "name": "Task", "status": "todo"},
    }
    task = normalize_airtable_record(record)
    assert task.external_ids["airtable"] == "rec1"
    assert task.item_id == "1"

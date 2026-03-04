from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel


class CanonicalTask(BaseModel):
    source: Literal["monday", "airtable", "clickup", "notion", "github"]
    board_id: Optional[str] = None
    item_id: Optional[str] = None
    external_ids: dict = {}
    parent_item_id: Optional[str] = None
    name: str
    description: str | None = None
    status: Literal["todo", "doing", "blocked", "done", "canceled"] = "todo"
    priority: Literal["low", "medium", "high", "urgent"] | None = None
    assignees: list[str] = []
    start_date: date | None = None
    due_date: date | None = None
    tags: list[str] = []
    est_hours: float | None = None
    logged_hours: float | None = None
    dependencies: list[str] = []
    subtasks: list[str] = []
    last_updated_ts: datetime | None = None
    raw: dict = {}

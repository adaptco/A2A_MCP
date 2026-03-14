from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field


class CanonicalTask(BaseModel):
    source: Literal["monday", "airtable", "clickup", "notion", "github"]
    board_id: Optional[str] = None
    item_id: Optional[str] = None
    external_ids: dict = Field(default_factory=dict)
    parent_item_id: Optional[str] = None
    name: str
    description: str | None = None
    status: Literal["todo", "doing", "blocked", "done", "canceled"] = "todo"
    priority: Literal["low", "medium", "high", "urgent"] | None = None
    assignees: list[str] = Field(default_factory=list)
    start_date: date | None = None
    due_date: date | None = None
    tags: list[str] = Field(default_factory=list)
    est_hours: float | None = None
    logged_hours: float | None = None
    dependencies: list[str] = Field(default_factory=list)
    subtasks: list[str] = Field(default_factory=list)
    last_updated_ts: datetime | None = None
    raw: dict = Field(default_factory=dict)

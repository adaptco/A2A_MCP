from datetime import date, datetime

from sqlalchemy import Column, Integer, String, Date, DateTime, Float, JSON, Boolean

from .base import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String, nullable=False)
    board_id = Column(String, nullable=True)
    item_id = Column(String, nullable=True, unique=True)
    external_ids = Column(JSON, default=dict)
    parent_item_id = Column(String, nullable=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    status = Column(String, nullable=False, default="todo")
    priority = Column(String, nullable=True)
    assignees = Column(JSON, default=list)
    start_date = Column(Date, nullable=True)
    due_date = Column(Date, nullable=True)
    tags = Column(JSON, default=list)
    est_hours = Column(Float, nullable=True)
    logged_hours = Column(Float, nullable=True)
    dependencies = Column(JSON, default=list)
    subtasks = Column(JSON, default=list)
    last_updated_ts = Column(DateTime, nullable=True)
    raw = Column(JSON, default=dict)

    proposed_status = Column(String, nullable=True)
    proposed_due_date = Column(Date, nullable=True)
    needs_human_review = Column(Boolean, default=False)

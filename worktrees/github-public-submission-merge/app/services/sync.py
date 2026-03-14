from __future__ import annotations

from typing import Dict, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models.task import Task
from ..models.id_map import IdMap
from ..models.audit import AuditLog
from ..schemas.task import CanonicalTask
from .gates import evaluate_gates


async def commit_to_monday(client, task: CanonicalTask, ctx: Dict) -> None:
    if not settings.ALLOW_MONDAY_WRITES:
        return
    status = ctx.get("proposed_status")
    if status:
        await client.update_status(task.board_id, task.item_id, status)
    start = task.start_date
    due = task.due_date
    if start or due:
        await client.update_dates(task.board_id, task.item_id, start, due)


async def upsert_and_sync(
    session: AsyncSession, task: CanonicalTask, ctx: Dict, monday_client=None
) -> Tuple[Task, list]:
    existing = await session.scalar(select(Task).where(Task.item_id == task.item_id))
    if not existing:
        existing = Task(item_id=task.item_id, source=task.source)
    for field, value in task.dict().items():
        if hasattr(existing, field) and value is not None:
            setattr(existing, field, value)
    session.add(existing)
    # id map
    idmap = await session.scalar(
        select(IdMap).where(IdMap.monday_item_id == task.item_id)
    )
    if not idmap:
        idmap = IdMap(monday_item_id=task.item_id)
    idmap.airtable_id = task.external_ids.get("airtable")
    session.add(idmap)
    await session.commit()

    results = evaluate_gates(task, ctx)
    if all(r.ok for r in results):
        if monday_client:
            await commit_to_monday(monday_client, task, ctx)
    else:
        existing.needs_human_review = True
        audit = AuditLog(
            actor_system=ctx.get("actor_system", "system"),
            action="gates_failed",
            after=task.dict(),
            gate_results=[r.__dict__ for r in results],
        )
        session.add(existing)
        session.add(audit)
        await session.commit()
    return existing, results

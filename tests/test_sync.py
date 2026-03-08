import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import select, func

from app.models.base import Base
from app.models.task import Task
from app.schemas.task import CanonicalTask
from app.services.sync import upsert_and_sync


@pytest.mark.asyncio
async def test_sync_idempotent(tmp_path):
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    task = CanonicalTask(source="monday", item_id="1", name="Task")
    async with Session() as session:
        await upsert_and_sync(session, task, {"proposed_status": "todo"})
        await upsert_and_sync(session, task, {"proposed_status": "todo"})
        count = await session.scalar(select(func.count()).select_from(Task))
        assert count == 1

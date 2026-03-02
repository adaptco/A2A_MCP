import asyncio
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.base import Base
from app.deps import get_session


@pytest.fixture(autouse=True)
def setup_db():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    async def init() -> None:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(init())
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_session():
        async with Session() as session:
            yield session

    app.dependency_overrides[get_session] = _get_session
    yield
    app.dependency_overrides.clear()


class DummyMonday:
    async def get_item(self, board_id, item_id):
        return {
            "id": item_id,
            "name": "Task",
            "board_id": board_id,
            "column_values": [],
        }

    async def close(self):
        pass


@pytest.fixture(autouse=True)
def patch_monday(monkeypatch):
    monkeypatch.setattr("app.routes.webhooks.MondayClient", lambda: DummyMonday())


def test_webhook_monday():
    client = TestClient(app)
    resp = client.post(
        "/webhook/monday", json={"board_id": "b1", "item_id": "1", "event": "create"}
    )
    assert resp.status_code == 200
    assert resp.json()["received"] is True


def test_webhook_airtable():
    client = TestClient(app)
    payload = {"record_id": "rec1", "fields": {"item_id": "1", "name": "Task"}}
    resp = client.post("/webhook/airtable", json=payload)
    assert resp.status_code == 200
    assert resp.json()["received"] is True

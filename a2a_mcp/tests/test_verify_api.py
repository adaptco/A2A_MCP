from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from orchestrator.settlement import Event, State, compute_lineage
from orchestrator.verify_api import get_db_connection, get_event_store, get_tenant_id, router


class FakeConn:
    def __init__(self, rows):
        self.rows = rows

    async def fetch(self, *_args, **_kwargs):
        return self.rows


class FakeStore:
    def __init__(self, events):
        self.events = events

    async def get_execution(self, conn, tenant_id: str, execution_id: str):
        return self.events


def _app_with(events):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_tenant_id] = lambda: "tenant-a"
    app.dependency_overrides[get_db_connection] = lambda: FakeConn([])
    app.dependency_overrides[get_event_store] = lambda: FakeStore(events)
    return app


def test_verify_endpoint_returns_409_on_integrity_conflict():
    first = Event(
        id=1,
        tenant_id="tenant-a",
        execution_id="exec-1",
        state=State.RUNNING.value,
        payload={"x": 1},
        hash_prev=None,
        hash_current=compute_lineage(None, State.RUNNING.value, {"x": 1}),
    )
    tampered = Event(
        id=2,
        tenant_id="tenant-a",
        execution_id="exec-1",
        state=State.FINALIZED.value,
        payload={"x": 3},
        hash_prev=first.hash_current,
        hash_current=compute_lineage(first.hash_current, State.FINALIZED.value, {"x": 2}),
    )

    client = TestClient(_app_with([first, tampered]))
    response = client.get("/v1/executions/exec-1/verify")

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["valid"] is False
    assert detail["reason"] == "Hash mismatch at event_id=2"


def test_verify_endpoint_returns_200_when_valid():
    first = Event(
        id=1,
        tenant_id="tenant-a",
        execution_id="exec-1",
        state=State.RUNNING.value,
        payload={"x": 1},
        hash_prev=None,
        hash_current=compute_lineage(None, State.RUNNING.value, {"x": 1}),
    )
    second = Event(
        id=2,
        tenant_id="tenant-a",
        execution_id="exec-1",
        state=State.FINALIZED.value,
        payload={"x": 2},
        hash_prev=first.hash_current,
        hash_current=compute_lineage(first.hash_current, State.FINALIZED.value, {"x": 2}),
    )

    client = TestClient(_app_with([first, second]))
    response = client.get("/v1/executions/exec-1/verify")

    assert response.status_code == 200
    payload = response.json()
    assert payload["valid"] is True
    assert payload["hash_head"] == second.hash_current


def test_verify_endpoint_returns_503_when_database_url_not_configured(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    app = FastAPI()
    app.include_router(router)

    client = TestClient(app)
    response = client.get("/v1/executions/exec-1/verify", headers={"x-tenant-id": "tenant-a"})

    assert response.status_code == 503
    # Note: In the implementation, if DATABASE_URL is missing, it raises HTTPException(503, detail="DATABASE_URL is not configured")
    # But the test code above had "Database connection dependency is not configured". I'll align them.
    assert response.json()["detail"] == "DATABASE_URL is not configured"

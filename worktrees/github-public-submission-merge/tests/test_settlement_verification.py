from __future__ import annotations

import sqlite3

import pytest

from orchestrator.settlement import Event, State, compute_lineage, verify_execution


def _build_event(
    event_id: int,
    tenant_id: str,
    execution_id: str,
    state: State,
    payload: dict,
    hash_prev: str | None,
) -> Event:
    return Event(
        id=event_id,
        tenant_id=tenant_id,
        execution_id=execution_id,
        state=state.value,
        payload=payload,
        hash_prev=hash_prev,
        hash_current=compute_lineage(hash_prev, payload),
    )


def test_verify_fails_when_payload_mutates_after_hashing() -> None:
    tenant_id = "tenant-a"
    execution_id = "exec-1"

    e1 = _build_event(1, tenant_id, execution_id, State.RUNNING, {"input": "A"}, None)
    e2 = _build_event(2, tenant_id, execution_id, State.FINALIZED, {"output": "B"}, e1.hash_current)

    tampered = Event(
        id=e2.id,
        tenant_id=e2.tenant_id,
        execution_id=e2.execution_id,
        state=e2.state,
        payload={"output": "X"},
        hash_prev=e2.hash_prev,
        hash_current=e2.hash_current,
    )

    result = verify_execution([e1, tampered])

    assert not result.valid
    assert result.reason == "Hash mismatch at event_id=2"


def test_partial_unique_index_blocks_second_finalized_event() -> None:
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE events (
            id INTEGER PRIMARY KEY,
            tenant_id TEXT NOT NULL,
            execution_id TEXT NOT NULL,
            state TEXT NOT NULL,
            payload TEXT NOT NULL,
            hash_prev TEXT,
            hash_current TEXT NOT NULL
        )
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX ux_events_one_finalized_per_execution
        ON events (tenant_id, execution_id)
        WHERE state = 'FINALIZED'
        """
    )

    cur.execute(
        "INSERT INTO events (id, tenant_id, execution_id, state, payload, hash_current) VALUES (1, ?, ?, 'FINALIZED', '{}', 'h1')",
        ("tenant-a", "exec-1"),
    )

    with pytest.raises(sqlite3.IntegrityError):
        cur.execute(
            "INSERT INTO events (id, tenant_id, execution_id, state, payload, hash_current) VALUES (2, ?, ?, 'FINALIZED', '{}', 'h2')",
            ("tenant-a", "exec-1"),
        )


def test_verify_fails_when_finalized_is_not_terminal() -> None:
    tenant_id = "tenant-a"
    execution_id = "exec-1"

    e1 = _build_event(1, tenant_id, execution_id, State.RUNNING, {"step": 1}, None)
    e2 = _build_event(2, tenant_id, execution_id, State.FINALIZED, {"step": 2}, e1.hash_current)
    e3 = _build_event(3, tenant_id, execution_id, State.RUNNING, {"step": 3}, e2.hash_current)

    result = verify_execution([e1, e2, e3])

    assert not result.valid
    assert result.reason == "FINALIZED is not terminal"


@pytest.mark.asyncio
async def test_advisory_lock_uses_tenant_and_execution_pair_keys() -> None:
    from orchestrator.settlement import advisory_lock_execution, hash32

    class FakeConn:
        def __init__(self) -> None:
            self.calls = []

        async def execute(self, query: str, *args):
            self.calls.append((query, args))

    conn = FakeConn()
    await advisory_lock_execution(conn, "tenant-a", "exec-1")

    assert conn.calls == [
        ("SELECT pg_advisory_xact_lock($1, $2)", (hash32("tenant-a"), hash32("exec-1")))
    ]

from __future__ import annotations

import hashlib
import json
import zlib
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Optional


class State(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    FINALIZED = "FINALIZED"


_ALLOWED_TRANSITIONS: dict[State, set[State]] = {
    State.IDLE: {State.IDLE, State.RUNNING, State.FINALIZED},
    State.RUNNING: {State.RUNNING, State.FINALIZED},
    State.FINALIZED: {State.FINALIZED},
}


@dataclass(frozen=True)
class Event:
    id: int
    tenant_id: str
    execution_id: str
    state: str
    payload: dict[str, Any]
    hash_prev: Optional[str]
    hash_current: str
    created_at: Optional[str] = None


@dataclass(frozen=True)
class VerifyResult:
    valid: bool
    head_hash: Optional[str]
    event_count: int
    reason: Optional[str] = None


def validate_transition(current_state: State, next_state: State) -> None:
    if next_state not in _ALLOWED_TRANSITIONS[current_state]:
        raise ValueError(f"Illegal transition: {current_state} -> {next_state}")


def canonical_payload(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_lineage(prev_hash: Optional[str], payload: dict[str, Any]) -> str:
    prev = prev_hash or ""
    material = f"{prev}:{canonical_payload(payload)}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def verify_execution(events: list[Event]) -> VerifyResult:
    if not events:
        return VerifyResult(valid=True, head_hash=None, event_count=0)

    events_sorted = sorted(events, key=lambda e: e.id)

    prev_hash: Optional[str] = None
    current_state = State.IDLE
    finalized_count = 0

    for i, event in enumerate(events_sorted):
        next_state = State(event.state)
        try:
            validate_transition(current_state, next_state)
        except ValueError as exc:
            return VerifyResult(False, None, len(events_sorted), str(exc))

        if next_state == State.FINALIZED:
            finalized_count += 1
            if finalized_count > 1:
                return VerifyResult(False, None, len(events_sorted), "Multiple FINALIZED events")

            if i != len(events_sorted) - 1:
                return VerifyResult(False, None, len(events_sorted), "FINALIZED is not terminal")

        recomputed = compute_lineage(prev_hash, event.payload)
        if recomputed != event.hash_current:
            return VerifyResult(False, None, len(events_sorted), f"Hash mismatch at event_id={event.id}")

        if event.hash_prev != prev_hash:
            return VerifyResult(False, None, len(events_sorted), f"Broken chain link at event_id={event.id}")

        prev_hash = event.hash_current
        current_state = next_state

    return VerifyResult(True, prev_hash, len(events_sorted))


def hash32(value: str) -> int:
    return zlib.crc32(value.encode("utf-8")) & 0x7FFFFFFF


async def advisory_lock_execution(conn: Any, tenant_id: str, execution_id: str) -> None:
    key1 = hash32(tenant_id)
    key2 = hash32(execution_id)
    await conn.execute("SELECT pg_advisory_xact_lock($1, $2)", key1, key2)


class PostgresEventStore:
    async def get_execution(self, conn: Any, tenant_id: str, execution_id: str) -> list[Event]:
        rows = await conn.fetch(
            """
            SELECT id, tenant_id, execution_id, state, payload, hash_prev, hash_current, created_at
            FROM events
            WHERE tenant_id=$1 AND execution_id=$2
            ORDER BY id ASC
            """,
            tenant_id,
            execution_id,
        )
        return [Event(**dict(row)) for row in rows]

    async def append(self, conn: Any, event: Event) -> None:
        await conn.execute(
            """
            INSERT INTO events (id, tenant_id, execution_id, state, payload, hash_prev, hash_current, created_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
            """,
            event.id,
            event.tenant_id,
            event.execution_id,
            event.state,
            event.payload,
            event.hash_prev,
            event.hash_current,
        )


AsyncExecutor = Callable[[], Any]


async def execute_with_execution_lock(
    conn: Any,
    tenant_id: str,
    execution_id: str,
    operation: AsyncExecutor,
) -> Any:
    await advisory_lock_execution(conn, tenant_id, execution_id)
    return await operation()

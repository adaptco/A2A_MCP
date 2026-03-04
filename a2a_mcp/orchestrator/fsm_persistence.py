from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional

from orchestrator import storage
from schemas.database import FSMEventModel, FSMExecutionModel, FSMSnapshotModel


DEFAULT_FSM_ID = "stateflow"


class IntegrityError(Exception):
    """Raised when append-only or lineage invariants are violated."""


@dataclass(frozen=True)
class EventRow:
    tenant_id: str
    fsm_id: str
    execution_id: str
    seq: int
    occurred_at_iso: str
    event_type: str
    event_version: int
    payload_canonical: bytes
    payload_hash: bytes
    prev_event_hash: Optional[bytes]
    event_hash: bytes
    system_version: str
    hash_version: int
    certification: str


def canonical_json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _parse_occurred_at(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _to_iso_z(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _event_meta_bytes(
    *,
    tenant_id: str,
    fsm_id: str,
    execution_id: str,
    seq: int,
    event_type: str,
    event_version: int,
    occurred_at_iso: str,
    system_version: str,
    hash_version: int,
    certification: str,
) -> bytes:
    return canonical_json_bytes(
        {
            "tenant_id": tenant_id,
            "fsm_id": fsm_id,
            "execution_id": execution_id,
            "seq": seq,
            "event_type": event_type,
            "event_version": event_version,
            "occurred_at": occurred_at_iso,
            "system_version": system_version,
            "hash_version": hash_version,
            "certification": certification,
        }
    )


class FSMEventStore:
    def __init__(self, db_manager: storage.DBManager | None = None):
        self._db = db_manager or storage._db_manager

    def append_event(
        self,
        *,
        tenant_id: str,
        execution_id: str,
        event_type: str,
        payload: dict[str, Any],
        occurred_at_iso: str,
        fsm_id: str = DEFAULT_FSM_ID,
        event_version: int = 1,
        system_version: str = "1.0.0",
        hash_version: int = 1,
        certification: str = "CERTIFIABLE",
        expected_seq: int | None = None,
        policy_hash: bytes = b"",
        role_matrix_ver: str = "unknown",
        materiality_ver: str = "unknown",
    ) -> EventRow:
        session = self._db.SessionLocal()
        try:
            execution = (
                session.query(FSMExecutionModel)
                .filter(
                    FSMExecutionModel.tenant_id == tenant_id,
                    FSMExecutionModel.execution_id == execution_id,
                )
                .first()
            )

            occurred_at = _parse_occurred_at(occurred_at_iso)

            if execution is None:
                execution = FSMExecutionModel(
                    tenant_id=tenant_id,
                    execution_id=execution_id,
                    fsm_id=fsm_id,
                    started_at=occurred_at,
                    head_seq=0,
                    head_hash=None,
                    status="RUNNING",
                    policy_hash=policy_hash,
                    role_matrix_ver=role_matrix_ver,
                    materiality_ver=materiality_ver,
                    system_version=system_version,
                    hash_version=hash_version,
                )
                session.add(execution)
                session.flush()

            seq = int(execution.head_seq) + 1
            if expected_seq is not None:
                if expected_seq <= int(execution.head_seq):
                    existing = (
                        session.query(FSMEventModel)
                        .filter(
                            FSMEventModel.tenant_id == tenant_id,
                            FSMEventModel.execution_id == execution_id,
                            FSMEventModel.seq == expected_seq,
                        )
                        .first()
                    )
                    if existing is None:
                        raise IntegrityError("Missing expected event for idempotent retry")
                    return self._to_event_row(existing)
                if expected_seq != seq:
                    raise IntegrityError(f"Sequence mismatch: expected {expected_seq} got {seq}")
            prev_hash = execution.head_hash
            canonical_payload = canonical_json_bytes(payload)
            payload_hash = sha256_bytes(canonical_payload)
            meta_bytes = _event_meta_bytes(
                tenant_id=tenant_id,
                fsm_id=execution.fsm_id,
                execution_id=execution_id,
                seq=seq,
                event_type=event_type,
                event_version=event_version,
                occurred_at_iso=occurred_at_iso,
                system_version=system_version,
                hash_version=hash_version,
                certification=certification,
            )
            event_hash = sha256_bytes((prev_hash or b"") + payload_hash + meta_bytes)

            existing = (
                session.query(FSMEventModel)
                .filter(
                    FSMEventModel.tenant_id == tenant_id,
                    FSMEventModel.execution_id == execution_id,
                    FSMEventModel.seq == seq,
                )
                .first()
            )
            if existing is not None:
                if (
                    existing.event_hash != event_hash
                    or existing.payload_hash != payload_hash
                    or existing.payload_canonical != canonical_payload
                    or existing.prev_event_hash != prev_hash
                    or existing.event_type != event_type
                ):
                    raise IntegrityError("Idempotency conflict: existing event differs for same sequence")
                return self._to_event_row(existing)

            row = FSMEventModel(
                tenant_id=tenant_id,
                fsm_id=execution.fsm_id,
                execution_id=execution_id,
                seq=seq,
                event_type=event_type,
                event_version=event_version,
                occurred_at=occurred_at,
                payload_canonical=canonical_payload,
                payload_hash=payload_hash,
                prev_event_hash=prev_hash,
                event_hash=event_hash,
                system_version=system_version,
                hash_version=hash_version,
                certification=certification,
            )
            session.add(row)

            execution.head_seq = seq
            execution.head_hash = event_hash
            if event_type in {"VERDICT_PASS", "RETRY_LIMIT_EXCEEDED"}:
                execution.status = "FINALIZED"
                execution.finalized_at = occurred_at
            elif event_type in {"VERDICT_FAIL", "REPAIR_ABORT"}:
                execution.status = "ABORTED"
                execution.finalized_at = occurred_at

            snapshot_hash = sha256_bytes(canonical_payload)
            session.add(
                FSMSnapshotModel(
                    tenant_id=tenant_id,
                    execution_id=execution_id,
                    snapshot_seq=seq,
                    snapshot_canonical=canonical_payload,
                    snapshot_hash=snapshot_hash,
                    created_at=occurred_at,
                )
            )
            session.commit()
            return EventRow(
                tenant_id=tenant_id,
                fsm_id=execution.fsm_id,
                execution_id=execution_id,
                seq=seq,
                occurred_at_iso=occurred_at_iso,
                event_type=event_type,
                event_version=event_version,
                payload_canonical=canonical_payload,
                payload_hash=payload_hash,
                prev_event_hash=prev_hash,
                event_hash=event_hash,
                system_version=system_version,
                hash_version=hash_version,
                certification=certification,
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def load_events(self, tenant_id: str, execution_id: str, from_seq: int = 1) -> list[EventRow]:
        session = self._db.SessionLocal()
        try:
            rows = (
                session.query(FSMEventModel)
                .filter(
                    FSMEventModel.tenant_id == tenant_id,
                    FSMEventModel.execution_id == execution_id,
                    FSMEventModel.seq >= from_seq,
                )
                .order_by(FSMEventModel.seq.asc())
                .all()
            )
            return [self._to_event_row(r) for r in rows]
        finally:
            session.close()

    def get_head(self, tenant_id: str, execution_id: str) -> tuple[int, Optional[bytes]]:
        session = self._db.SessionLocal()
        try:
            execution = (
                session.query(FSMExecutionModel)
                .filter(
                    FSMExecutionModel.tenant_id == tenant_id,
                    FSMExecutionModel.execution_id == execution_id,
                )
                .first()
            )
            if execution is None:
                return 0, None
            return int(execution.head_seq), execution.head_hash
        finally:
            session.close()

    def verify_chain(self, tenant_id: str, execution_id: str) -> bool:
        events = self.load_events(tenant_id, execution_id)
        prev: Optional[bytes] = None
        expected_seq = 1
        for event in events:
            if event.seq != expected_seq:
                return False
            meta = _event_meta_bytes(
                tenant_id=tenant_id,
                fsm_id=event.fsm_id,
                execution_id=execution_id,
                seq=event.seq,
                event_type=event.event_type,
                event_version=event.event_version,
                occurred_at_iso=event.occurred_at_iso,
                system_version=event.system_version,
                hash_version=event.hash_version,
                certification=event.certification,
            )
            expected_hash = sha256_bytes((prev or b"") + event.payload_hash + meta)
            if event.payload_hash != sha256_bytes(event.payload_canonical):
                return False
            if event.prev_event_hash != prev:
                return False
            if event.event_hash != expected_hash:
                return False
            prev = event.event_hash
            expected_seq += 1
        return True

    def latest_snapshot(self, tenant_id: str, execution_id: str) -> Optional[dict[str, Any]]:
        session = self._db.SessionLocal()
        try:
            snap = (
                session.query(FSMSnapshotModel)
                .filter(
                    FSMSnapshotModel.tenant_id == tenant_id,
                    FSMSnapshotModel.execution_id == execution_id,
                )
                .order_by(FSMSnapshotModel.snapshot_seq.desc())
                .first()
            )
            if snap is None:
                return None
            return json.loads(snap.snapshot_canonical.decode("utf-8"))
        finally:
            session.close()

    def export_execution_bundle_bytes(self, tenant_id: str, execution_id: str) -> bytes:
        head_seq, head_hash = self.get_head(tenant_id, execution_id)
        events = self.load_events(tenant_id, execution_id)
        payload = {
            "tenant_id": tenant_id,
            "execution_id": execution_id,
            "head_seq": head_seq,
            "head_hash": head_hash.hex() if head_hash else None,
            "events": [
                {
                    "seq": e.seq,
                    "occurred_at": e.occurred_at_iso,
                    "event_type": e.event_type,
                    "event_version": e.event_version,
                    "payload": json.loads(e.payload_canonical.decode("utf-8")),
                    "payload_hash": e.payload_hash.hex(),
                    "prev_event_hash": e.prev_event_hash.hex() if e.prev_event_hash else None,
                    "event_hash": e.event_hash.hex(),
                    "system_version": e.system_version,
                    "hash_version": e.hash_version,
                    "certification": e.certification,
                }
                for e in events
            ],
        }
        return canonical_json_bytes(payload)

    def _to_event_row(self, row: FSMEventModel) -> EventRow:
        return EventRow(
            tenant_id=row.tenant_id,
            fsm_id=row.fsm_id,
            execution_id=row.execution_id,
            seq=int(row.seq),
            occurred_at_iso=_to_iso_z(row.occurred_at),
            event_type=row.event_type,
            event_version=int(row.event_version),
            payload_canonical=row.payload_canonical,
            payload_hash=row.payload_hash,
            prev_event_hash=row.prev_event_hash,
            event_hash=row.event_hash,
            system_version=row.system_version,
            hash_version=int(row.hash_version),
            certification=row.certification,
        )


_DEFAULT_TENANT = os.getenv("DEFAULT_TENANT_ID", "default")


def persist_state_machine_snapshot(plan_id: str, snapshot: dict[str, Any], tenant_id: str = _DEFAULT_TENANT) -> None:
    history = snapshot.get("history", [])
    if not history:
        return

    rec = history[-1]
    occurred_at_iso = datetime.fromtimestamp(float(rec.get("timestamp", datetime.now(tz=timezone.utc).timestamp())), tz=timezone.utc).isoformat().replace("+00:00", "Z")

    store = FSMEventStore()
    store.append_event(
        expected_seq=len(history),
        tenant_id=tenant_id,
        execution_id=plan_id,
        event_type=str(rec.get("event", "UNKNOWN")),
        payload=snapshot,
        occurred_at_iso=occurred_at_iso,
    )


def load_state_machine_snapshot(plan_id: str, tenant_id: str = _DEFAULT_TENANT) -> Optional[dict[str, Any]]:
    return FSMEventStore().latest_snapshot(tenant_id, plan_id)

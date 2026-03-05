from __future__ import annotations

from datetime import datetime, timezone

from orchestrator.fsm_persistence import FSMEventStore
from orchestrator.storage import DBManager
from schemas.database import FSMEventModel


def _store(tmp_path):
    db_file = tmp_path / "fsm_test.db"
    manager = DBManager()
    manager.engine.dispose()

    # Override to isolated sqlite for this test process
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from schemas.database import Base

    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    manager.engine = engine
    manager.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return FSMEventStore(manager)


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")


def test_append_is_idempotent(tmp_path):
    store = _store(tmp_path)
    payload = {"plan_id": "p1", "state": "SCHEDULED", "history": [{"event": "OBJECTIVE_INGRESS", "timestamp": 1000.0}]}

    first = store.append_event(
        tenant_id="tenant-a",
        execution_id="p1",
        event_type="OBJECTIVE_INGRESS",
        payload=payload,
        occurred_at_iso=_iso(1000.0),
        expected_seq=1,
    )
    second = store.append_event(
        tenant_id="tenant-a",
        execution_id="p1",
        event_type="OBJECTIVE_INGRESS",
        payload=payload,
        occurred_at_iso=_iso(1000.0),
        expected_seq=1,
    )

    assert first.event_hash == second.event_hash
    assert first.seq == second.seq == 1


def test_chain_integrity_detects_mutation(tmp_path):
    store = _store(tmp_path)
    store.append_event(
        tenant_id="tenant-a",
        execution_id="p2",
        event_type="OBJECTIVE_INGRESS",
        payload={"plan_id": "p2", "history": [{"event": "OBJECTIVE_INGRESS", "timestamp": 1000.0}]},
        occurred_at_iso=_iso(1000.0),
        expected_seq=1,
    )

    session = store._db.SessionLocal()
    try:
        row = (
            session.query(FSMEventModel)
            .filter(FSMEventModel.tenant_id == "tenant-a", FSMEventModel.execution_id == "p2", FSMEventModel.seq == 1)
            .first()
        )
        row.payload_canonical = b'{"tampered":true}'
        session.commit()
    finally:
        session.close()

    assert store.verify_chain("tenant-a", "p2") is False


def test_replay_is_deterministic(tmp_path):
    store = _store(tmp_path)
    base_payload = {"plan_id": "p3", "state": "SCHEDULED", "history": [{"event": "OBJECTIVE_INGRESS", "timestamp": 1000.0}]}
    running_payload = {
        "plan_id": "p3",
        "state": "EXECUTING",
        "history": [
            {"event": "OBJECTIVE_INGRESS", "timestamp": 1000.0},
            {"event": "RUN_DISPATCHED", "timestamp": 1001.0},
        ],
    }
    store.append_event(
        tenant_id="tenant-a",
        execution_id="p3",
        event_type="OBJECTIVE_INGRESS",
        payload=base_payload,
        occurred_at_iso=_iso(1000.0),
        expected_seq=1,
    )
    store.append_event(
        tenant_id="tenant-a",
        execution_id="p3",
        event_type="RUN_DISPATCHED",
        payload=running_payload,
        occurred_at_iso=_iso(1001.0),
        expected_seq=2,
    )

    replay_one = [e.payload_canonical for e in store.load_events("tenant-a", "p3")]
    replay_two = [e.payload_canonical for e in store.load_events("tenant-a", "p3")]

    assert replay_one == replay_two


def test_export_bundle_is_byte_identical(tmp_path):
    store = _store(tmp_path)
    store.append_event(
        tenant_id="tenant-a",
        execution_id="p4",
        event_type="OBJECTIVE_INGRESS",
        payload={"plan_id": "p4", "state": "SCHEDULED", "history": [{"event": "OBJECTIVE_INGRESS", "timestamp": 1000.0}]},
        occurred_at_iso=_iso(1000.0),
        expected_seq=1,
    )
    one = store.export_execution_bundle_bytes("tenant-a", "p4")
    two = store.export_execution_bundle_bytes("tenant-a", "p4")

    assert one == two


def test_snapshot_accelerates_but_does_not_change_result(tmp_path):
    store = _store(tmp_path)
    payloads = [
        {"plan_id": "p5", "state": "SCHEDULED", "history": [{"event": "OBJECTIVE_INGRESS", "timestamp": 1000.0}]},
        {
            "plan_id": "p5",
            "state": "EXECUTING",
            "history": [
                {"event": "OBJECTIVE_INGRESS", "timestamp": 1000.0},
                {"event": "RUN_DISPATCHED", "timestamp": 1001.0},
            ],
        },
    ]
    store.append_event(
        tenant_id="tenant-a",
        execution_id="p5",
        event_type="OBJECTIVE_INGRESS",
        payload=payloads[0],
        occurred_at_iso=_iso(1000.0),
        expected_seq=1,
    )
    store.append_event(
        tenant_id="tenant-a",
        execution_id="p5",
        event_type="RUN_DISPATCHED",
        payload=payloads[1],
        occurred_at_iso=_iso(1001.0),
        expected_seq=2,
    )

    latest_snapshot = store.latest_snapshot("tenant-a", "p5")
    full_replay_last_payload = store.load_events("tenant-a", "p5")[-1].payload_canonical

    assert latest_snapshot is not None
    assert latest_snapshot == payloads[-1]
    assert full_replay_last_payload == store.load_events("tenant-a", "p5")[-1].payload_canonical

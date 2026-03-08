import time
import uuid
import threading

from orchestrator import storage
from orchestrator.stateflow import StateMachine, State, PartialVerdict
from schemas.database import PlanStateModel


def _wait_for_snapshot(plan_id: str, timeout: float = 2.0):
    deadline = time.time() + timeout
    snapshot = None
    while time.time() < deadline:
        snapshot = storage.load_plan_state(plan_id)
        if snapshot and snapshot.get("state") == State.RETRY.value and snapshot.get("attempts") == 1:
            return snapshot
        time.sleep(0.05)
    return snapshot


def test_plan_state_save_load_roundtrip():
    plan_id = f"plan-{uuid.uuid4()}"

    sm = StateMachine(
        max_retries=3,
        persistence_callback=lambda pid, snap: storage.save_plan_state(pid, snap),
    )
    sm.plan_id = plan_id

    sm.trigger("OBJECTIVE_INGRESS")
    sm.trigger("RUN_DISPATCHED")
    sm.trigger("EXECUTION_COMPLETE")

    def policy_partial():
        raise PartialVerdict()

    sm.evaluate_apply_policy(policy_partial)

    snapshot = _wait_for_snapshot(plan_id)
    assert snapshot is not None
    assert snapshot["state"] == State.RETRY.value
    assert snapshot["attempts"] == 1

    session = storage._db_manager.SessionLocal()
    try:
        row = session.query(PlanStateModel).filter(PlanStateModel.plan_id == plan_id).first()
        assert row is not None
    finally:
        session.close()

    loaded_snapshot = storage.load_plan_state(plan_id)
    assert loaded_snapshot is not None

    reconstructed = StateMachine.from_dict(loaded_snapshot)
    assert reconstructed.current_state() == sm.current_state()
    assert len(reconstructed.history) == len(sm.history)

def test_persistence_preserves_transition_order_under_concurrency():
    plan_id = f"plan-{uuid.uuid4()}"
    write_order = []

    def persistence_callback(pid, snap):
        state = snap.get("state")
        if state == State.SCHEDULED.value:
            time.sleep(0.2)
        else:
            time.sleep(0.01)
        storage.save_plan_state(pid, snap)
        write_order.append(state)

    sm = StateMachine(max_retries=3, persistence_callback=persistence_callback)
    sm.plan_id = plan_id

    t1 = threading.Thread(target=lambda: sm.trigger("OBJECTIVE_INGRESS"))
    t2 = threading.Thread(target=lambda: sm.trigger("RUN_DISPATCHED"))

    t1.start()
    t1.join()
    t2.start()
    t2.join()

    snapshot = storage.load_plan_state(plan_id)
    assert snapshot is not None
    assert snapshot["state"] == State.EXECUTING.value
    assert write_order == [State.SCHEDULED.value, State.EXECUTING.value]

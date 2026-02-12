# tests/test_stateflow.py
import pytest
from A2A_MCP.orchestrator.stateflow import StateMachine, State, PartialVerdict

def test_happy_path():
    sm = StateMachine(max_retries=3)
    sm.trigger("OBJECTIVE_INGRESS")
    assert sm.current_state() == State.SCHEDULED
    sm.trigger("RUN_DISPATCHED")
    assert sm.current_state() == State.EXECUTING
    sm.trigger("EXECUTION_COMPLETE", artifact_id="a1")
    assert sm.current_state() == State.EVALUATING

    # policy that returns True (pass)
    def policy_ok():
        return True

    sm.evaluate_apply_policy(policy_ok)
    assert sm.current_state() == State.TERMINATED_SUCCESS

def test_retry_limit_exceeded():
    sm = StateMachine(max_retries=2)
    sm.trigger("OBJECTIVE_INGRESS")
    sm.trigger("RUN_DISPATCHED")
    sm.trigger("EXECUTION_COMPLETE")

    # policy that requests partial verdict (retry) by raising PartialVerdict
    def policy_partial():
        raise PartialVerdict()

    # first partial -> RETRY
    sm.evaluate_apply_policy(policy_partial)
    assert sm.current_state() == State.RETRY
    # dispatch retry
    sm.trigger("RETRY_DISPATCHED")
    assert sm.current_state() == State.EXECUTING
    # execution completes again
    sm.trigger("EXECUTION_COMPLETE")
    # second partial -> now max_retries is 2 => should lead to TERMINATED_FAIL
    sm.evaluate_apply_policy(policy_partial)
    assert sm.current_state() == State.TERMINATED_FAIL

def test_override_forward_only():
    sm = StateMachine(max_retries=3)
    sm.trigger("OBJECTIVE_INGRESS")
    sm.trigger("RUN_DISPATCHED")
    # override to TERMINATED_SUCCESS
    rec = sm.override(State.TERMINATED_SUCCESS, reason="test", override_by="tester1")
    assert sm.current_state() == State.TERMINATED_SUCCESS
    # cannot override from terminated back to EXECUTING when forward_only True
    with pytest.raises(ValueError):
        sm.override(State.EXECUTING, reason="illegal", forward_only=True)
    # But non-forward override from terminated should still be blocked unless forward_only False is allowed
    with pytest.raises(ValueError):
        sm.override(State.SCHEDULED, reason="illegal-cannot", forward_only=True)

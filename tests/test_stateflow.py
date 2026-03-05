# tests/test_stateflow.py
import pytest
from orchestrator.stateflow import StateMachine, State, PartialVerdict

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
    # With unified FSM, VERDICT_PASS -> PRIME_RENDERING
    assert sm.current_state() == State.PRIME_RENDERING
    
    sm.trigger("PRIME_RENDER_COMPLETE")
    assert sm.current_state() == State.PRIME_VALIDATING
    
    sm.trigger("PRIME_VALIDATION_PASS")
    assert sm.current_state() == State.PRIME_EXPORTING
    
    sm.trigger("PRIME_EXPORT_COMPLETE")
    assert sm.current_state() == State.PRIME_COMMITTING
    
    sm.trigger("PRIME_COMMIT_COMPLETE")
    assert sm.current_state() == State.TERMINATED_SUCCESS

def test_retry_limit_exceeded():
    sm = StateMachine(max_retries=1)
    sm.trigger("OBJECTIVE_INGRESS")
    sm.trigger("RUN_DISPATCHED")
    sm.trigger("EXECUTION_COMPLETE")

    # policy that requests partial verdict (retry) by raising PartialVerdict
    def policy_partial():
        raise PartialVerdict()

    # first partial -> RETRY (attempts becomes 1, which == max_retries)
    # With max_retries=1 the very first VERDICT_PARTIAL should exhaust the limit
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

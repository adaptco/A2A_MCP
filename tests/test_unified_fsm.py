import pytest
from orchestrator.stateflow import StateMachine, State

def test_unified_fsm_prime_transitions():
    sm = StateMachine()
    assert sm.state == State.IDLE
    
    # 1. Start
    sm.trigger("OBJECTIVE_INGRESS")
    assert sm.state == State.SCHEDULED
    
    # 2. Execute
    sm.trigger("RUN_DISPATCHED")
    assert sm.state == State.EXECUTING
    
    # 3. Complete & Evaluate
    sm.trigger("EXECUTION_COMPLETE")
    assert sm.state == State.EVALUATING
    
    # 4. Pass Verdict -> Enter Prime Directive
    sm.trigger("VERDICT_PASS")
    assert sm.state == State.PRIME_RENDERING
    
    # 5. Prime Render Complete
    sm.trigger("PRIME_RENDER_COMPLETE")
    assert sm.state == State.PRIME_VALIDATING
    
    # 6. Prime Validation Pass
    sm.trigger("PRIME_VALIDATION_PASS", residual=0.05)
    assert sm.state == State.PRIME_EXPORTING
    
    # 7. Prime Export Complete
    sm.trigger("PRIME_EXPORT_COMPLETE")
    assert sm.state == State.PRIME_COMMITTING
    
    # 8. Prime Commit Complete -> Terminal
    sm.trigger("PRIME_COMMIT_COMPLETE")
    assert sm.state == State.TERMINATED_SUCCESS

def test_unified_fsm_prime_validation_failure():
    sm = StateMachine()
    sm.override(State.PRIME_VALIDATING)
    
    # Validation Fail -> REPAIR
    sm.trigger("PRIME_VALIDATION_FAIL", residual=0.99, reason="High PINN residual")
    assert sm.state == State.REPAIR
    
    # Repair -> EXECUTING
    sm.trigger("REPAIR_COMPLETE")
    assert sm.state == State.EXECUTING

if __name__ == "__main__":
    test_unified_fsm_prime_transitions()
    test_unified_fsm_prime_validation_failure()
    print("✓ Unified FSM tests passed")

from orchestrator.release_orchestrator import (
    ReleaseOrchestrator,
    ReleasePhase,
    ReleaseSignals,
)


def test_waiting_for_claude_phase():
    model = ReleaseOrchestrator()
    signals = ReleaseSignals(claude_task_complete=False, claude_checked_todos=1, claude_total_todos=9)
    assert model.resolve_phase(signals) == ReleasePhase.WAITING_FOR_CLAUDE
    state = model.system_state(signals)
    assert state["next_action"] == "wait_for_claude_todos_to_complete"


def test_validation_phase_when_tests_or_conflicts_pending():
    model = ReleaseOrchestrator()
    signals = ReleaseSignals(
        claude_task_complete=True,
        tests_passed=False,
        conflicts_resolved=True,
    )
    assert model.resolve_phase(signals) == ReleasePhase.RUNNING_VALIDATION


def test_ready_for_release_phase():
    model = ReleaseOrchestrator()
    signals = ReleaseSignals(
        claude_task_complete=True,
        tests_passed=True,
        conflicts_resolved=True,
        bot_review_complete=True,
        claude_checked_todos=9,
        claude_total_todos=9,
    )
    state = model.system_state(signals)
    assert state["phase"] == ReleasePhase.READY_FOR_RELEASE.value
    assert state["next_action"] == "publish_foundation_release_bundle"


def test_system_state_includes_runtime_bridge_snapshot():
    model = ReleaseOrchestrator()
    signals = ReleaseSignals(
        claude_task_complete=True,
        tests_passed=True,
        conflicts_resolved=True,
        bot_review_complete=False,
        handshake_initialized=True,
        runtime_assignment_written=True,
        runtime_workers_ready=3,
        token_stream_normalized=True,
    )
    state = model.system_state(signals)
    runtime_bridge = state["runtime_bridge"]
    assert runtime_bridge["handshake_initialized"] is True
    assert runtime_bridge["runtime_assignment_written"] is True
    assert runtime_bridge["runtime_workers_ready"] == 3
    assert runtime_bridge["token_stream_normalized"] is True
    assert state["bridge_schema"] == "runtime.assignment.v1"

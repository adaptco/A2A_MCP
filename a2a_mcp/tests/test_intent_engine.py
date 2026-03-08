import asyncio
import uuid
from types import SimpleNamespace

import pytest

from agents.pinn_agent import PINNAgent
from agents.tester import TestReport
from orchestrator.intent_engine import IntentEngine
from schemas.project_plan import PlanAction, ProjectPlan


def test_intent_engine_executes_plan(monkeypatch):
    engine = IntentEngine()

    generate_calls = []

    async def fake_generate_solution(parent_id, feedback=None):
        artifact = SimpleNamespace(
            artifact_id=str(uuid.uuid4()),
            content=f"solution for {feedback}",
            type="code_solution",
        )
        generate_calls.append((parent_id, artifact.artifact_id))
        return artifact

    async def fake_validate(_artifact_id):
        return TestReport(status="PASS", critique="looks good")

    monkeypatch.setattr(engine.coder, "generate_solution", fake_generate_solution)
    monkeypatch.setattr(engine.tester, "validate", fake_validate)

    saved = []

    def fake_save_artifact(artifact):
        saved.append(artifact)

    monkeypatch.setattr(engine.db, "save_artifact", fake_save_artifact)
    monkeypatch.setattr(engine.db, "get_artifact", lambda _id: None)

    plan = ProjectPlan(
        plan_id="plan-1",
        project_name="demo",
        requester="qa",
        actions=[
            PlanAction(action_id="a1", title="Build", instruction="Write code"),
            PlanAction(action_id="a2", title="Refine", instruction="Refine code"),
        ],
    )

    artifact_ids = asyncio.run(engine.execute_plan(plan))

    assert len(artifact_ids) == 6
    assert all(action.status == "completed" for action in plan.actions)
    # 2 actions * (1 code + 1 test + 1 pinn) = 6 artifacts
    assert len(saved) == 6


def test_intent_engine_does_not_double_persist_code_artifact(monkeypatch):
    engine = IntentEngine()

    async def fake_generate_solution(parent_id, feedback=None):
        artifact = SimpleNamespace(
            artifact_id=str(uuid.uuid4()),
            parent_artifact_id=parent_id,
            type="code_solution",
            content=f"solution for {feedback}",
            agent_name="CoderAgent-Alpha",
            version="1.1.0",
        )
        # Simulate CoderAgent persistence side effect.
        engine.db.save_artifact(artifact)
        return artifact

    async def fake_validate(_artifact_id):
        return TestReport(status="PASS", critique="ok")

    saved_ids = set()

    def fake_save_artifact(artifact):
        if artifact.artifact_id in saved_ids:
            raise RuntimeError("duplicate artifact id")
        saved_ids.add(artifact.artifact_id)

    monkeypatch.setattr(engine.coder, "generate_solution", fake_generate_solution)
    monkeypatch.setattr(engine.tester, "validate", fake_validate)
    monkeypatch.setattr(engine.db, "save_artifact", fake_save_artifact)
    monkeypatch.setattr(engine.db, "get_artifact", lambda _id: _id if _id in saved_ids else None)

    plan = ProjectPlan(
        plan_id="plan-root",
        project_name="demo",
        requester="qa",
        actions=[PlanAction(action_id="a1", title="Build", instruction="Write code")],
    )

    artifact_ids = asyncio.run(engine.execute_plan(plan))
    assert len(artifact_ids) == 3


def test_intent_engine_with_unified_fsm(monkeypatch):
    from orchestrator.stateflow import StateMachine, State
    sm = StateMachine()
    engine = IntentEngine(sm=sm)

    async def fake_generate_solution(parent_id, feedback=None, context_tokens=None):
        return SimpleNamespace(
            artifact_id=str(uuid.uuid4()),
            content="print('hello world')\n# This is a much longer artifact content to ensure PINN residual validation passes.\n# We need rigorous documentation and extensive comments to satisfy the physicist agent.\n# Residual should be below 0.15.",
            type="code_solution",
            metadata={}
        )

    async def fake_validate(_artifact_id, **kwargs):
        return TestReport(status="PASS", critique="looks good")

    monkeypatch.setattr(engine.coder, "generate_solution", fake_generate_solution)
    monkeypatch.setattr(engine.tester, "validate", fake_validate)
    monkeypatch.setattr(engine.db, "save_artifact", lambda x: None)
    monkeypatch.setattr(engine.db, "get_artifact", lambda x: None)

    plan = ProjectPlan(
        plan_id="plan-fsm",
        project_name="fsm-test",
        requester="tester",
        actions=[PlanAction(action_id="a1", title="Task", instruction="Do it")],
    )

    asyncio.run(engine.execute_plan(plan))

    # Verify FSM states
    states = [h.to_state for h in sm.history]
    assert State.PRIME_RENDERING in states
    assert State.PRIME_VALIDATING in states
    assert State.PRIME_EXPORTING in states
    assert State.PRIME_COMMITTING in states
    assert sm.state == State.TERMINATED_SUCCESS

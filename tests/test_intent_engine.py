import asyncio
import logging
import uuid
from types import SimpleNamespace

import pytest

from agents.pinn_agent import PINNAgent
from agents.tester import TestReport
from orchestrator.intent_engine import IntentEngine
from schemas.project_plan import PlanAction, ProjectPlan


def test_pinn_deterministic_embedding_is_stable():
    agent = PINNAgent()
    v1 = agent._deterministic_embedding("same prompt")
    v2 = agent._deterministic_embedding("same prompt")

    assert v1 == v2
    assert len(v1) == 16


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
    assert len(saved) == 2



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

    plan = ProjectPlan(
        plan_id="plan-root",
        project_name="demo",
        requester="qa",
        actions=[PlanAction(action_id="a1", title="Build", instruction="Write code")],
    )

    artifact_ids = asyncio.run(engine.execute_plan(plan))

    assert len(artifact_ids) == 3
    assert plan.actions[0].status == "completed"

def test_intent_engine_chains_from_previous_code_artifact(monkeypatch):
    engine = IntentEngine()

    parent_ids = []
    generated_ids = []

    async def fake_generate_solution(parent_id, feedback=None):
        parent_ids.append(parent_id)
        artifact_id = str(uuid.uuid4())
        generated_ids.append(artifact_id)
        return SimpleNamespace(artifact_id=artifact_id, content=f"solution for {feedback}")

    async def fake_validate(_artifact_id):
        return TestReport(status="PASS", critique="ok")

    monkeypatch.setattr(engine.coder, "generate_solution", fake_generate_solution)
    monkeypatch.setattr(engine.tester, "validate", fake_validate)
    monkeypatch.setattr(engine.db, "save_artifact", lambda _artifact: None)

    plan = ProjectPlan(
        plan_id="plan-root",
        project_name="demo",
        requester="qa",
        actions=[
            PlanAction(action_id="a1", title="Build", instruction="Write code"),
            PlanAction(action_id="a2", title="Refine", instruction="Refine code"),
        ],
    )

    asyncio.run(engine.execute_plan(plan))

    assert parent_ids[0] == "plan-root"
    assert parent_ids[1] == generated_ids[0]

def test_notify_completion_logs_exception(monkeypatch, caplog):
    """
    Test that _notify_completion logs an exception when notification fails,
    instead of silently swallowing it.
    """
    engine = IntentEngine()

    # Mock send_pipeline_completion_notification to raise an exception
    def mock_send_notification(*args, **kwargs):
        raise RuntimeError("Notification failed!")

    monkeypatch.setattr(
        "orchestrator.intent_engine.send_pipeline_completion_notification",
        mock_send_notification
    )

    # Ensure we capture logs
    caplog.set_level(logging.ERROR)

    # Call the method
    engine._notify_completion(
        project_name="test_project",
        success=True,
        completed_actions=1,
        failed_actions=0
    )

    # Assert that the error was logged
    assert "Notification failed!" in caplog.text
    # We expect at least one error log
    assert len(caplog.records) > 0
    assert caplog.records[0].levelname == "ERROR"

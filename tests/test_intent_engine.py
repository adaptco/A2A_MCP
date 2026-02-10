import asyncio
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))

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

    async def fake_generate_solution(parent_id, feedback=None):
        return SimpleNamespace(
            artifact_id=str(uuid.uuid4()),
            content=f"solution for {feedback}",
        )

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
    assert len(saved) == 4

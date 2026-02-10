from __future__ import annotations

from fastapi import FastAPI

from orchestrator.intent_engine import IntentEngine
from schemas.project_plan import ProjectPlan

app = FastAPI(title="A2A MCP Webhook")
engine = IntentEngine()


@app.post("/webhook")
async def process_plan(plan: ProjectPlan) -> dict:
    artifact_ids = await engine.execute_plan(plan)
    return {
        "plan_id": plan.plan_id,
        "artifact_ids": artifact_ids,
        "action_status": {action.action_id: action.status for action in plan.actions},
    }

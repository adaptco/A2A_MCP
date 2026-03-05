"""FastAPI app for orchestrator HTTP endpoints and plan ingress routes."""

from __future__ import annotations

import logging
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Depends

from orchestrator.intent_engine import IntentEngine
from orchestrator.webhook import ingress_router
from orchestrator.auth import authenticate_user
from orchestrator.logging import setup_logging
from orchestrator.actions_gateway import router as actions_router

setup_logging()

def validate_orchestrator_config():
    """Fail-fast on missing critical environment variables."""
    if os.getenv("ENV") == "production":
        if not os.getenv("LLM_API_KEY"):
            raise RuntimeError("LLM_API_KEY is required in production.")
        if not os.getenv("LLM_ENDPOINT"):
            raise RuntimeError("LLM_ENDPOINT is required in production.")

validate_orchestrator_config()

logger = logging.getLogger(__name__)

app = FastAPI(title="A2A Orchestrator API", version="1.0.0")
app.include_router(ingress_router)
app.include_router(actions_router)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


def _build_pipeline_response(result: Any) -> dict[str, Any]:
    test_summary = "\n".join(
        f"- {item['artifact']}: {item['status']} (score={item['judge_score']})"
        for item in result.test_verdicts
    )
    final_code = result.code_artifacts[-1].content if result.code_artifacts else ""
    return {
        "status": "A2A Workflow Complete" if result.success else "A2A Workflow Incomplete",
        "pipeline_results": {
            "plan_id": result.plan.plan_id,
            "blueprint_id": result.blueprint.plan_id,
            "research": [artifact.artifact_id for artifact in result.architecture_artifacts],
            "coding": [artifact.artifact_id for artifact in result.code_artifacts],
            "testing": result.test_verdicts,
        },
        "test_summary": test_summary,
        "final_code": final_code,
    }


@app.post("/orchestrate")
async def orchestrate(
    user_query: str = Query(..., min_length=1),
    requester: str = Query(default="api"),
    max_healing_retries: int = Query(default=3, ge=1, le=10),
    auth: dict = Depends(authenticate_user),
) -> dict[str, Any]:
    """Run the full multi-agent pipeline for a user query."""
    try:
        engine = IntentEngine()
        result = await engine.run_full_pipeline(
            description=user_query,
            requester=requester,
            max_healing_retries=max_healing_retries,
        )
        return _build_pipeline_response(result)
    except HTTPException:
        raise
    except Exception:  # noqa: BLE001 - Catch all to mask internal errors.
        logger.exception("orchestration failure")
        raise HTTPException(
            status_code=500, detail="orchestration failure: an internal error occurred"
        ) from None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "orchestrator.api:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False,
    )

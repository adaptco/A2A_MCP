from __future__ import annotations

from fastapi import FastAPI

from prime_directive.api.schemas import HealthResponse
from prime_directive.pipeline.context import PipelineContext
from prime_directive.pipeline.engine import PipelineEngine

app = FastAPI(title="PRIME_DIRECTIVE")
_engine = PipelineEngine(PipelineContext(run_id="bootstrap"))


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(**_engine.health())

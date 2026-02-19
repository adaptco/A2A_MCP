from __future__ import annotations

from prime_directive.pipeline.context import PipelineContext


class PipelineEngine:
    """Placeholder orchestration engine for staged migration."""

    def __init__(self, context: PipelineContext) -> None:
        self.context = context

    def health(self) -> dict[str, str]:
        return {"status": "ok", "run_id": self.context.run_id}

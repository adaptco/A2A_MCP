"""Canonical prompt-building input schemas."""

from pydantic import BaseModel, Field


class PromptIntent(BaseModel):
    """Structured intent/context passed by agents to the LLM adapter."""

    user_input: str = Field(default="", description="Primary user/task payload.")
    task_context: str | None = Field(
        default=None,
        description="Supporting context that frames how user_input should be interpreted.",
    )
    workflow_constraints: list[str] = Field(
        default_factory=list,
        description="Agent/workflow-specific constraints to append after platform constraints.",
    )
    system_constraints: list[str] = Field(
        default_factory=list,
        description="Additional adapter-level system constraints.",
    )
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Optional tags for observability/traceability.",
    )

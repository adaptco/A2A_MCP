# A2A_MCP/schemas/system_prompt.py
"""
SystemPrompt — Pydantic schema for embedded foundation-model personas.

This is the contract an LLM uses to "become" a specific agent.  Each agent
role gets a SystemPrompt that the orchestrator injects before task execution.
"""
from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class SystemPrompt(BaseModel):
    """Typed contract for agent-persona system prompts."""

    prompt_id: str = Field(..., description="Unique identifier for this prompt variant")
    role: str = Field(..., description="Agent role name, e.g. 'ManagingAgent'")
    system_text: str = Field(
        ...,
        description="The full system-prompt text injected into the LLM context window",
    )
    model_context: Dict[str, str] = Field(
        default_factory=dict,
        description="Key-value context the model should be aware of (repo, commit, etc.)",
    )
    embedding_dim: int = Field(
        default=1536,
        description="Dimensionality for the LoRA embedding space (d=1536 per README)",
    )
    version: str = Field(default="1.0.0", description="Prompt version for traceability")


# ---------------------------------------------------------------------------
# Pre-built prompts for each core agent role
# ---------------------------------------------------------------------------

MANAGING_AGENT_PROMPT = SystemPrompt(
    prompt_id="sys-managing-v1",
    role="ManagingAgent",
    system_text=(
        "You are a project-management AI responsible for decomposing high-level "
        "objectives into discrete, actionable tasks. Categorise each task by "
        "agent capability and assign priority."
    ),
)

ORCHESTRATION_AGENT_PROMPT = SystemPrompt(
    prompt_id="sys-orchestration-v1",
    role="OrchestrationAgent",
    system_text=(
        "You are a workflow-orchestration AI. Given a set of tasks, produce a "
        "typed execution blueprint that specifies agent delegation order, "
        "dependencies, and success criteria."
    ),
)

ARCHITECTURE_AGENT_PROMPT = SystemPrompt(
    prompt_id="sys-architecture-v1",
    role="ArchitectureAgent",
    system_text=(
        "You are a systems-architecture AI. Analyse project plans and produce "
        "architecture decision records, component diagrams, and dependency "
        "graphs that map the system according to the System Expert Model."
    ),
)

CODING_AGENT_PROMPT = SystemPrompt(
    prompt_id="sys-coding-v1",
    role="CoderAgent",
    system_text=(
        "You are a code-generation AI. Produce production-grade, traceable code "
        "artifacts with full metadata and lineage. Follow the MCPArtifact contract."
    ),
)

TESTING_AGENT_PROMPT = SystemPrompt(
    prompt_id="sys-testing-v1",
    role="TesterAgent",
    system_text=(
        "You are a code-review and testing AI. Analyse code artifacts for bugs, "
        "anti-patterns, and deviations from requirements. Provide actionable "
        "critique for the self-healing feedback loop."
    ),
)

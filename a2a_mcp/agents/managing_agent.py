# A2A_MCP/agents/managing_agent.py
"""
ManagingAgent — Task categorisation and swarm dispatch.

Accepts a free-text project description, breaks it into discrete
PlanAction tasks, and assigns each to the appropriate downstream agent.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import List, Optional

from orchestrator.llm_adapters.base import InternalLLMRequest
from orchestrator.llm_util import LLMService
from orchestrator.storage import DBManager
from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import PlanAction, ProjectPlan
from schemas.prompt_inputs import PromptIntent


class ManagingAgent:
    """Categorises a project description into actionable `PlanAction` items."""

    AGENT_NAME = "ManagingAgent-Alpha"
    VERSION = "1.0.0"

    def __init__(self) -> None:
        self.llm = LLMService()
        self.db = DBManager()

    async def categorize_project(
        self,
        description: str,
        requester: str = "system",
    ) -> ProjectPlan:
        """
        Use the LLM as an intent engine to decompose *description* into a
        series of PlanAction items, then wrap them in a ProjectPlan.
        """
        prompt_intent = PromptIntent(
            task_context=description,
            user_input="Decompose the project into numbered tasks with a short title and one-line instruction per task.",
            workflow_constraints=[
                "Act as a project-management planner.",
                "Return output as a numbered task list that is easy to parse line-by-line.",
            ],
            metadata={
                "agent": self.AGENT_NAME,
                "requester": requester,
                "summary": f"Categorizing project: {description[:50]}...",
                "constraints_count": len(["Act as a project-management planner.", "Return output as a numbered task list that is easy to parse line-by-line."])
            },
        )

        # Convert PromptIntent to string for LLMService compatibility
        prompt_str = (
            f"Context: {prompt_intent.task_context}\n"
            f"Task: {prompt_intent.user_input}\n"
            f"Constraints: {', '.join(prompt_intent.workflow_constraints)}"
        )
        # Optimize: Move blocking LLM call to a thread
        raw_response = await asyncio.to_thread(self.llm.call_llm, prompt=prompt_str)
        actions = self._parse_actions(raw_response)

        plan = ProjectPlan(
            plan_id=f"plan-{uuid.uuid4().hex[:8]}",
            project_name=description[:80],
            requester=requester,
            actions=actions,
        )

        # Persist a categorisation artifact for traceability
        artifact = MCPArtifact(
            artifact_id=f"cat-{uuid.uuid4().hex[:8]}",
            type="categorisation",
            content=raw_response,
            metadata={"agent": self.AGENT_NAME, "plan_id": plan.plan_id},
        )
        await asyncio.to_thread(self.db.save_artifact, artifact)
        return plan

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_actions(llm_text: str) -> List[PlanAction]:
        """
        Best-effort parser that turns numbered lines from the LLM into
        PlanAction objects.  Falls back to a single catch-all action when
        the output is not parseable.
        """
        actions: List[PlanAction] = []
        for line in llm_text.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            # Strip leading numbering  "1. ", "1) ", "- "
            for prefix in (".", ")", "-"):
                idx = line.find(prefix)
                if idx != -1 and idx < 5:
                    line = line[idx + 1 :].strip()
                    break

            actions.append(
                PlanAction(
                    action_id=f"act-{uuid.uuid4().hex[:8]}",
                    title=line[:60],
                    instruction=line,
                )
            )

        if not actions:
            actions.append(
                PlanAction(
                    action_id=f"act-{uuid.uuid4().hex[:8]}",
                    title="Catch-all task",
                    instruction=llm_text,
                )
            )
        return actions

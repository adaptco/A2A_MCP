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

from orchestrator.llm_util import LLMService
from orchestrator.storage import DBManager
from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import PlanAction, ProjectPlan


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
        prompt = (
            "You are a project-management AI. "
            "Break the following project description into a numbered list of "
            "discrete tasks. For each task provide a short title and a one-line "
            "instruction.\n\n"
            f"Project description:\n{description}"
        )

        loop = asyncio.get_running_loop()
        raw_response = await loop.run_in_executor(None, self.llm.call_llm, prompt)
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
        await loop.run_in_executor(None, self.db.save_artifact, artifact)
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

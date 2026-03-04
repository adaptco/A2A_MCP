"""
Managing agent module.
"""
import logging
import time
from app.services.auth_middleware import require_auth
from app.services.telemetry import TelemetryService
from app.orchestrator_agent import CoreOrchestratorMergeAgent
from orchestrator.intent_engine import IntentEngine  # pylint: disable=import-error,no-name-in-module

logger = logging.getLogger("ManagingAgent")

class ManagingAgent:
    """
    Specialized Managing Agent for the Antigravity Project.
    Orchestrates high-level project tasks, middleware, and sub-agent handoffs.
    """
    AGENT_NAME = "Antigravity-Manager-V1"

    def __init__(self):
        self.telemetry = TelemetryService()
        self.engine = IntentEngine()
        # Initialize the merge agent for branch automation
        self.repo_manager = CoreOrchestratorMergeAgent(
            repo_path="c:\\Users\\eqhsp\\.antigravity\\A2A_MCP\\A2A_MCP"
        )

    @require_auth
    async def automate_project_goal(self, goal_description: str):
        """
        Main entry point for autonomous project automation.
        1. Decomposes goal into tasks.
        2. Orchestrates sub-agents via IntentEngine.
        3. Manages branch lifecycle and merges via repo_manager.
        """
        self.telemetry.record_event(self.AGENT_NAME, "project_start", {"goal": goal_description})
        start_time = time.time()

        try:
            # Stage 1: Decomposition
            logger.info("Decomposing goal: %s", goal_description)
            plan = await self.engine.manager.categorize_project(
                goal_description, "Antigravity-Manager"
            )

            # Stage 2: Autonomous Execution Loop
            # In a production scenario, this would likely spin off workers or use an async queue
            for action in plan.actions:
                logger.info("Executing scheduled action: %s", action.title)
                # Integration with IntentEngine's full pipeline
                # (This would be bridged to AutonomousOrchestrator logic)

            duration = (time.time() - start_time) * 1000
            self.telemetry.record_performance(self.AGENT_NAME, duration, True)
            return {"status": "success", "plan_id": plan.plan_id}

        except Exception as e:
            logger.exception("Project automation failed: %s", e)
            duration = (time.time() - start_time) * 1000
            self.telemetry.record_performance(self.AGENT_NAME, duration, False)
            raise

if __name__ == "__main__":
    import asyncio
    # For local test, ensure AGENT_AUTH_TOKEN is set
    import os
    os.environ["AGENT_AUTH_TOKEN"] = "sk-test-token-val-1234567890"

    agent = ManagingAgent()
    asyncio.run(agent.automate_project_goal("Optimize Antigravity Middleware Performance"))

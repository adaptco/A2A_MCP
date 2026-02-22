import asyncio
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies before import
sys.modules['schemas'] = MagicMock()
sys.modules['schemas.agent_artifacts'] = MagicMock()
sys.modules['schemas.project_plan'] = MagicMock()
sys.modules['orchestrator'] = MagicMock()
sys.modules['orchestrator.storage'] = MagicMock()

# Setup mocks
from schemas.agent_artifacts import MCPArtifact
from schemas.project_plan import ProjectPlan, PlanAction
from orchestrator.storage import DBManager

# Mock return values for Pydantic models
ProjectPlan.model_dump_json.return_value = "{}"

from agents.orchestration_agent import OrchestrationAgent

async def main():
    agent = OrchestrationAgent()
    # Mock the DBManager instance
    agent.db = MagicMock(spec=DBManager)

    print("Building blueprint...")
    plan = await agent.build_blueprint(
        project_name="Test Project",
        task_descriptions=["Task 1", "Task 2"]
    )

    # Verify save_artifact was called
    if agent.db.save_artifact.called:
        print("SUCCESS: save_artifact was called.")
    else:
        print("FAILURE: save_artifact was NOT called.")
        sys.exit(1)

    print("Verification complete.")

if __name__ == "__main__":
    asyncio.run(main())

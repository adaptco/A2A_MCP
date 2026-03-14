from schemas.agent_artifacts import MCPArtifact
from orchestrator.llm_util import LLMService
from orchestrator.storage import DBManager
from pydantic import BaseModel

class TestReport(BaseModel):
    status: str  # "PASS" or "FAIL"
    critique: str

class TesterAgent:
    def __init__(self):
        self.agent_name = "TesterAgent-Alpha"
        self.llm = LLMService()
        self.db = DBManager()

    async def validate(self, artifact_id: str) -> TestReport:
        """
        Phase 2 Logic: Analyzes code artifacts and generates 
        actionable feedback for self-healing.
        """
        artifact = self.db.get_artifact(artifact_id)
        
        # Phase 3 Logic: Using LLM to verify code logic vs. requirements
        prompt = f"Analyze this code for bugs or anti-patterns:\n{artifact.content}"
        analysis = self.llm.call_llm(prompt)

        # Determine status (Heuristic for demo, LLM-guided for Production)
        status = "FAIL" if "error" in analysis.lower() or "bug" in analysis.lower() else "PASS"
        
        return TestReport(
            status=status,
            critique=analysis
        )

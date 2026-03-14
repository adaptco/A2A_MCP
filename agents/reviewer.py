"""
This module defines the ReviewerAgent for evaluating code artifacts.
"""
import uuid
from types import SimpleNamespace

from schemas.agent_artifacts import MCPArtifact
from orchestrator.llm_util import LLMService
from orchestrator.storage import DBManager

class ReviewerAgent:
    """
    Agent responsible for reviewing generated code and providing feedback.
    """
    def __init__(self):
        self.agent_name = "ReviewerAgent"
        self.version = "1.0.0"
        self.llm = LLMService()
        self.db = DBManager()

    async def review_artifact(self, artifact_id: str) -> MCPArtifact:
        """
        Reviews an existing artifact and produces a review report.
        """
        artifact = self.db.get_artifact(artifact_id)

        if not artifact:
            return None

        prompt = (
            f"Please review the following code artifact:\n\n"
            f"Type: {artifact.type}\n"
            f"Content: {artifact.content}\n\n"
            f"Provide a detailed review including quality, security, and performance considerations."
        )
        
        review_content = await self.llm.acall_llm(prompt)
        if review_content is None:
            review_content = "Review failed: No response from LLM."

        review_artifact = MCPArtifact(
            artifact_id=str(uuid.uuid4()),
            agent_name=self.agent_name,
            type="review_report",
            content=review_content,
            metadata={
                "reviewed_artifact_id": artifact_id,
                "version": self.version,
            },
        )
        
        db_artifact = SimpleNamespace(
            artifact_id=review_artifact.artifact_id,
            parent_artifact_id=artifact_id,
            agent_name=review_artifact.agent_name,
            version=self.version,
            type=review_artifact.type,
            content=review_artifact.content,
        )

        self.db.save_artifact(db_artifact)
        return review_artifact

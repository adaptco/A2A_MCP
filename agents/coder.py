"""
This module defines the CoderAgent for generating and managing code artifacts.
"""
import uuid
from types import SimpleNamespace

from schemas.agent_artifacts import MCPArtifact
from orchestrator.llm_util import LLMService
from orchestrator.storage import DBManager

# pylint: disable=too-few-public-methods
class CoderAgent:
    """
    Agent responsible for ingesting context and generating traceable code solutions.
    """
    def __init__(self):
        self.agent_name = "CoderAgent"
        self.version = "1.1.0"
        self.llm = LLMService()
        self.db = DBManager()

    async def generate_solution(self, parent_id: str, feedback: str = None) -> MCPArtifact:
        """
        Ingests parent context to produce a persistent, traceable code artifact.
        """
        parent_context = self.db.get_artifact(parent_id)

        if parent_context:
            context_content = parent_context.content
        else:
            context_content = "No previous context found. Proceeding with initial architectural build."

        prompt = f"Context: {context_content}\nFeedback: {feedback if feedback else 'Initial build'}"
        code_solution = self.llm.call_llm(prompt)

        artifact = MCPArtifact(
            artifact_id=str(uuid.uuid4()),
            agent_name=self.agent_name,
            type="code_solution",
            content=code_solution,
            metadata={
                "parent_artifact_id": parent_id,
                "feedback": feedback,
                "version": self.version,
            },
        )
        db_artifact = SimpleNamespace(
            artifact_id=artifact.artifact_id,
            parent_artifact_id=parent_id,
            agent_name=artifact.agent_name,
            version=self.version,
            type=artifact.type,
            content=artifact.content,
        )

        self.db.save_artifact(db_artifact)
        return artifact

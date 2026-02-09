from schemas.agent_artifacts import MCPArtifact
from orchestrator.llm_util import LLMService
from orchestrator.storage import DBManager
import uuid

class CoderAgent:
    def __init__(self):
        self.agent_name = "CoderAgent-Alpha"
        self.version = "1.1.0"
        self.llm = LLMService()
        self.db = DBManager()

    async def generate_solution(self, parent_id: str, feedback: str = None) -> MCPArtifact:
        """
        Directives: Phase 1 Reliability & Metadata Traceability.
        Ingests parent context to produce a persistent, traceable code artifact.
        """
        # Retrieve context from persistence layer
        parent_context = self.db.get_artifact(parent_id)
        
        # Phase 3 Logic: Intelligent generation vs. Heuristic fixes
        prompt = f"Context: {parent_context.content}\nFeedback: {feedback if feedback else 'Initial build'}"
        code_solution = await self.llm.generate(prompt)

        # Create Contract-First Artifact
        artifact = MCPArtifact(
            artifact_id=str(uuid.uuid4()),
            parent_artifact_id=parent_id,
            agent_name=self.agent_name,
            version=self.version,
            type="code_solution",
            content=code_solution
        )

        # Persistence & Traceability
        self.db.save_artifact(artifact)
        return artifact

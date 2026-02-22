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
        
        # --- FIX: Handle Empty Database (NoneType) ---
        if parent_context:
            context_content = parent_context.content
        else:
            context_content = "No previous context found. Proceeding with initial architectural build."

        # Phase 3 Logic: Intelligent generation vs. Heuristic fixes
        prompt = f"Context: {context_content}\nFeedback: {feedback if feedback else 'Initial build'}"
        
        # Ensure we use the 'call_llm' method defined in your llm_util.py
        code_solution = await self.llm.call_llm_async(prompt)

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

from schemas.agent_artifacts import MCPArtifact
from orchestrator.llm_util import LLMService
from orchestrator.storage import DBManager
from typing import Any, Iterable
import uuid

class CoderAgent:
    def __init__(self):
        self.agent_name = "CoderAgent-Alpha"
        self.version = "1.1.0"
        self.llm = LLMService()
        self.db = DBManager()

    @staticmethod
    def _format_context_tokens(context_tokens: Iterable[Any] | None) -> str:
        """Render structured vector-context tokens for runtime LLM grounding."""
        if not context_tokens:
            return "No runtime context tokens provided."

        lines = []
        for idx, token in enumerate(context_tokens, start=1):
            text = str(getattr(token, "text", "")).strip()
            token_id = str(getattr(token, "token_id", "unknown"))
            score = getattr(token, "score", None)
            source = str(getattr(token, "source_artifact_id", "unknown"))
            snippet = " ".join(text.split())
            if len(snippet) > 220:
                snippet = snippet[:217] + "..."
            if score is None:
                lines.append(
                    f"{idx}. token={token_id} source={source} text={snippet}"
                )
            else:
                lines.append(
                    f"{idx}. score={float(score):.3f} token={token_id} source={source} text={snippet}"
                )
        return "\n".join(lines)

    async def generate_solution(
        self,
        parent_id: str,
        feedback: str = None,
        context_tokens: Iterable[Any] | None = None,
    ) -> MCPArtifact:
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

        runtime_token_context = self._format_context_tokens(context_tokens)
        prompt = (
            f"Persistent Context:\n{context_content}\n\n"
            "Runtime Context Tokens:\n"
            f"{runtime_token_context}\n\n"
            f"Task Feedback:\n{feedback if feedback else 'Initial build'}"
        )
        
        # Ensure we use the 'call_llm' method defined in your llm_util.py
        code_solution = self.llm.call_llm(
            prompt,
            system_prompt=(
                "You are CoderAgent-Alpha. Use runtime context tokens as grounding "
                "for implementation decisions, and keep outputs production-safe."
            ),
        )

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

from schemas.agent_artifacts import MCPArtifact
from orchestrator.llm_util import LLMService
from orchestrator.storage import DBManager
from typing import Any, Iterable
from pydantic import BaseModel

class TestReport(BaseModel):
    __test__ = False
    status: str  # "PASS" or "FAIL"
    critique: str

class TesterAgent:
    __test__ = False
    def __init__(self):
        self.agent_name = "TesterAgent-Alpha"
        self.llm = LLMService()
        self.db = DBManager()

    @staticmethod
    def _format_context_tokens(context_tokens: Iterable[Any] | None) -> str:
        """Render structured vector-context tokens for runtime validation."""
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

    async def validate(
        self,
        artifact_id: str,
        supplemental_context: str | None = None,
        context_tokens: Iterable[Any] | None = None,
    ) -> TestReport:
        """
        Phase 2 Logic: Analyzes code artifacts and generates 
        actionable feedback for self-healing.
        """
        artifact = self.db.get_artifact(artifact_id)
        if artifact is None:
            return TestReport(
                status="FAIL",
                critique=f"Artifact not found: {artifact_id}",
            )
        
        # Phase 3 Logic: Using LLM to verify code logic vs. requirements
        token_context = self._format_context_tokens(context_tokens)
        prompt = (
            "Analyze this code for bugs, regressions, and anti-patterns.\n\n"
            f"Code:\n{artifact.content}\n\n"
            "Runtime Context Tokens:\n"
            f"{token_context}"
        )
        if supplemental_context:
            prompt = (
                f"{prompt}\n\n"
                "Retrieved vector context:\n"
                f"{supplemental_context}"
            )
        analysis = self.llm.call_llm(
            prompt,
            system_prompt=(
                "You are TesterAgent-Alpha. Use runtime context tokens to evaluate "
                "whether the implementation satisfies constraints and safety checks."
            ),
        )

        # Determine status (Heuristic for demo, LLM-guided for Production)
        status = "FAIL" if "error" in analysis.lower() or "bug" in analysis.lower() else "PASS"
        
        return TestReport(
            status=status,
            critique=analysis
        )

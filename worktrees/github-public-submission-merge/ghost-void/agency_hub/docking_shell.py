"""
DockingShell - The Hub controller for Agentic Field Games.

Implements the core cycle: Observe → Normalize → Unify → Act
Supports pluggable token synthesizers (heuristic or LLM-backed).
"""
import json
import numpy as np
from typing import Dict, List, Any, Optional, Protocol, runtime_checkable
from .tensor_field import TensorField
from .spoke_adapter import SpokeAdapter


# ── Token Synthesizer Protocol ──────────────────────────────────────

@runtime_checkable
class TokenSynthesizer(Protocol):
    """Interface for action-token generation strategies."""

    def synthesize(
        self,
        unified_state: Dict[str, Any],
        raw_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Generate an action token from the current state."""
        ...


# ── Heuristic Synthesizer ──────────────────────────────────────────

class HeuristicSynthesizer:
    """Original rule-based token synthesis (explore / exploit)."""

    def synthesize(
        self,
        unified_state: Dict[str, Any],
        raw_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        scores = unified_state.get("similarity_scores", [])

        if not scores or max(scores) < 0.3:
            return {"action": "explore", "params": {"direction": "random"}}

        knowledge_idx = unified_state["knowledge_retrieved"][0]
        return {
            "action": "spawn_structure",
            "params": {"type": "platform", "knowledge_ref": knowledge_idx},
        }


# ── Task-Aware Heuristic Synthesizer ───────────────────────────────

class TaskHeuristicSynthesizer:
    """
    Heuristic synthesizer tuned for TaskSpoke environments.

    Decision logic:
    1. If a current task has 0 effort remaining → complete it.
    2. If a current task has effort remaining → work on it.
    3. Otherwise → start the first available task.
    4. Fallback → explore.
    """

    def synthesize(
        self,
        unified_state: Dict[str, Any],
        raw_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        current = raw_state.get("current_task")
        available = raw_state.get("available_tasks", [])
        work_remaining = raw_state.get("work_remaining", {})

        # If we're on a task with zero effort → complete
        if current and work_remaining.get(current, 0) <= 0:
            return {"action": "complete_task", "params": {}}

        # If we're on a task still needing work → work on it
        if current and work_remaining.get(current, 0) > 0:
            return {"action": "work_on_task", "params": {}}

        # Not on any task → start next available
        if available:
            return {
                "action": "start_task",
                "params": {"task_name": available[0]},
            }

        # Nothing to do
        return {"action": "explore", "params": {}}


# ── LLM Synthesizer ───────────────────────────────────────────────

class LLMSynthesizer:
    """
    Token synthesizer backed by Google Gemini API.

    Sends the unified + raw state as context and expects
    a JSON action token in return.
    """

    SYSTEM_PROMPT = """\
You are a Task Navigation Agent. You receive the current state of a task
graph and must decide the single best next action.

RULES:
- You MUST respond with ONLY a JSON object: {"action": "<name>", "params": {…}}
- Valid actions: start_task, work_on_task, complete_task, skip_task, navigate_to, explore
- start_task requires params.task_name (a task from available_tasks)
- navigate_to requires params.task_name
- skip_task requires params.task_name
- work_on_task and complete_task take no params
- Respect dependencies: only start/navigate to tasks in available_tasks
- If current_task has work_remaining == 0, you should complete_task
- If current_task has work_remaining > 0, you should work_on_task
- If no current_task, pick from available_tasks using start_task
- Minimise total cycles — be efficient
"""

    def __init__(self, model: str = "gemini-2.0-flash", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key) if self.api_key else genai.Client()
            except ImportError:
                raise ImportError(
                    "google-genai is required for LLMSynthesizer. "
                    "Install with: pip install google-genai"
                )
        return self._client

    def synthesize(
        self,
        unified_state: Dict[str, Any],
        raw_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        client = self._get_client()

        user_prompt = (
            f"Current state:\n"
            f"  current_task: {raw_state.get('current_task')}\n"
            f"  task_status: {json.dumps(raw_state.get('task_status', {}))}\n"
            f"  available_tasks: {raw_state.get('available_tasks', [])}\n"
            f"  available_actions: {raw_state.get('available_actions', [])}\n"
            f"  work_remaining: {json.dumps(raw_state.get('work_remaining', {}))}\n"
            f"  completion_pct: {raw_state.get('completion_pct', 0):.0f}%\n"
            f"  knowledge_similarity: {unified_state.get('similarity_scores', [])}\n"
            f"\nDecide the next action."
        )

        try:
            response = client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config={
                    "system_instruction": self.SYSTEM_PROMPT,
                    "temperature": 0.1,
                },
            )
            text = response.text.strip()
            # Strip markdown fences if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            token = json.loads(text)
            if "action" not in token:
                raise ValueError("Missing 'action' key")
            return token

        except Exception as e:
            print(f"  [LLM] Error: {e} — falling back to heuristic")
            return TaskHeuristicSynthesizer().synthesize(unified_state, raw_state)


# ── Docking Shell ──────────────────────────────────────────────────

class DockingShell:
    """Central controller for the Agency Hub."""

    def __init__(
        self,
        embedding_dim: int = 64,
        synthesizer: Optional[TokenSynthesizer] = None,
    ):
        """
        Initialize the Docking Shell.

        Args:
            embedding_dim: Dimensionality of the cognitive manifold
            synthesizer: Strategy for generating action tokens.
                         Defaults to HeuristicSynthesizer.
        """
        self.tensor_field = TensorField(embedding_dim=embedding_dim)
        self.spoke: Optional[SpokeAdapter] = None
        self.cycle_count = 0
        self.synthesizer = synthesizer or HeuristicSynthesizer()

    def dock(self, spoke: SpokeAdapter) -> bool:
        """Connect to a Field Game (Spoke)."""
        self.spoke = spoke
        print(f"[DOCK] Connected to: {spoke.get_name()}")
        print(f"[DOCK] State schema: {spoke.get_state_schema()}")
        return True

    def inject_knowledge(self, concepts: List[np.ndarray]):
        """Prime the RAG system with knowledge vectors."""
        self.tensor_field.inject_knowledge(concepts)
        print(f"[KNOWLEDGE] Injected {len(concepts)} concepts")

    def cycle(self) -> Dict[str, Any]:
        """
        Execute one cycle: Observe → Normalize → Unify → Act.

        Returns:
            Dictionary with cycle results
        """
        if not self.spoke:
            raise RuntimeError("No spoke docked. Call dock() first.")

        self.cycle_count += 1

        # 1. OBSERVE
        raw_state = self.spoke.observe()

        # 2. NORMALIZE
        voxel_tensor = self.tensor_field.voxelize_state(raw_state)
        eigenstate = self.tensor_field.compute_eigenstate(voxel_tensor)

        # 3. UNIFY
        unified_state = self.tensor_field.rag_unify(eigenstate)

        # 4. ACT — delegated to synthesizer
        token = self.synthesizer.synthesize(unified_state, raw_state)
        success = self.spoke.act(token)

        # Log
        print(f"[CYCLE {self.cycle_count}] Eigenstate: {eigenstate[:5]}...")
        print(f"[CYCLE {self.cycle_count}] Token: {token}")
        print(f"[CYCLE {self.cycle_count}] Action success: {success}")

        return {
            "cycle": self.cycle_count,
            "eigenstate": eigenstate.tolist(),
            "unified_state": unified_state,
            "token": token,
            "success": success,
            "raw_state": raw_state,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Return statistics about the docking session."""
        return {
            "cycles_executed": self.cycle_count,
            "spoke_connected": self.spoke.get_name() if self.spoke else None,
            "embedding_dim": self.tensor_field.get_embedding_dim(),
            "knowledge_count": len(self.tensor_field.knowledge_vectors),
            "synthesizer": type(self.synthesizer).__name__,
        }

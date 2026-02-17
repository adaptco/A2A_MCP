"""Judge and Avatar integration for orchestrator.

Provides judge evaluation of agent actions and avatar personality integration.
"""

from typing import Dict, Any, List, Optional
from judge.decision import JudgmentModel, ActionScore
from avatars.registry import get_avatar_registry, AvatarRegistry
from avatars.avatar import Avatar
from avatars.setup import setup_default_avatars


class JudgeOrchestrator:
    """
    Integrates Judge and Avatar systems into orchestration flow.
    
    Responsibilities:
    1. Initialize Judge with spec-loaded criteria
    2. Initialize avatars and bind to agents
    3. Evaluate agent actions via Judge
    4. Provide avatar personality context to agents
    """

    def __init__(self, judge_preset: str = "simulation") -> None:
        """Initialize Judge and Avatar registry."""
        # Initialize Judge with spec-loaded criteria
        self.judge = JudgmentModel(preset=judge_preset)

        # Initialize Avatar registry and set up default avatars
        self.avatar_registry: AvatarRegistry = get_avatar_registry()
        setup_default_avatars()

        # Bind preset
        self._preset = judge_preset

    def get_avatar_for_agent(self, agent_name: str) -> Optional[Avatar]:
        """Get avatar bound to a specific agent."""
<<<<<<< HEAD
        return self.avatar_registry.get_avatar_for_agent(agent_name)
=======
        if hasattr(self.avatar_registry, "get_avatar_for_agent"):
            return self.avatar_registry.get_avatar_for_agent(agent_name)

        # Backward-compatible fallback for older registry API.
        for avatar in self.avatar_registry.list_avatars().values():
            if avatar.profile.bound_agent == agent_name:
                return avatar
        return None
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe

    def judge_action(
        self,
        action: str,
        context: Dict[str, Any],
        agent_name: Optional[str] = None
    ) -> ActionScore:
        """
        Judge a single action using MCDA framework.
        
        Args:
            action: Description of the action to judge
            context: Decision context (speed, fuel, position, etc.)
            agent_name: Optional agent performing the action
            
        Returns:
            ActionScore with overall and per-criterion scores
        """
        # Judge the action
        scores = self.judge.judge_actions([action], context)
        if scores:
            return scores[0]

        # Fallback if judge returns empty
        return ActionScore(action=action, overall_score=0.5)

    def judge_actions(
        self,
        actions: List[str],
        context: Dict[str, Any],
        agent_name: Optional[str] = None
    ) -> List[ActionScore]:
        """
        Judge multiple actions and return ranked list.
        
        Uses MCDA to score each action against safety, spec alignment,
        player intent, and latency criteria.
        """
        return self.judge.judge_actions(actions, context)

    def best_action(
        self,
        actions: List[str],
        context: Dict[str, Any],
        agent_name: Optional[str] = None
    ) -> Optional[ActionScore]:
        """Get highest-scoring action."""
        return self.judge.best_action(actions, context)

    def get_agent_system_context(self, agent_name: str) -> str:
        """Get system prompt for agent based on bound avatar."""
        avatar = self.get_avatar_for_agent(agent_name)
        if avatar:
            return avatar.get_system_context()

        # Fallback
        return f"You are {agent_name}. Follow specifications and provide high-quality output."

    def evaluate_agent_response(
        self,
        agent_name: str,
        response_text: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Evaluate an agent's response for quality and alignment.
        
        Returns evaluation report with Judge scores and avatar feedback.
        """
        avatar = self.get_avatar_for_agent(agent_name)

        return {
            "agent_name": agent_name,
            "avatar": avatar.profile.name if avatar else "unknown",
            "response_length": len(response_text),
            "avatar_style": avatar.profile.style if avatar else None,
            "judge_preset": self._preset,
            "context_keys": list(context.keys()),
        }

    def list_avatars(self) -> List[Dict[str, Any]]:
        """List all registered avatars with their bindings."""
        avatars = self.avatar_registry.list_avatars()
<<<<<<< HEAD
=======
        if isinstance(avatars, dict):
            avatars = list(avatars.values())
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
        return [
            {
                "avatar_id": a.profile.avatar_id,
                "name": a.profile.name,
                "style": a.profile.style.value,
                "bound_agent": a.profile.bound_agent,
<<<<<<< HEAD
                "description": a.profile.description,
=======
                "description": getattr(a.profile, "description", ""),
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
            }
            for a in avatars
        ]

    def __repr__(self) -> str:
        avatars = len(self.avatar_registry.list_avatars())
        return (
            f"<JudgeOrchestrator preset={self._preset} "
            f"avatars={avatars}>"
        )


# Global singleton
_judge_orchestrator: Optional[JudgeOrchestrator] = None


def get_judge_orchestrator(
    preset: str = "simulation",
    reset: bool = False,
) -> JudgeOrchestrator:
    """Access the global JudgeOrchestrator singleton."""
    global _judge_orchestrator
    if (
        _judge_orchestrator is None
        or reset
        or _judge_orchestrator._preset != preset
    ):
        _judge_orchestrator = JudgeOrchestrator(judge_preset=preset)
    return _judge_orchestrator

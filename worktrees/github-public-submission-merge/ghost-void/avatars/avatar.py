"""Avatar personality wrapper for agents."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any
import uuid


class AvatarStyle(str, Enum):
    """Avatar personality styles."""
    ENGINEER = "engineer"      # Precise, safety-first
    DESIGNER = "designer"      # Visual, metaphor-friendly
    DRIVER = "driver"          # Game-facing, conversational


@dataclass
class AvatarProfile:
    """Avatar personality and deployment configuration."""
    avatar_id: str = field(default_factory=lambda: f"avatar-{str(uuid.uuid4())[:8]}")
    name: str = ""
    style: AvatarStyle = AvatarStyle.ENGINEER
    bound_agent: Optional[str] = None  # Agent class name this avatar wraps
    voice_config: Dict[str, Any] = field(default_factory=dict)  # voice, pitch, speed, etc.
    ui_config: Dict[str, Any] = field(default_factory=dict)    # color, icon, theme, etc.
    system_prompt: str = ""  # Personality-specific instructions
    metadata: Dict[str, Any] = field(default_factory=dict)


class Avatar:
    """Thin wrapper over an agent, binding personality and UI."""

    def __init__(self, profile: AvatarProfile):
        self.profile = profile
        self.agent = None  # Bound at runtime based on profile.bound_agent

    def bind_agent(self, agent_instance: Any) -> None:
        """Bind a concrete agent instance to this avatar."""
        self.agent = agent_instance

    def get_system_context(self) -> str:
        """Return personality-modified system prompt for agent execution."""
        base = self.profile.system_prompt or f"You are a {self.profile.style.value} assistant."
        return base

    def get_voice_params(self) -> Dict[str, Any]:
        """Return voice configuration for TTS/speech synthesis."""
        return self.profile.voice_config

    def get_ui_params(self) -> Dict[str, Any]:
        """Return UI configuration for avatar rendering."""
        return self.profile.ui_config

    async def respond(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> str:
        """
        Invoke bound agent with personality wrapping.

        Args:
            prompt: User or game-world prompt
            context: Optional contextual information (game state, previous turns, etc.)

        Returns:
            Agent response (optionally post-processed with personality filters)
        """
        if not self.agent:
            raise RuntimeError(f"Avatar {self.profile.avatar_id} has no bound agent")

        # Modify prompt with avatar personality
        augmented_prompt = f"{self.get_system_context()}\n\n{prompt}"

        # Delegate to agent (signature depends on agent type)
        parent_id = (context or {}).get("artifact_id", "avatar_context")
        result = await self.agent.generate_solution(
            parent_id=parent_id,
            feedback=augmented_prompt
        )
        return result.content if hasattr(result, 'content') else str(result)

    def __repr__(self) -> str:
        return f"<Avatar id={self.profile.avatar_id} name={self.profile.name} style={self.profile.style.value}>"

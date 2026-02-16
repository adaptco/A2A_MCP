"""Avatar core classes for agent personality and voice."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List


class AvatarStyle(str, Enum):
    """Avatar personality styles aligned with agent behaviors."""
    ENGINEER = "engineer"    # Conservative, safety-first, cautious decisions
    DESIGNER = "designer"    # Creative, visually-driven, exploratory actions
    DRIVER = "driver"        # Fun-focused, engaging, in-universe actions


@dataclass
class AvatarProfile:
    """Configuration for an agent avatar personality."""
    avatar_id: str
    name: str
    style: AvatarStyle = AvatarStyle.ENGINEER
    bound_agent: Optional[str] = None
    description: str = ""

    # Voice and UI configuration
    voice_config: Dict[str, Any] = field(default_factory=dict)
    ui_config: Dict[str, Any] = field(default_factory=dict)

    # System prompt for LLM behavior
    system_prompt: str = ""

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate profile after initialization."""
        if not self.avatar_id:
            raise ValueError("avatar_id is required")
        if not self.name:
            raise ValueError("name is required")


class Avatar:
    """
    Personality wrapper for agent.
    Provides system context, voice params, and UI config based on style.
    """

    def __init__(self, profile: AvatarProfile) -> None:
        """Initialize avatar with personality profile."""
        self.profile = profile
        self._response_cache: Dict[str, str] = {}

    async def respond(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Respond to a prompt with avatar personality.
        Integrates system context and decision criteria.
        """
        # Build full context with avatar personality
        system_context = self.get_system_context()
        full_prompt = f"{system_context}\n\nTask: {prompt}"

        if context:
            full_prompt += f"\n\nContext: {context}"

        # In a real implementation, this would call the agent's LLM
        # For now, return a placeholder indicating the avatar context
        return f"[{self.profile.name}] {full_prompt[:100]}..."

    def get_system_context(self) -> str:
        """Get system prompt for this avatar's style."""
        if self.profile.system_prompt:
            return self.profile.system_prompt

        style_prompts = {
            AvatarStyle.ENGINEER: (
                "You are an Engineer avatar. Prioritize safety, validation, and "
                "adherence to specifications. Prefer conservative decisions and "
                "thorough testing. Question assumptions and ensure all constraints are met."
            ),
            AvatarStyle.DESIGNER: (
                "You are a Designer avatar. Prioritize visual clarity, user experience, "
                "and creative problem-solving. Explore novel approaches and push boundaries "
                "while maintaining aesthetic coherence."
            ),
            AvatarStyle.DRIVER: (
                "You are a Driver avatar. Prioritize engagement, fun, and in-universe "
                "authenticity. Make decisions that are exciting and narratively appropriate. "
                "Balance risk-taking with situational awareness."
            ),
        }

        return style_prompts.get(self.profile.style, "")

    def get_voice_params(self) -> Dict[str, Any]:
        """Get voice configuration for audio/speech interface."""
        defaults = {
            "pitch": 1.0,
            "speed": 1.0,
            "tone": "neutral",
        }

        # Merge with profile config
        voice_params = {**defaults, **self.profile.voice_config}

        # Adjust for style
        style_adjustments = {
            AvatarStyle.ENGINEER: {"pitch": 0.95, "tone": "analytical"},
            AvatarStyle.DESIGNER: {"pitch": 1.05, "tone": "enthusiastic"},
            AvatarStyle.DRIVER: {"pitch": 1.0, "tone": "energetic"},
        }

        style_adj = style_adjustments.get(self.profile.style, {})
        return {**voice_params, **style_adj}

    def get_ui_params(self) -> Dict[str, Any]:
        """Get UI configuration (colors, icons, layout hints)."""
        defaults = {
            "color_primary": "#666666",
            "color_secondary": "#999999",
            "icon": "⚙️",
            "theme": "default",
        }

        # Merge with profile config
        ui_params = {**defaults, **self.profile.ui_config}

        # Adjust for style
        style_colors = {
            AvatarStyle.ENGINEER: {
                "color_primary": "#0066cc",
                "color_secondary": "#003366",
                "icon": "⚙️",
                "theme": "technical",
            },
            AvatarStyle.DESIGNER: {
                "color_primary": "#ff6600",
                "color_secondary": "#ff3300",
                "icon": "🎨",
                "theme": "creative",
            },
            AvatarStyle.DRIVER: {
                "color_primary": "#ff0000",
                "color_secondary": "#dd0000",
                "icon": "🏎️",
                "theme": "action",
            },
        }

        style_ui = style_colors.get(self.profile.style, {})
        return {**ui_params, **style_ui}

    def __repr__(self) -> str:
        return (
            f"<Avatar name={self.profile.name} style={self.profile.style} "
            f"bound_to={self.profile.bound_agent}>"
        )

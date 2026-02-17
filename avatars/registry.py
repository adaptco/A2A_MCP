<<<<<<< HEAD
"""Avatar registry for managing agent-avatar bindings."""

from typing import Dict, Optional, List
=======
"""Avatar registry and factory."""

from typing import Dict, Optional
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe
from avatars.avatar import Avatar, AvatarProfile, AvatarStyle


class AvatarRegistry:
<<<<<<< HEAD
    """
    Central registry for avatar-agent bindings.
    Singleton pattern provides global access.
    """

    _instance: Optional["AvatarRegistry"] = None
    _avatars: Dict[str, Avatar] = {}
    _agent_bindings: Dict[str, str] = {}  # agent_name -> avatar_id

    def __new__(cls) -> "AvatarRegistry":
        """Ensure singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register_avatar(self, profile: AvatarProfile) -> Avatar:
        """Register a new avatar and optionally bind to an agent."""
        avatar = Avatar(profile)
        self._avatars[profile.avatar_id] = avatar

        if profile.bound_agent:
            self._agent_bindings[profile.bound_agent] = profile.avatar_id

        return avatar

    def get_avatar(self, avatar_id: str) -> Optional[Avatar]:
        """Get avatar by ID."""
        return self._avatars.get(avatar_id)

    def get_avatar_for_agent(self, agent_name: str) -> Optional[Avatar]:
        """Get avatar bound to a specific agent."""
        avatar_id = self._agent_bindings.get(agent_name)
        if avatar_id:
            return self._avatars.get(avatar_id)
        return None

    def bind_agent_to_avatar(self, agent_name: str, avatar_id: str) -> None:
        """Bind an agent to an avatar."""
        if avatar_id not in self._avatars:
            raise ValueError(f"Avatar {avatar_id} not found")
        self._agent_bindings[agent_name] = avatar_id

    def list_avatars(self) -> List[Avatar]:
        """Get all registered avatars."""
        return list(self._avatars.values())

    def list_bindings(self) -> Dict[str, str]:
        """Get all agent-avatar bindings."""
        return self._agent_bindings.copy()

    def clear(self) -> None:
        """Clear all avatars and bindings (for testing)."""
        self._avatars.clear()
        self._agent_bindings.clear()

    def __repr__(self) -> str:
        return (
            f"<AvatarRegistry avatars={len(self._avatars)} "
            f"bindings={len(self._agent_bindings)}>"
        )


def get_avatar_registry() -> AvatarRegistry:
    """Access the global avatar registry singleton."""
    return AvatarRegistry()
=======
    """Centralized registry for avatar profiles."""

    def __init__(self):
        self._avatars: Dict[str, Avatar] = {}
        self._profiles: Dict[str, AvatarProfile] = {}
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Initialize default avatar profiles."""
        profiles = {
            "engineer": AvatarProfile(
                avatar_id="avatar-engineer-001",
                name="Engineer",
                style=AvatarStyle.ENGINEER,
                bound_agent="ArchitectureAgent",
                system_prompt=(
                    "You are an engineer avatar. Be precise, logical, and safety-conscious. "
                    "Focus on specs, constraints, and failure modes. Minimize ambiguity."
                ),
                ui_config={
                    "color": "#2E86DE",
                    "icon": "⚙️",
                    "theme": "dark-mono"
                }
            ),
            "designer": AvatarProfile(
                avatar_id="avatar-designer-001",
                name="Designer",
                style=AvatarStyle.DESIGNER,
                bound_agent="ArchitectureAgent",
                system_prompt=(
                    "You are a designer avatar. Be visual, creative, and metaphor-friendly. "
                    "Focus on aesthetics, UX, and narrative coherence."
                ),
                ui_config={
                    "color": "#A29BFE",
                    "icon": "🎨",
                    "theme": "gradient"
                }
            ),
            "driver": AvatarProfile(
                avatar_id="avatar-driver-001",
                name="Driver",
                style=AvatarStyle.DRIVER,
                bound_agent="CoderAgent",
                system_prompt=(
                    "You are a driver avatar. Be conversational, game-aware, and responsive. "
                    "Understand in-universe context and player intent. Keep tone engaging."
                ),
                ui_config={
                    "color": "#FF6348",
                    "icon": "🏁",
                    "theme": "neon"
                }
            )
        }

        for key, profile in profiles.items():
            self._profiles[key] = profile
            self._avatars[key] = Avatar(profile)

    def get_avatar(self, avatar_key: str) -> Optional[Avatar]:
        """Retrieve an avatar by key."""
        return self._avatars.get(avatar_key)

    def get_profile(self, avatar_key: str) -> Optional[AvatarProfile]:
        """Retrieve an avatar profile by key."""
        return self._profiles.get(avatar_key)

    def register_avatar(self, key: str, profile: AvatarProfile) -> Avatar:
        """Register a new avatar profile."""
        avatar = Avatar(profile)
        self._avatars[key] = avatar
        self._profiles[key] = profile
        return avatar

    def list_avatars(self) -> Dict[str, Avatar]:
        """Return all registered avatars."""
        return dict(self._avatars)

    def get_avatar_for_agent(self, agent_name: str) -> Optional[Avatar]:
        """Retrieve avatar bound to a given agent name."""
        for avatar in self._avatars.values():
            if avatar.profile.bound_agent == agent_name:
                return avatar
        return None

    def clear(self) -> None:
        """Clear registry state; useful for tests."""
        self._avatars.clear()
        self._profiles.clear()

    def __repr__(self) -> str:
        return f"<AvatarRegistry avatars={list(self._avatars.keys())}>"


# Global singleton registry
_global_registry = AvatarRegistry()


def get_registry() -> AvatarRegistry:
    """Access the global avatar registry."""
    return _global_registry


def get_avatar_registry() -> AvatarRegistry:
    """Compatibility alias used by newer avatar integrations."""
    return get_registry()
>>>>>>> cde431b91765a0efa58a544c6bbce7e87c940fbe

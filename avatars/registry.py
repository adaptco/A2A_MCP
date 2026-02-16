"""Avatar registry for managing agent-avatar bindings."""

from typing import Dict, Optional, List
from avatars.avatar import Avatar, AvatarProfile, AvatarStyle


class AvatarRegistry:
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

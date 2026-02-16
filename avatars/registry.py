"""Avatar registry and factory."""

from typing import Dict, Optional
from avatars.avatar import Avatar, AvatarProfile, AvatarStyle


class AvatarRegistry:
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

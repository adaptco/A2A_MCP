"""Setup avatars and bind them to agents."""

from avatars.avatar import AvatarProfile, AvatarStyle
from avatars.registry import get_avatar_registry


def setup_default_avatars() -> None:
    """
    Register default avatars and bind them to the canonical agent pipeline.

    Mapping:
    - ManagingAgent -> Engineer
    - OrchestrationAgent -> Engineer
    - ArchitectureAgent -> Designer
    - CoderAgent -> Engineer
    - TesterAgent -> Engineer
    - ResearcherAgent -> Designer
    - PINNAgent -> Engineer
    """
    registry = get_avatar_registry()

    profiles = [
        (
            "manager",
            AvatarProfile(
                avatar_id="avatar_managing",
                name="Manager",
                style=AvatarStyle.ENGINEER,
                bound_agent="ManagingAgent",
                voice_config={"tone": "authoritative"},
                ui_config={"color_primary": "#0066cc", "icon": "manager"},
            ),
        ),
        (
            "conductor",
            AvatarProfile(
                avatar_id="avatar_orchestration",
                name="Conductor",
                style=AvatarStyle.ENGINEER,
                bound_agent="OrchestrationAgent",
                voice_config={"tone": "methodical"},
                ui_config={"color_primary": "#0066cc", "icon": "conductor"},
            ),
        ),
        (
            "architect",
            AvatarProfile(
                avatar_id="avatar_architecture",
                name="Architect",
                style=AvatarStyle.DESIGNER,
                bound_agent="ArchitectureAgent",
                voice_config={"tone": "creative"},
                ui_config={"color_primary": "#ff6600", "icon": "architect"},
            ),
        ),
        (
            "coder",
            AvatarProfile(
                avatar_id="avatar_coder",
                name="Coder",
                style=AvatarStyle.ENGINEER,
                bound_agent="CoderAgent",
                voice_config={"tone": "technical"},
                ui_config={"color_primary": "#0066cc", "icon": "coder"},
            ),
        ),
        (
            "tester",
            AvatarProfile(
                avatar_id="avatar_tester",
                name="Tester",
                style=AvatarStyle.ENGINEER,
                bound_agent="TesterAgent",
                voice_config={"tone": "critical"},
                ui_config={"color_primary": "#0066cc", "icon": "tester"},
            ),
        ),
        (
            "researcher",
            AvatarProfile(
                avatar_id="avatar_researcher",
                name="Researcher",
                style=AvatarStyle.DESIGNER,
                bound_agent="ResearcherAgent",
                voice_config={"tone": "inquisitive"},
                ui_config={"color_primary": "#ff6600", "icon": "researcher"},
            ),
        ),
        (
            "physicist",
            AvatarProfile(
                avatar_id="avatar_pinn",
                name="Physicist",
                style=AvatarStyle.ENGINEER,
                bound_agent="PINNAgent",
                voice_config={"tone": "analytical"},
                ui_config={"color_primary": "#0066cc", "icon": "physicist"},
            ),
        ),
    ]

    for key, profile in profiles:
        registry.register_avatar(key, profile)


def reset_avatars() -> None:
    """Clear avatar registry state (for tests that need isolation)."""
    registry = get_avatar_registry()
    registry.clear()

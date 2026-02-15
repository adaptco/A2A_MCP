"""Setup avatars and bind them to agents."""

from avatars.avatar import AvatarProfile, AvatarStyle
from avatars.registry import get_avatar_registry


def setup_default_avatars() -> None:
    """
    Register default avatars and bind them to the canonical agent pipeline.
    
    Mapping:
    - ManagingAgent -> Engineer (safety-first, oversight)
    - OrchestrationAgent -> Engineer (planning, specification)
    - ArchitectureAgent -> Designer (creative solutions, system design)
    - CoderAgent -> Engineer (correctness, implementation)
    - TesterAgent -> Engineer (validation, coverage)
    - ResearcherAgent -> Designer (exploration, discovery)
    - PINNAgent -> Engineer (constraint adherence, physics)
    """
    registry = get_avatar_registry()

    # Engineer avatars (safety, spec adherence, validation)
    managing_profile = AvatarProfile(
        avatar_id="avatar_managing",
        name="Manager",
        style=AvatarStyle.ENGINEER,
        bound_agent="ManagingAgent",
        description="Oversees agent coordination and execution flow",
        voice_config={"tone": "authoritative"},
        ui_config={"color_primary": "#0066cc", "icon": "👔"},
    )
    registry.register_avatar(managing_profile)

    orchestration_profile = AvatarProfile(
        avatar_id="avatar_orchestration",
        name="Conductor",
        style=AvatarStyle.ENGINEER,
        bound_agent="OrchestrationAgent",
        description="Directs execution blueprint and delegates to agents",
        voice_config={"tone": "methodical"},
        ui_config={"color_primary": "#0066cc", "icon": "🎼"},
    )
    registry.register_avatar(orchestration_profile)

    # Designer avatar (architecture, creativity)
    architecture_profile = AvatarProfile(
        avatar_id="avatar_architecture",
        name="Architect",
        style=AvatarStyle.DESIGNER,
        bound_agent="ArchitectureAgent",
        description="Designs system structure and integration patterns",
        voice_config={"tone": "creative"},
        ui_config={"color_primary": "#ff6600", "icon": "🏗️"},
    )
    registry.register_avatar(architecture_profile)

    # Coder engineer (implementation correctness)
    coder_profile = AvatarProfile(
        avatar_id="avatar_coder",
        name="Coder",
        style=AvatarStyle.ENGINEER,
        bound_agent="CoderAgent",
        description="Implements solutions with correctness and clarity",
        voice_config={"tone": "technical"},
        ui_config={"color_primary": "#0066cc", "icon": "💻"},
    )
    registry.register_avatar(coder_profile)

    # Tester engineer (validation)
    tester_profile = AvatarProfile(
        avatar_id="avatar_tester",
        name="Tester",
        style=AvatarStyle.ENGINEER,
        bound_agent="TesterAgent",
        description="Validates implementations and ensures quality",
        voice_config={"tone": "critical"},
        ui_config={"color_primary": "#0066cc", "icon": "✓"},
    )
    registry.register_avatar(tester_profile)

    # Researcher designer (exploration)
    researcher_profile = AvatarProfile(
        avatar_id="avatar_researcher",
        name="Researcher",
        style=AvatarStyle.DESIGNER,
        bound_agent="ResearcherAgent",
        description="Explores solutions and investigates alternatives",
        voice_config={"tone": "inquisitive"},
        ui_config={"color_primary": "#ff6600", "icon": "🔬"},
    )
    registry.register_avatar(researcher_profile)

    # PINN agent engineer (physics constraints)
    pinn_profile = AvatarProfile(
        avatar_id="avatar_pinn",
        name="Physicist",
        style=AvatarStyle.ENGINEER,
        bound_agent="PINNAgent",
        description="Ensures physics and constraint adherence",
        voice_config={"tone": "analytical"},
        ui_config={"color_primary": "#0066cc", "icon": "⚛️"},
    )
    registry.register_avatar(pinn_profile)


def reset_avatars() -> None:
    """Clear avatar registry state (for tests that need isolation)."""
    registry = get_avatar_registry()
    registry.clear()

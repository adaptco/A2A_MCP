"""Test avatar-agent bindings and Judge integration (Part E)."""

import sys
sys.path.insert(0, ".")

from avatars.avatar import AvatarProfile, AvatarStyle, Avatar
from avatars.registry import get_avatar_registry
from avatars.setup import setup_default_avatars, reset_avatars
from orchestrator.judge_orchestrator import get_judge_orchestrator
from judge.decision import JudgmentModel


def test_avatar_profiles():
    """Test avatar creation and personality profiles."""
    print("\n=== Test 1: Avatar Profiles ===")

    engineer = AvatarProfile(
        avatar_id="test_engineer",
        name="Test Engineer",
        style=AvatarStyle.ENGINEER,
        bound_agent="CoderAgent",
        description="Safety-first coder",
    )
    avatar = Avatar(engineer)

    print(f"Avatar: {avatar}")
    print(f"System Context:\n{avatar.get_system_context()[:100]}...")
    print(f"Voice Params: {avatar.get_voice_params()}")
    print(f"UI Params: {avatar.get_ui_params()}")

    assert avatar.profile.style == AvatarStyle.ENGINEER
    assert "Engineer" in avatar.get_system_context()
    print("[OK] Avatar profiles work")


def test_avatar_registry():
    """Test avatar registry and agent bindings."""
    print("\n=== Test 2: Avatar Registry ===")

    reset_avatars()
    registry = get_avatar_registry()

    # Create and register avatars
    profile1 = AvatarProfile(
        avatar_id="avatar_test_1",
        name="Test Avatar 1",
        style=AvatarStyle.DESIGNER,
        bound_agent="ArchitectureAgent",
    )
    registry.register_avatar(profile1)

    profile2 = AvatarProfile(
        avatar_id="avatar_test_2",
        name="Test Avatar 2",
        style=AvatarStyle.ENGINEER,
        bound_agent="CoderAgent",
    )
    registry.register_avatar(profile2)

    # Test retrieval
    avatar1 = registry.get_avatar("avatar_test_1")
    avatar2 = registry.get_avatar_for_agent("ArchitectureAgent")

    assert avatar1 is not None
    assert avatar2 is not None
    assert avatar2.profile.name == "Test Avatar 1"

    bindings = registry.list_bindings()
    assert len(bindings) == 2
    print(f"Bindings: {bindings}")
    print("[OK] Avatar registry works")


def test_default_avatars_setup():
    """Test default avatar setup and canonical agent bindings."""
    print("\n=== Test 3: Default Avatars Setup ===")

    reset_avatars()
    registry = get_avatar_registry()

    # Setup default avatars
    setup_default_avatars()

    avatars = registry.list_avatars()
    bindings = registry.list_bindings()

    print(f"Registered {len(avatars)} avatars")
    print(f"Bindings: {len(bindings)}")

    expected_agents = [
        "ManagingAgent",
        "OrchestrationAgent",
        "ArchitectureAgent",
        "CoderAgent",
        "TesterAgent",
        "ResearcherAgent",
        "PINNAgent",
    ]

    for agent_name in expected_agents:
        avatar = registry.get_avatar_for_agent(agent_name)
        assert avatar is not None, f"Missing avatar for {agent_name}"
        print(f"  {agent_name:20} -> {avatar.profile.name:12} ({avatar.profile.style.value})")

    print("[OK] Default avatars setup works")


def test_judge_with_avatars():
    """Test Judge integration with avatars."""
    print("\n=== Test 4: Judge with Avatars ===")

    # Get Judge with specs-loaded criteria
    judge = JudgmentModel(preset="simulation")

    # Test Judge can load criteria
    criteria = judge._criteria
    print(f"Judge loaded {len(criteria)} criteria:")
    for crit_type, criterion in criteria.items():
        print(f"  {crit_type.value:15} weight={criterion.weight:.1f}")

    # Test action scoring
    context = {
        "speed_mph": 50,
        "max_speed_mph": 155,
        "nearest_obstacle_distance_m": 100,
        "fuel_remaining_gal": 10,
        "lateral_g_force": 0.3,
    }

    actions = [
        "accelerate to 60 mph",
        "maintain current speed",
        "brake to 30 mph",
    ]

    scores = judge.judge_actions(actions, context)

    print(f"\nAction scores:")
    for score in scores:
        print(f"  {score.action:30} -> {score.overall_score:.3f}")

    assert len(scores) == 3
    print("[OK] Judge with avatars works")


def test_judge_orchestrator_integration():
    """Test full JudgeOrchestrator integration."""
    print("\n=== Test 5: JudgeOrchestrator Integration ===")

    orchestrator = get_judge_orchestrator(preset="simulation")

    # Check avatars are loaded
    avatars = orchestrator.list_avatars()
    print(f"JudgeOrchestrator initialized with {len(avatars)} avatars")

    # Get avatar for agent
    coder_avatar = orchestrator.get_avatar_for_agent("CoderAgent")
    print(f"CoderAgent avatar: {coder_avatar.profile.name}")

    # Get system context for agent
    system_context = orchestrator.get_agent_system_context("CoderAgent")
    print(f"CoderAgent system context: {system_context[:80]}...")

    # Judge an action
    context = {
        "speed_mph": 45,
        "max_speed_mph": 155,
        "fuel_remaining_gal": 8,
        "lateral_g_force": 0.2,
    }

    score = orchestrator.judge_action("implement feature with tests", context, "CoderAgent")
    print(f"Action score: {score.overall_score:.3f}")

    print("[OK] JudgeOrchestrator integration works")


def test_avatar_response_with_context():
    """Test avatar responding with system context."""
    print("\n=== Test 6: Avatar Response with Context ===")

    reset_avatars()
    registry = get_avatar_registry()

    engineer = AvatarProfile(
        avatar_id="test_engineer_response",
        name="Engineer Avatar",
        style=AvatarStyle.ENGINEER,
        bound_agent="CoderAgent",
        description="Safety-first implementation",
    )
    registry.register_avatar(engineer)

    avatar = registry.get_avatar("test_engineer_response")

    context = {
        "task": "implement login function",
        "safety_level": "critical",
    }

    import asyncio
    response = asyncio.run(avatar.respond("Write a login function", context))
    print(f"Avatar response: {response[:100]}...")

    print("[OK] Avatar response with context works")


if __name__ == "__main__":
    print("=" * 60)
    print("Testing Avatar-Agent Binding (Part E)")
    print("=" * 60)

    test_avatar_profiles()
    test_avatar_registry()
    test_default_avatars_setup()
    test_judge_with_avatars()
    test_judge_orchestrator_integration()
    test_avatar_response_with_context()

    print("\n" + "=" * 60)
    print("[OK] All Part E integration tests passed!")
    print("=" * 60)

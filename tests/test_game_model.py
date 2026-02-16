"""Tests for typed game model contract and integration boundaries."""

from schemas.game_model import (
    AgentRuntimeState,
    GameActionResult,
    GameModel,
    OwnerSystem,
    ZoneSpec,
)


def test_game_model_ownership_boundaries_present():
    model = GameModel()
    by_domain = {item.domain: item for item in model.ownership}

    assert by_domain["agent_runtime_state"].owner == OwnerSystem.CORE_ORCHESTRATOR
    assert by_domain["world_specifications"].owner == OwnerSystem.SSOT
    assert by_domain["physics_ground_truth"].owner == OwnerSystem.GROUND


def test_game_model_zone_registration_and_state_updates():
    model = GameModel(preset="simulation")
    model.register_zone(
        ZoneSpec(
            zone_id="zone_1",
            name="Downtown",
            speed_limit_mph=35,
            obstacle_density=0.2,
            difficulty_rating=2,
        )
    )

    model.upsert_agent_state(
        AgentRuntimeState(
            agent_name="CoderAgent",
            x=10.0,
            y=0.0,
            z=20.0,
            speed_mph=15.0,
            heading_deg=90.0,
            fuel_gal=12.0,
            current_zone="zone_1",
        )
    )
    model.apply_action_result(
        GameActionResult(
            agent_name="CoderAgent",
            action="accelerate to 25 mph",
            score=0.81,
            zone="zone_1",
            speed_mph=25.0,
            fuel_gal=11.8,
        )
    )

    state = model.agent_states["CoderAgent"]
    assert model.zones["zone_1"].name == "Downtown"
    assert state.last_action == "accelerate to 25 mph"
    assert state.last_judge_score == 0.81
    assert state.speed_mph == 25.0


def test_game_model_snapshots_are_recorded():
    model = GameModel()
    model.upsert_agent_state(
        AgentRuntimeState(agent_name="TesterAgent", x=0.0, y=0.0, z=0.0)
    )

    first = model.snapshot(frame=1)
    second = model.snapshot(frame=2)

    assert first.frame == 1
    assert second.frame == 2
    assert len(model.history) == 2

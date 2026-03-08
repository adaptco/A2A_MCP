from __future__ import annotations

from agent_style_entropy import build_style_temperature_plan, uniform_dotproduct
from world_foundation_model import build_world_foundation_model


def test_uniform_dotproduct_is_bounded() -> None:
    score = uniform_dotproduct([1.0, 0.0, 1.0], [1.0, 1.0, 0.0])
    assert -1.0 <= score <= 1.0


def test_style_temperature_plan_is_deterministic() -> None:
    first = build_style_temperature_plan(
        prompt="Implement backend API and frontend status view",
        risk_profile="high",
        changed_path_count=17,
    )
    second = build_style_temperature_plan(
        prompt="Implement backend API and frontend status view",
        risk_profile="high",
        changed_path_count=17,
    )

    assert first == second
    assert 0.15 <= first["temperature"] <= 0.85
    assert first["selected_template"] in {"frontend", "backend", "fullstack"}
    assert first["api_skill_tokens"]


def test_world_foundation_model_exposes_style_and_skill_tokens() -> None:
    block = build_world_foundation_model(
        prompt="Patch merge conflicts and stabilize orchestrator API",
        repository="adaptco/A2A_MCP",
        commit_sha="abc123",
        actor="tester",
        cluster_count=4,
        risk_profile="medium",
    )

    infra = block["infrastructure_agent"]
    assert "style_temperature_profile" in infra
    assert "template_route" in infra
    assert "api_skill_tokens" in infra
    assert infra["template_route"]["selected_actions"]

from __future__ import annotations

import json
from pathlib import Path

from a2a_mcp.blackmamba.planner import AgentBlackMamba


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_anchor(path: Path, payload: dict) -> None:
    path.write_text(f"# Anchor\n\n```json\n{json.dumps(payload, indent=2)}\n```\n", encoding="utf-8")


def test_agent_blackmamba_estimates_task_from_xml(tmp_path: Path) -> None:
    temp_repo = tmp_path / "repo"
    (temp_repo / "specs").mkdir(parents=True)
    (temp_repo / "specs" / "enterprise_agent_map.xml").write_text(
        (REPO_ROOT / "specs" / "enterprise_agent_map.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    root_memory = tmp_path / "root"
    root_memory.mkdir()
    _write_anchor(
        root_memory / "AGENTS.md",
        {
            "workspace_preferences": {"working_style": {"tone": "planner"}},
            "agent_overrides": {},
            "milestones": [],
            "token_budget": {},
        },
    )
    _write_anchor(root_memory / "Skills.md", {"shared_skills": ["playwright"], "integration_nodes": []})

    planner = AgentBlackMamba(
        repo_root=temp_repo,
        root_path=root_memory,
        enterprise_map_path=temp_repo / "specs" / "enterprise_agent_map.xml",
    )
    estimate = planner.estimate_task(
        objective="Estimate the next release checkpoint",
        complexity=0.67,
        risk=0.73,
        interfaces=["frontier-registry", "github-actions-control", "antigravity-hitl"],
        dependencies=["enterprise_agent_map.xml"],
    )

    assert estimate.predicted_tokens > 0
    assert estimate.predicted_minutes > 0
    assert estimate.predicted_cost_usd > 0
    assert any(stage.agent_id == "agent:blackmamba" for stage in estimate.stage_budgets)
    assert any(checkpoint["id"] == "release-review" for checkpoint in estimate.approval_checkpoints)

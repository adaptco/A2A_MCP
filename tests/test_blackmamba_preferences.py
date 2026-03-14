from __future__ import annotations

import json
from pathlib import Path

from a2a_mcp.blackmamba.preferences import load_workspace_preferences


def _write_markdown_json(path: Path, payload: dict) -> None:
    path.write_text(f"# Memory\n\n```json\n{json.dumps(payload, indent=2)}\n```\n", encoding="utf-8")


def test_load_workspace_preferences_uses_explicit_root_files(tmp_path: Path) -> None:
    agents_payload = {
        "workspace_preferences": {
            "working_style": {
                "tone": "surgical",
                "token_management": "tight_budget",
            }
        },
        "agent_overrides": {"agent:blackmamba": {"enterprise_role": "timekeeper"}},
        "milestones": [{"id": "MX", "name": "Test milestone"}],
        "token_budget": {"loop_1": {"tokens": [1, 2], "business_days": [3, 4]}},
    }
    skills_payload = {
        "shared_skills": ["moa-cli-coding-fabric", "playwright"],
        "integration_nodes": ["frontier-registry", "antigravity-hitl"],
    }
    _write_markdown_json(tmp_path / "AGENTS.md", agents_payload)
    _write_markdown_json(tmp_path / "Skills.md", skills_payload)

    bundle = load_workspace_preferences(root_path=tmp_path)

    assert bundle.working_style["tone"] == "surgical"
    assert bundle.working_style["token_management"] == "tight_budget"
    assert bundle.shared_skills == ["moa-cli-coding-fabric", "playwright"]
    assert bundle.integration_nodes == ["frontier-registry", "antigravity-hitl"]
    assert bundle.memory_sources[0].exists is True
    assert bundle.memory_sources[1].exists is True


def test_load_workspace_preferences_falls_back_to_user_profile(tmp_path: Path, monkeypatch) -> None:
    home_dir = tmp_path / "home"
    home_dir.mkdir()
    _write_markdown_json(
        home_dir / "AGENTS.md",
        {
            "workspace_preferences": {"working_style": {"tone": "fallback"}},
            "agent_overrides": {},
            "milestones": [],
            "token_budget": {},
        },
    )
    _write_markdown_json(
        home_dir / "Skills.md",
        {
            "shared_skills": ["linear"],
            "integration_nodes": ["github-actions-control"],
        },
    )
    monkeypatch.setenv("USERPROFILE", str(home_dir))

    bundle = load_workspace_preferences(root_path=tmp_path / "missing-root")

    assert bundle.working_style["tone"] == "fallback"
    assert bundle.shared_skills == ["linear"]
    assert bundle.memory_sources[0].path.endswith("AGENTS.md")
    assert bundle.memory_sources[0].exists is True

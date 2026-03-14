from __future__ import annotations

import json
from pathlib import Path

from a2a_mcp.blackmamba.enterprise_map import compile_enterprise_artifacts


REPO_ROOT = Path(__file__).resolve().parents[1]


def _write_anchor(path: Path, payload: dict) -> None:
    path.write_text(f"# Anchor\n\n```json\n{json.dumps(payload, indent=2)}\n```\n", encoding="utf-8")


def test_compile_enterprise_artifacts_generates_runtime_payloads(tmp_path: Path) -> None:
    temp_repo = tmp_path / "repo"
    (temp_repo / "specs").mkdir(parents=True)
    map_path = temp_repo / "specs" / "enterprise_agent_map.xml"
    map_path.write_text(
        (REPO_ROOT / "specs" / "enterprise_agent_map.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    root_memory = tmp_path / "root"
    root_memory.mkdir()
    _write_anchor(
        root_memory / "AGENTS.md",
        {
            "workspace_preferences": {"working_style": {"tone": "deterministic"}},
            "agent_overrides": {},
            "milestones": [],
            "token_budget": {},
        },
    )
    _write_anchor(
        root_memory / "Skills.md",
        {
            "shared_skills": ["moa-cli-coding-fabric"],
            "integration_nodes": ["antigravity-hitl"],
        },
    )

    antigravity_root = tmp_path / "antigravity"
    org_github_root = tmp_path / ".github"
    result = compile_enterprise_artifacts(
        map_path=map_path,
        repo_root=temp_repo,
        root_path=root_memory,
        antigravity_root=antigravity_root,
        org_github_root=org_github_root,
        skip_external_sync=False,
    )

    assert Path(result["generated_paths"]["compiled_map"]).exists()
    compiled_payload = json.loads(Path(result["generated_paths"]["compiled_map"]).read_text(encoding="utf-8"))
    assert compiled_payload["workspace_memory"]["working_style"]["tone"] == "deterministic"
    assert any(card["agent_id"] == "agent:blackmamba" for card in compiled_payload["agent_cards"])
    assert (antigravity_root / "enterprise_extension_node_map.v1.json").exists()
    assert (org_github_root / "codex" / "generated" / "enterprise_extension_node_map.v1.json").exists()

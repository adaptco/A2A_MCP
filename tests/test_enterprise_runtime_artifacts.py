from pathlib import Path

import pytest

from scripts.build_enterprise_runtime_artifacts import parse_enterprise_map


def test_parse_enterprise_map_extracts_core_artifacts() -> None:
    artifacts = parse_enterprise_map(Path("specs/enterprise_agent_map.xml"))

    assert len(artifacts["agent_cards"]["cards"]) >= 2
    assert any(i["name"] == "GitHub" for i in artifacts["integration_registry"]["integrations"])
    assert artifacts["reward_policy_bundle"]["ledger"]["semantic"] == 0.4
    assert any(t["interface"] == "A2A_MCP" for t in artifacts["mcp_topology"]["nodes"])
    assert any(tool["tool_id"] == "ext:antigravity.browser" for tool in artifacts["tool_registry"]["tools"])


def test_parse_enterprise_map_requires_expected_sections(tmp_path: Path) -> None:
    broken = tmp_path / "broken.xml"
    broken.write_text("<enterpriseAgentMap version='1.0'></enterpriseAgentMap>", encoding="utf-8")

    with pytest.raises(ValueError, match="Missing required XML section"):
        parse_enterprise_map(broken)

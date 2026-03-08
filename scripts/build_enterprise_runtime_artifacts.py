#!/usr/bin/env python3
"""Generate runtime JSON artifacts from specs/enterprise_agent_map.xml."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP = REPO_ROOT / "specs" / "enterprise_agent_map.xml"


def _text(node: ET.Element | None, default: str = "") -> str:
    if node is None or node.text is None:
        return default
    return node.text.strip()


def _required(root: ET.Element, query: str) -> ET.Element:
    node = root.find(query)
    if node is None:
        raise ValueError(f"Missing required XML section: {query}")
    return node


def parse_enterprise_map(xml_path: Path) -> dict[str, Any]:
    root = ET.parse(xml_path).getroot()
    if root.tag != "enterpriseAgentMap":
        raise ValueError("Expected <enterpriseAgentMap> root")

    _required(root, "./agentCards")
    _required(root, "./integrations")
    _required(root, "./mcpTopology")

    cards: list[dict[str, Any]] = []
    for agent in root.findall("./agentCards/agent"):
        cards.append(
            {
                "agent_id": agent.get("id", ""),
                "display_name": agent.get("displayName", agent.get("id", "")),
                "role": agent.get("role", "pipeline_operator"),
                "owner": agent.get("owner", "unassigned"),
                "reward_weights": {
                    "semantic": float(agent.get("rewardSemantic", "0.34")),
                    "systems": float(agent.get("rewardSystems", "0.33")),
                    "domain": float(agent.get("rewardDomain", "0.33")),
                },
                "mcp_tool_scope": [n.get("name", "") for n in agent.findall("./toolScope/tool") if n.get("name")],
                "escalation_policy": {
                    "required": agent.get("escalationRequired", "true") == "true",
                    "target": agent.get("escalationTarget", "agent:frontier.anthropic.claude"),
                },
            }
        )

    integrations: list[dict[str, Any]] = []
    for integration in root.findall("./integrations/integration"):
        integrations.append(
            {
                "name": integration.get("name", ""),
                "enabled": integration.get("enabled", "false") == "true",
                "interface": integration.get("interface", ""),
                "node": integration.get("node", ""),
            }
        )

    topology: list[dict[str, str]] = []
    for node in root.findall("./mcpTopology/node"):
        topology.append(
            {
                "id": node.get("id", ""),
                "interface": node.get("interface", ""),
                "plane": node.get("plane", "upper"),
            }
        )

    extensions: list[dict[str, Any]] = []
    for ext in root.findall("./extensions/extension"):
        extensions.append(
            {
                "id": ext.get("id", ""),
                "interface": ext.get("interface", ""),
                "owner": ext.get("owner", ""),
                "checkpoint": ext.get("checkpoint", "manual_approval"),
            }
        )

    tool_registry = {
        "version": "v1",
        "tools": [
            {
                "tool_id": ext["id"],
                "interface": ext["interface"],
                "approval_checkpoint": ext["checkpoint"],
                "owner": ext["owner"],
            }
            for ext in extensions
        ],
    }

    reward_policy = {
        "ledger": {
            "semantic": float(_text(root.find("./rewardLedger/semanticWeight"), "0.4")),
            "systems": float(_text(root.find("./rewardLedger/systemsWeight"), "0.3")),
            "domain": float(_text(root.find("./rewardLedger/domainWeight"), "0.3")),
        },
        "cost_model": {
            "token_unit_cost": float(_text(root.find("./costModel/tokenUnitCost"), "0.000002")),
            "latency_unit_cost": float(_text(root.find("./costModel/latencyUnitCost"), "0.01")),
            "approval_unit_cost": float(_text(root.find("./costModel/approvalUnitCost"), "0.15")),
        },
    }

    return {
        "agent_cards": {"version": "v1", "cards": cards},
        "integration_registry": {"version": "v1", "integrations": integrations},
        "extension_node_map": {"version": "v1", "extensions": extensions},
        "mcp_topology": {"version": "v1", "nodes": topology},
        "tool_registry": tool_registry,
        "reward_policy_bundle": {"version": "v1", **reward_policy},
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate runtime artifacts from enterprise MAP XML")
    parser.add_argument("--map", default=str(DEFAULT_MAP))
    parser.add_argument("--agent-cards-out", default=str(REPO_ROOT / "registry" / "agents" / "enterprise_agent_cards.v1.json"))
    parser.add_argument("--integrations-out", default=str(REPO_ROOT / "registry" / "integrations" / "enterprise_integration_registry.v1.json"))
    parser.add_argument("--extensions-out", default=str(REPO_ROOT / "registry" / "extensions" / "enterprise_extension_node_map.v1.json"))
    parser.add_argument("--topology-out", default=str(REPO_ROOT / "registry" / "topology" / "enterprise_mcp_topology.v1.json"))
    parser.add_argument("--tools-out", default=str(REPO_ROOT / "registry" / "tools" / "enterprise_tool_registry.v1.json"))
    parser.add_argument("--reward-policy-out", default=str(REPO_ROOT / "runtime" / "policies" / "enterprise_reward_policy.v1.json"))
    args = parser.parse_args()

    artifacts = parse_enterprise_map(Path(args.map))
    _write_json(Path(args.agent_cards_out), artifacts["agent_cards"])
    _write_json(Path(args.integrations_out), artifacts["integration_registry"])
    _write_json(Path(args.extensions_out), artifacts["extension_node_map"])
    _write_json(Path(args.topology_out), artifacts["mcp_topology"])
    _write_json(Path(args.tools_out), artifacts["tool_registry"])
    _write_json(Path(args.reward_policy_out), artifacts["reward_policy_bundle"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

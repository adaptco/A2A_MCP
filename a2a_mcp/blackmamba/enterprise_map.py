"""Compile the canonical enterprise XML map into runtime artifacts."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from .preferences import WorkspaceMemoryBundle, load_workspace_preferences


REPO_ROOT = Path(__file__).resolve().parents[2]


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _text(node: ET.Element | None, default: str = "") -> str:
    if node is None or node.text is None:
        return default
    return node.text.strip()


def _attr(node: ET.Element, name: str, default: str = "") -> str:
    return node.attrib.get(name, default).strip()


def _attr_int(node: ET.Element, name: str, default: int = 0) -> int:
    try:
        return int(_attr(node, name, str(default)))
    except ValueError:
        return default


def _attr_float(node: ET.Element, name: str, default: float = 0.0) -> float:
    try:
        return float(_attr(node, name, str(default)))
    except ValueError:
        return default


def _attr_bool(node: ET.Element, name: str, default: bool = False) -> bool:
    value = _attr(node, name, "true" if default else "false").lower()
    return value in {"1", "true", "yes", "on"}


def _child_texts(node: ET.Element, tag: str) -> list[str]:
    return [_text(child) for child in node.findall(tag) if _text(child)]


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def parse_enterprise_agent_map(map_path: str | Path) -> dict[str, Any]:
    """Parse the canonical XML map into a normalized dictionary."""

    map_file = Path(map_path)
    tree = ET.parse(map_file)
    root = tree.getroot()
    if root.tag != "EnterpriseAgentMap":
        raise ValueError(f"Unexpected root tag: {root.tag}")

    workspace_node = root.find("Workspace")
    if workspace_node is None:
        raise ValueError("EnterpriseAgentMap is missing a Workspace node")

    workspace = {
        "root_path": _attr(workspace_node, "rootPath", "C:\\"),
        "memory_path": _attr(workspace_node, "memoryPath", "C:\\AGENTS.md"),
        "skills_path": _attr(workspace_node, "skillsPath", "C:\\Skills.md"),
        "working_style": _attr(workspace_node, "workingStyle", "direct-rigorous-pragmatic"),
        "normalization_ref": _attr(workspace_node, "normalizationRef"),
        "phase_map_ref": _attr(workspace_node, "phaseMapRef"),
        "dmn_ref": _attr(workspace_node, "dmnRef"),
        "preferences": [
            {"key": _attr(pref, "key"), "value": _attr(pref, "value")}
            for pref in workspace_node.findall("Preference")
            if _attr(pref, "key")
        ],
    }

    topology_nodes: list[dict[str, Any]] = []
    for node in root.findall("./MCPTopology/Node"):
        topology_nodes.append(
            {
                "id": _attr(node, "id"),
                "kind": _attr(node, "kind"),
                "interface": _attr(node, "interface"),
                "target": _attr(node, "target", "shared"),
                "approval_mode": _attr(node, "approvalMode", "checkpointed"),
                "capabilities": _child_texts(node, "Capability"),
                "worker_prompt": _text(node.find("WorkerPrompt")),
                "reward_channel": _text(node.find("RewardChannel")),
            }
        )

    extensions: list[dict[str, Any]] = []
    for extension in root.findall("./ExtensionRegistry/Extension"):
        extensions.append(
            {
                "id": _attr(extension, "id"),
                "provider": _attr(extension, "provider"),
                "node_ref": _attr(extension, "nodeRef"),
                "interface": _attr(extension, "interface"),
                "rollout_status": _attr(extension, "rolloutStatus", "staged"),
                "health_state": _attr(extension, "healthState", "unknown"),
                "owning_agent_role": _attr(extension, "owningAgentRole"),
                "webhook_endpoint": _attr(extension, "webhookEndpoint"),
                "scopes": _child_texts(extension, "Scope"),
                "env_vars": _child_texts(extension, "Env"),
                "worker_prompt": _text(extension.find("WorkerPrompt")),
            }
        )

    reward_profiles: list[dict[str, Any]] = []
    for profile in root.findall("./RewardLedger/Profile"):
        dimensions = []
        for dimension in profile.findall("Dimension"):
            dimensions.append(
                {
                    "name": _attr(dimension, "name"),
                    "weight": _attr_float(dimension, "weight", 0.0),
                }
            )
        reward_profiles.append(
            {
                "id": _attr(profile, "id"),
                "purpose": _attr(profile, "purpose"),
                "dimensions": dimensions,
                "acceptance_threshold": _attr_float(profile, "acceptanceThreshold", 0.7),
            }
        )

    agent_cards: list[dict[str, Any]] = []
    for agent in root.findall("./AgentCards/AgentCard"):
        reward_weights = agent.find("RewardWeights")
        escalation = agent.find("EscalationPolicy")
        ownership = agent.find("Ownership")
        budget_defaults = agent.find("BudgetDefaults")
        agent_cards.append(
            {
                "agent_id": _attr(agent, "agentId"),
                "display_name": _attr(agent, "displayName"),
                "provider": _attr(agent, "provider"),
                "model_family": _attr(agent, "modelFamily"),
                "default_model": _attr(agent, "defaultModel"),
                "enterprise_role": _attr(agent, "enterpriseRole"),
                "reward_profile": _attr(agent, "rewardProfile"),
                "approval_mode": _attr(agent, "approvalMode", "checkpointed"),
                "role_summary": _text(agent.find("RoleSummary")),
                "tool_scope": _child_texts(agent, "Tool"),
                "topology_node_refs": _child_texts(agent, "TopologyNodeRef"),
                "worker_prompt": _text(agent.find("WorkerPrompt")),
                "reward_weights": {
                    "semantic": _attr_float(reward_weights, "semantic", 0.0)
                    if reward_weights is not None
                    else 0.0,
                    "systems": _attr_float(reward_weights, "systems", 0.0)
                    if reward_weights is not None
                    else 0.0,
                    "domain": _attr_float(reward_weights, "domain", 0.0)
                    if reward_weights is not None
                    else 0.0,
                },
                "escalation_policy": {
                    "on_risk": _attr(escalation, "onRisk"),
                    "on_architecture": _attr(escalation, "onArchitecture"),
                    "on_recovery": _attr(escalation, "onRecovery"),
                }
                if escalation is not None
                else {},
                "ownership": {
                    "enterprise_function": _attr(ownership, "enterpriseFunction"),
                    "owner": _attr(ownership, "owner"),
                }
                if ownership is not None
                else {},
                "budget_defaults": {
                    "minutes": _attr_int(budget_defaults, "minutes", 0),
                    "tokens": _attr_int(budget_defaults, "tokens", 0),
                    "cost_usd": _attr_float(budget_defaults, "costUsd", 0.0),
                }
                if budget_defaults is not None
                else {},
            }
        )

    orchestration_routes = []
    for route in root.findall("./OrchestrationPlane/Route"):
        orchestration_routes.append(
            {
                "id": _attr(route, "id"),
                "from": _attr(route, "from"),
                "to": _attr(route, "to"),
                "condition": _attr(route, "condition"),
                "description": _text(route.find("Description")),
            }
        )

    pinn_constraints = []
    for constraint in root.findall("./PinnPlane/Constraint"):
        pinn_constraints.append(
            {
                "id": _attr(constraint, "id"),
                "type": _attr(constraint, "type"),
                "expression": _attr(constraint, "expression"),
                "description": _text(constraint.find("Description")),
            }
        )

    embeddings = []
    for cluster in root.findall("./Embeddings/Cluster"):
        embeddings.append(
            {
                "id": _attr(cluster, "id"),
                "strategy": _attr(cluster, "strategy"),
                "tokenization": _attr(cluster, "tokenization"),
                "hints": [
                    {"key": _attr(hint, "key"), "value": _attr(hint, "value")}
                    for hint in cluster.findall("Hint")
                ],
            }
        )

    hitl_checkpoints = []
    for checkpoint in root.findall("./HITL/Checkpoint"):
        hitl_checkpoints.append(
            {
                "id": _attr(checkpoint, "id"),
                "stage": _attr(checkpoint, "stage"),
                "required": _attr_bool(checkpoint, "required", True),
                "viewer": _attr(checkpoint, "viewer", "browser"),
                "description": _text(checkpoint.find("Description")),
            }
        )

    economics_model = root.find("./Economics/Model")
    if economics_model is None:
        raise ValueError("EnterpriseAgentMap is missing Economics/Model")

    economics = {
        "id": _attr(economics_model, "id"),
        "currency": _attr(root.find("./Economics"), "currency", "USD"),
        "base_tokens": _attr_int(economics_model, "baseTokens", 48000),
        "base_minutes": _attr_float(economics_model, "baseMinutes", 42.0),
        "base_token_rate": _attr_float(economics_model, "baseTokenRate", 0.000035),
        "base_minute_rate": _attr_float(economics_model, "baseMinuteRate", 0.42),
        "approval_penalty_minutes": _attr_float(economics_model, "approvalPenaltyMinutes", 3.0),
        "risk_multiplier": _attr_float(economics_model, "riskMultiplier", 0.65),
        "interface_multiplier": _attr_float(economics_model, "interfaceMultiplier", 0.12),
        "dependency_multiplier": _attr_float(economics_model, "dependencyMultiplier", 0.07),
        "checkpoint_penalty_tokens": _attr_int(economics_model, "checkpointPenaltyTokens", 1200),
    }

    milestones = []
    for milestone in root.findall("./Milestones/Milestone"):
        milestones.append(
            {
                "id": _attr(milestone, "id"),
                "name": _attr(milestone, "name"),
                "duration_business_days": [
                    _attr_int(milestone, "durationMinDays", 0),
                    _attr_int(milestone, "durationMaxDays", 0),
                ],
                "token_budget": [
                    _attr_int(milestone, "tokensMin", 0),
                    _attr_int(milestone, "tokensMax", 0),
                ],
                "output": _text(milestone.find("Output")),
            }
        )

    return {
        "version": _attr(root, "version", "1.0"),
        "map_id": _attr(root, "mapId", map_file.stem),
        "workspace": workspace,
        "topology_nodes": topology_nodes,
        "extensions": extensions,
        "agent_cards": agent_cards,
        "reward_profiles": reward_profiles,
        "orchestration_routes": orchestration_routes,
        "pinn_constraints": pinn_constraints,
        "embeddings": embeddings,
        "hitl_checkpoints": hitl_checkpoints,
        "economics": economics,
        "milestones": milestones,
    }


def _integration_registry_payload(parsed_map: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": "v1",
        "generated_at": _iso_now(),
        "integrations": parsed_map["extensions"],
    }


def _reward_policy_payload(parsed_map: dict[str, Any]) -> dict[str, Any]:
    return {
        "version": "v1",
        "generated_at": _iso_now(),
        "profiles": parsed_map["reward_profiles"],
    }


def _extension_map_payload(parsed_map: dict[str, Any], target: str) -> dict[str, Any]:
    nodes = [
        node
        for node in parsed_map["topology_nodes"]
        if node["target"] in {"shared", target}
    ]
    node_ids = {node["id"] for node in nodes}
    extensions = [extension for extension in parsed_map["extensions"] if extension["node_ref"] in node_ids]
    return {
        "version": "v1",
        "generated_at": _iso_now(),
        "target": target,
        "nodes": nodes,
        "extensions": extensions,
    }


def _enrich_agent_cards(
    parsed_map: dict[str, Any],
    memory: WorkspaceMemoryBundle,
) -> list[dict[str, Any]]:
    topology_lookup = {node["id"]: node for node in parsed_map["topology_nodes"]}
    by_node: dict[str, list[dict[str, Any]]] = {}
    for extension in parsed_map["extensions"]:
        by_node.setdefault(extension["node_ref"], []).append(extension)

    enriched_cards = []
    for card in parsed_map["agent_cards"]:
        override = memory.agent_overrides.get(card["agent_id"], {})
        working_style = {
            **memory.working_style,
            **override.get("working_style", {}),
        }
        integration_scopes: list[str] = []
        interface_bindings = []
        for node_ref in card["topology_node_refs"]:
            interface_bindings.append(topology_lookup.get(node_ref, {}))
            for extension in by_node.get(node_ref, []):
                integration_scopes.extend(extension["scopes"])

        enriched_cards.append(
            {
                **card,
                "working_style": working_style,
                "memory_sources": memory.to_dict()["memory_sources"],
                "shared_skills": memory.shared_skills,
                "integration_scopes": sorted(dict.fromkeys(integration_scopes)),
                "interface_bindings": [binding for binding in interface_bindings if binding],
            }
        )
    return enriched_cards


def compile_enterprise_artifacts(
    map_path: str | Path | None = None,
    *,
    repo_root: str | Path | None = None,
    root_path: str | Path = "C:\\",
    agents_memory_path: str | Path | None = None,
    skills_memory_path: str | Path | None = None,
    antigravity_root: str | Path | None = None,
    org_github_root: str | Path | None = None,
    skip_external_sync: bool = False,
) -> dict[str, Any]:
    """Compile XML-authored runtime artifacts and sync target maps."""

    repo = Path(repo_root) if repo_root else REPO_ROOT
    xml_map_path = Path(map_path) if map_path else repo / "specs" / "enterprise_agent_map.xml"
    memory = load_workspace_preferences(
        root_path=root_path,
        agents_path=agents_memory_path,
        skills_path=skills_memory_path,
    )
    parsed_map = parse_enterprise_agent_map(xml_map_path)
    enriched_cards = _enrich_agent_cards(parsed_map, memory)

    compiled_map = {
        "version": "v1",
        "generated_at": _iso_now(),
        "map_id": parsed_map["map_id"],
        "workspace": parsed_map["workspace"],
        "workspace_memory": memory.to_dict(),
        "topology_nodes": parsed_map["topology_nodes"],
        "extensions": parsed_map["extensions"],
        "agent_cards": enriched_cards,
        "reward_profiles": parsed_map["reward_profiles"],
        "orchestration_routes": parsed_map["orchestration_routes"],
        "pinn_constraints": parsed_map["pinn_constraints"],
        "embeddings": parsed_map["embeddings"],
        "hitl_checkpoints": parsed_map["hitl_checkpoints"],
        "economics": parsed_map["economics"],
        "milestones": parsed_map["milestones"] or memory.milestones,
    }

    agent_cards_payload = {
        "version": "v1",
        "generated_at": _iso_now(),
        "cards": enriched_cards,
    }
    integration_payload = _integration_registry_payload(parsed_map)
    reward_payload = _reward_policy_payload(parsed_map)
    antigravity_payload = _extension_map_payload(parsed_map, "antigravity")
    org_github_payload = _extension_map_payload(parsed_map, "org-github")

    outputs = {
        "agent_cards": repo / "registry" / "agents" / "enterprise_agent_cards.v1.json",
        "integration_registry": repo / "registry" / "integrations" / "integration_registry.v1.json",
        "reward_policy": repo / "registry" / "rewards" / "reward_policy_bundle.v1.json",
        "antigravity_extension_map": repo
        / "registry"
        / "interfaces"
        / "extension_node_map.antigravity.v1.json",
        "org_github_extension_map": repo
        / "registry"
        / "interfaces"
        / "extension_node_map.org-github.v1.json",
        "compiled_map": repo / "registry" / "maps" / "enterprise_agent_map.compiled.v1.json",
    }

    _write_json(outputs["agent_cards"], agent_cards_payload)
    _write_json(outputs["integration_registry"], integration_payload)
    _write_json(outputs["reward_policy"], reward_payload)
    _write_json(outputs["antigravity_extension_map"], antigravity_payload)
    _write_json(outputs["org_github_extension_map"], org_github_payload)
    _write_json(outputs["compiled_map"], compiled_map)

    if not skip_external_sync and antigravity_root:
        _write_json(Path(antigravity_root) / "enterprise_extension_node_map.v1.json", antigravity_payload)
    if not skip_external_sync and org_github_root:
        _write_json(
            Path(org_github_root) / "codex" / "generated" / "enterprise_extension_node_map.v1.json",
            org_github_payload,
        )

    return {
        "memory": memory.to_dict(),
        "parsed_map": parsed_map,
        "compiled_map": compiled_map,
        "generated_paths": {key: str(path) for key, path in outputs.items()},
    }

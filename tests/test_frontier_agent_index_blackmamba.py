from __future__ import annotations

import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = REPO_ROOT / "scripts" / "build_frontier_agent_index.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("build_frontier_agent_index", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_frontier_cards_include_blackmamba_enrichment() -> None:
    module = _load_module()
    cards = module._build_cards(
        ["route_a2a_intent", "get_runtime_assignment"],
        token_ref="runtime/rbac/frontier_rbac_tokens.local.json",
        enterprise_cards={
            "agent:frontier.endpoint.gpt": {
                "enterprise_role": "delivery",
                "reward_profile": "delivery",
                "reward_weights": {"semantic": 0.3, "systems": 0.4, "domain": 0.3},
                "ownership": {"owner": "delivery-core"},
                "topology_node_refs": ["frontier-registry", "github-actions-control"],
                "approval_mode": "checkpointed",
                "budget_defaults": {"minutes": 80, "tokens": 200000, "cost_usd": 24.0},
            },
            "agent:frontier.anthropic.claude": {},
            "agent:frontier.vertex.gemini": {},
            "agent:frontier.ollama.llama": {},
        },
        memory_bundle={
            "working_style": {"tone": "direct"},
            "memory_sources": [{"kind": "agents", "path": "C:/Users/eqhsp/AGENTS.md", "exists": True}],
        },
    )

    endpoint_card = next(card for card in cards if card["agent_id"] == "agent:frontier.endpoint.gpt")
    assert endpoint_card["enterprise_role"] == "delivery"
    assert endpoint_card["working_style"]["tone"] == "direct"
    assert endpoint_card["topology_nodes"] == ["frontier-registry", "github-actions-control"]

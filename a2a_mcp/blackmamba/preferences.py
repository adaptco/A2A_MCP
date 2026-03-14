"""Workspace memory loaders for root agent anchors."""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


JSON_FENCE_PATTERN = re.compile(r"```(?:json|jsonc)?\s*(\{.*?\})\s*```", re.DOTALL)


DEFAULT_WORKING_STYLE = {
    "tone": "direct",
    "execution_mode": "deterministic_moa_loop",
    "planning_bias": "implementation_first",
    "risk_posture": "guarded_delivery",
    "context_strategy": "chunk_relevant_context",
    "time_management": "checkpointed",
    "token_management": "budgeted",
}

DEFAULT_WORKSPACE_PREFERENCES = {
    "working_style": DEFAULT_WORKING_STYLE,
    "topology_mode": "single_mcp_environment",
    "runtime_priority": ["planner", "architect", "coder", "tester", "reviewer"],
    "approval_mode": "browser_hitl",
    "reward_focus": ["semantic", "systems", "domain"],
}

DEFAULT_AGENT_OVERRIDES = {
    "agent:blackmamba": {
        "enterprise_role": "timekeeper",
        "working_style": {
            "tone": "precise",
            "time_management": "cost_estimation_first",
            "token_management": "predict_then_allocate",
        },
    }
}

DEFAULT_MILESTONES = [
    {
        "id": "M1",
        "name": "Canonical model and memory refactor",
        "duration_business_days": [2, 3],
        "token_budget": [120000, 180000],
    },
    {
        "id": "M2",
        "name": "MAP XML and expanded agent-card compiler",
        "duration_business_days": [3, 4],
        "token_budget": [180000, 260000],
    },
    {
        "id": "M3",
        "name": "Extension/interface topology wiring",
        "duration_business_days": [3, 5],
        "token_budget": [220000, 320000],
    },
    {
        "id": "M4",
        "name": "BlackMamba library and economics model",
        "duration_business_days": [4, 5],
        "token_budget": [240000, 340000],
    },
    {
        "id": "M5",
        "name": "HITL browser app and sandbox validation",
        "duration_business_days": [3, 4],
        "token_budget": [180000, 260000],
    },
    {
        "id": "M6",
        "name": "PR reconciliation and release hardening",
        "duration_business_days": [4, 6],
        "token_budget": [260000, 380000],
    },
    {
        "id": "M7",
        "name": "Org .github promotion and live enterprise connectors",
        "duration_business_days": [5, 8],
        "token_budget": [300000, 500000],
    },
]

DEFAULT_TOKEN_BUDGET = {
    "loop_1": {"tokens": [940000, 1360000], "business_days": [15, 21]},
    "program": {"tokens": [1500000, 2240000], "business_days": [24, 35]},
}

DEFAULT_SHARED_SKILLS = {
    "shared_skills": [
        "moa-cli-coding-fabric",
        "agents-as-embodied-avatars",
        "runtime-avatar-wasm-generator",
        "playwright",
        "linear",
        "openai-docs",
    ],
    "integration_nodes": [
        "office-graph",
        "google-workspace-sync",
        "airtable-agent-base",
        "github-actions-control",
        "firebase-studio-sandbox",
        "vertex-ai-orchestrator",
        "doors-requirements",
        "windchill-rvs-delivery",
        "canvas-frontdoor",
        "antigravity-hitl",
    ],
}


@dataclass(slots=True)
class MemorySource:
    """Source metadata for root memory anchors."""

    kind: str
    path: str
    exists: bool


@dataclass(slots=True)
class WorkspaceMemoryBundle:
    """Normalized memory bundle consumed by card and planner builders."""

    root_path: str
    workspace_preferences: dict[str, Any]
    working_style: dict[str, Any]
    agent_overrides: dict[str, Any]
    milestones: list[dict[str, Any]]
    token_budget: dict[str, Any]
    shared_skills: list[str]
    integration_nodes: list[str]
    memory_sources: list[MemorySource] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["memory_sources"] = [asdict(source) for source in self.memory_sources]
        return payload


def _first_json_object(text: str) -> dict[str, Any]:
    for match in JSON_FENCE_PATTERN.finditer(text):
        candidate = match.group(1).strip()
        try:
            loaded = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(loaded, dict):
            return loaded
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        loaded = json.loads(stripped)
        if isinstance(loaded, dict):
            return loaded
    return {}


def _load_markdown_json(path: Path, default_payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return json.loads(json.dumps(default_payload)), False

    payload = _first_json_object(path.read_text(encoding="utf-8"))
    if not payload:
        payload = json.loads(json.dumps(default_payload))
    return payload, True


def load_workspace_preferences(
    root_path: str | Path = "C:\\",
    agents_path: str | Path | None = None,
    skills_path: str | Path | None = None,
) -> WorkspaceMemoryBundle:
    """Load and normalize persistent workspace memory anchors."""

    root = Path(root_path)
    user_home = Path(os.environ.get("USERPROFILE", str(root)))

    agents_candidates = (
        [Path(agents_path)]
        if agents_path
        else [root / "AGENTS.md", user_home / "AGENTS.md"]
    )
    skills_candidates = (
        [Path(skills_path)]
        if skills_path
        else [root / "Skills.md", user_home / "Skills.md"]
    )

    agents_anchor = next((path for path in agents_candidates if path.exists()), agents_candidates[0])
    skills_anchor = next((path for path in skills_candidates if path.exists()), skills_candidates[0])

    agents_payload, agents_exists = _load_markdown_json(
        agents_anchor,
        {
            "workspace_preferences": DEFAULT_WORKSPACE_PREFERENCES,
            "agent_overrides": DEFAULT_AGENT_OVERRIDES,
            "milestones": DEFAULT_MILESTONES,
            "token_budget": DEFAULT_TOKEN_BUDGET,
        },
    )
    skills_payload, skills_exists = _load_markdown_json(skills_anchor, DEFAULT_SHARED_SKILLS)

    workspace_preferences = {
        **DEFAULT_WORKSPACE_PREFERENCES,
        **agents_payload.get("workspace_preferences", {}),
    }
    working_style = {
        **DEFAULT_WORKING_STYLE,
        **workspace_preferences.get("working_style", {}),
    }
    workspace_preferences["working_style"] = working_style

    return WorkspaceMemoryBundle(
        root_path=str(root),
        workspace_preferences=workspace_preferences,
        working_style=working_style,
        agent_overrides=agents_payload.get("agent_overrides", DEFAULT_AGENT_OVERRIDES),
        milestones=agents_payload.get("milestones", DEFAULT_MILESTONES),
        token_budget=agents_payload.get("token_budget", DEFAULT_TOKEN_BUDGET),
        shared_skills=list(skills_payload.get("shared_skills", DEFAULT_SHARED_SKILLS["shared_skills"])),
        integration_nodes=list(
            skills_payload.get("integration_nodes", DEFAULT_SHARED_SKILLS["integration_nodes"])
        ),
        memory_sources=[
            MemorySource(kind="agents", path=str(agents_anchor), exists=agents_exists),
            MemorySource(kind="skills", path=str(skills_anchor), exists=skills_exists),
        ],
    )

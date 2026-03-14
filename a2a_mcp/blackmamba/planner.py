"""BlackMamba task planner and checkpoint estimator."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .economics import BudgetSignals, SignalEconomicsModel
from .enterprise_map import REPO_ROOT, compile_enterprise_artifacts


def _iso_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


@dataclass(slots=True)
class RoleBudget:
    """Budget allocation for a single deterministic MoA stage."""

    stage: str
    agent_id: str
    predicted_tokens: int
    predicted_minutes: float
    predicted_cost_usd: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TaskEstimate:
    """Serializable task estimate payload."""

    task_id: str
    objective: str
    complexity: float
    risk: float
    interfaces: list[str]
    predicted_tokens: int
    predicted_minutes: float
    predicted_cost_usd: float
    approval_checkpoints: list[dict[str, Any]]
    stage_budgets: list[RoleBudget]
    reward_profile: dict[str, Any]
    topology_nodes: list[str]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["stage_budgets"] = [stage.to_dict() for stage in self.stage_budgets]
        return payload


class TokenBudgetAllocator:
    """Allocate a total token budget across the deterministic MoA stages."""

    STAGE_AGENT_MAP = {
        "Planner": "agent:blackmamba",
        "Architect": "agent:frontier.vertex.gemini",
        "Coder": "agent:frontier.endpoint.gpt",
        "Tester": "agent:frontier.ollama.llama",
        "Reviewer": "agent:frontier.anthropic.claude",
    }

    DEFAULT_WEIGHTS = {
        "Planner": 0.16,
        "Architect": 0.18,
        "Coder": 0.31,
        "Tester": 0.17,
        "Reviewer": 0.18,
    }

    def allocate(
        self,
        total_tokens: int,
        total_minutes: float,
        total_cost_usd: float,
    ) -> list[RoleBudget]:
        allocations: list[RoleBudget] = []
        remaining_tokens = total_tokens
        remaining_minutes = total_minutes
        remaining_cost = total_cost_usd
        stages = list(self.DEFAULT_WEIGHTS.items())

        for index, (stage, weight) in enumerate(stages):
            if index == len(stages) - 1:
                stage_tokens = remaining_tokens
                stage_minutes = round(remaining_minutes, 2)
                stage_cost = round(remaining_cost, 2)
            else:
                stage_tokens = int(round(total_tokens * weight))
                stage_minutes = round(total_minutes * weight, 2)
                stage_cost = round(total_cost_usd * weight, 2)
                remaining_tokens -= stage_tokens
                remaining_minutes -= stage_minutes
                remaining_cost = round(remaining_cost - stage_cost, 2)

            allocations.append(
                RoleBudget(
                    stage=stage,
                    agent_id=self.STAGE_AGENT_MAP[stage],
                    predicted_tokens=stage_tokens,
                    predicted_minutes=stage_minutes,
                    predicted_cost_usd=stage_cost,
                )
            )
        return allocations


class TimeBudgetManager:
    """Helper for checkpoint-aware scheduling."""

    def checkpoint_penalty_minutes(self, checkpoint_count: int, approval_penalty_minutes: float) -> float:
        return round(max(0, checkpoint_count) * approval_penalty_minutes, 2)


class AgentBlackMamba:
    """Planner that projects runtime, token burn, and approval checkpoints."""

    def __init__(
        self,
        *,
        repo_root: str | Path | None = None,
        root_path: str | Path = "C:\\",
        enterprise_map_path: str | Path | None = None,
        agents_memory_path: str | Path | None = None,
        skills_memory_path: str | Path | None = None,
    ) -> None:
        self.repo_root = Path(repo_root) if repo_root else REPO_ROOT
        self.root_path = root_path
        self.enterprise_map_path = (
            Path(enterprise_map_path)
            if enterprise_map_path
            else self.repo_root / "specs" / "enterprise_agent_map.xml"
        )
        result = compile_enterprise_artifacts(
            map_path=self.enterprise_map_path,
            repo_root=self.repo_root,
            root_path=self.root_path,
            agents_memory_path=agents_memory_path,
            skills_memory_path=skills_memory_path,
            skip_external_sync=True,
        )
        self.compiled_map = result["compiled_map"]
        self.economics = SignalEconomicsModel.from_config(self.compiled_map["economics"])
        self.token_allocator = TokenBudgetAllocator()
        self.time_manager = TimeBudgetManager()

    def _select_topology_nodes(self, interfaces: list[str]) -> list[str]:
        node_ids = []
        by_interface = {node["interface"]: node["id"] for node in self.compiled_map["topology_nodes"]}
        for interface in interfaces:
            node_id = by_interface.get(interface)
            if node_id:
                node_ids.append(node_id)
        if "root-memory" not in node_ids:
            node_ids.insert(0, "root-memory")
        return list(dict.fromkeys(node_ids))

    def _reward_profile_for_risk(self, risk: float) -> dict[str, Any]:
        preferred = "governance" if risk >= 0.7 else "delivery"
        for profile in self.compiled_map["reward_profiles"]:
            if profile["id"] == preferred:
                return profile
        return self.compiled_map["reward_profiles"][0]

    def _approval_checkpoints(
        self,
        interfaces: list[str],
        complexity: float,
        risk: float,
    ) -> list[dict[str, Any]]:
        checkpoints = []
        for checkpoint in self.compiled_map["hitl_checkpoints"]:
            if checkpoint["id"] == "release-review" and risk < 0.72 and len(interfaces) < 4:
                continue
            if checkpoint["id"] == "scope-review" and complexity < 0.35:
                continue
            checkpoints.append(checkpoint)
        return checkpoints

    def estimate_task(
        self,
        *,
        objective: str,
        complexity: float = 0.55,
        risk: float = 0.4,
        interfaces: list[str] | None = None,
        dependencies: list[str] | None = None,
        reward_alignment: float = 0.82,
    ) -> TaskEstimate:
        selected_interfaces = interfaces or [
            "frontier-registry",
            "github-actions-control",
            "antigravity-hitl",
        ]
        selected_dependencies = dependencies or []
        checkpoints = self._approval_checkpoints(selected_interfaces, complexity, risk)
        profile = self._reward_profile_for_risk(risk)
        profile_weight = sum(dimension["weight"] for dimension in profile["dimensions"]) / max(
            1, len(profile["dimensions"])
        )
        signals = BudgetSignals(
            complexity=complexity,
            risk=risk,
            interface_count=len(selected_interfaces),
            checkpoint_count=len(checkpoints),
            dependency_count=len(selected_dependencies),
            reward_alignment=min(1.0, reward_alignment * max(0.8, profile_weight)),
        )
        cost = self.economics.estimate(signals)
        stages = self.token_allocator.allocate(
            total_tokens=cost.predicted_tokens,
            total_minutes=cost.predicted_minutes,
            total_cost_usd=cost.predicted_cost_usd,
        )
        task_id = f"blackmamba-{_slug(objective)[:48] or 'task'}"
        return TaskEstimate(
            task_id=task_id,
            objective=objective,
            complexity=round(complexity, 4),
            risk=round(risk, 4),
            interfaces=selected_interfaces,
            predicted_tokens=cost.predicted_tokens,
            predicted_minutes=cost.predicted_minutes,
            predicted_cost_usd=cost.predicted_cost_usd,
            approval_checkpoints=checkpoints,
            stage_budgets=stages,
            reward_profile=profile,
            topology_nodes=self._select_topology_nodes(selected_interfaces),
            generated_at=_iso_now(),
        )

    def write_estimate(self, output_path: str | Path, **kwargs: Any) -> dict[str, Any]:
        estimate = self.estimate_task(**kwargs).to_dict()
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(estimate, indent=2) + "\n", encoding="utf-8")
        return estimate

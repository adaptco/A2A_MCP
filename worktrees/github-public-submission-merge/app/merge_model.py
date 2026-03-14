"""Domain model for orchestrating branch merge waves and middleware contract."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Branch:
    """Metadata describing a Git branch that participates in the merge plan."""

    id: str
    name: str
    category: str
    primary_branch: str
    description: str
    owner: str
    status: str
    dependencies: List[str]
    artifacts: List[str]
    ci: Dict[str, List[str]]

    def summary(self) -> Dict[str, Any]:
        """Return a normalized representation safe for API exposure."""

        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "primary_branch": self.primary_branch,
            "description": self.description,
            "owner": self.owner,
            "status": self.status,
            "dependencies": list(self.dependencies),
            "artifacts": list(self.artifacts),
            "ci": {key: list(value) for key, value in self.ci.items()},
        }

    def merge_view(self) -> Dict[str, Any]:
        """Return the subset of branch attributes needed for merge planning."""

        return {
            "id": self.id,
            "name": self.name,
            "primary_branch": self.primary_branch,
            "status": self.status,
            "dependencies": list(self.dependencies),
            "artifacts": list(self.artifacts),
        }


@dataclass
class MergeWave:
    """Represents a merge wave where a set of branches land into a target."""

    id: str
    order: int
    description: str
    target: str
    sources: List[str]
    preconditions: List[str]
    validation: List[str]


@dataclass
class AutomationHook:
    """Automation step that should run around a merge wave."""

    id: str
    description: str
    entrypoint: str
    triggers: List[str]


@dataclass
class NotificationRoute:
    """Notification channel used to broadcast merge status."""

    channel: str
    events: List[str]
    summary_template: str


@dataclass
class AutomationPlan:
    """Encapsulates hooks and notifications used by automation."""

    hooks: List[AutomationHook]
    notifications: List[NotificationRoute]


@dataclass
class MiddlewareRoute:
    """HTTP route exposed by the middleware service."""

    method: str
    path: str
    purpose: str


@dataclass
class MiddlewareContract:
    """Contract detailing middleware capabilities and routes."""

    service_name: str
    description: str
    capabilities: List[str]
    routes: List[MiddlewareRoute]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the contract for HTTP responses."""

        return {
            "service_name": self.service_name,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "routes": [asdict(route) for route in self.routes],
        }


@dataclass
class MergeModel:
    """Aggregate merge planning model consumed by middleware and CI."""

    version: str
    updated: str
    branches: Dict[str, Branch]
    branch_order: List[str]
    merge_waves: List[MergeWave]
    automation: AutomationPlan
    middleware_contract: MiddlewareContract

    @classmethod
    def empty(cls) -> "MergeModel":
        """Return a safe empty model when configuration is unavailable."""

        automation = AutomationPlan(hooks=[], notifications=[])
        contract = MiddlewareContract(
            service_name="core-orchestrator-middleware",
            description="No merge model configured.",
            capabilities=[],
            routes=[],
        )
        return cls(
            version="0.0.0",
            updated="",
            branches={},
            branch_order=[],
            merge_waves=[],
            automation=automation,
            middleware_contract=contract,
        )

    @classmethod
    def from_file(cls, path: Path) -> "MergeModel":
        """Load a merge model from a JSON file."""

        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MergeModel":
        """Instantiate a merge model from raw dictionary data."""

        branch_objs = [Branch(**branch) for branch in data.get("branches", [])]
        branches = {branch.id: branch for branch in branch_objs}
        branch_order = [branch.id for branch in branch_objs]

        waves = [MergeWave(**wave) for wave in data.get("merge_waves", [])]
        waves.sort(key=lambda wave: (wave.order, wave.id))

        automation_data = data.get("automation", {})
        hooks = [AutomationHook(**hook) for hook in automation_data.get("hooks", [])]
        notifications = [
            NotificationRoute(**route) for route in automation_data.get("notifications", [])
        ]
        automation = AutomationPlan(hooks=hooks, notifications=notifications)

        middleware_data = data.get("middleware_contract", {})
        routes = [MiddlewareRoute(**route) for route in middleware_data.get("routes", [])]
        middleware_contract = MiddlewareContract(
            service_name=middleware_data.get("service_name", "core-orchestrator-middleware"),
            description=middleware_data.get("description", ""),
            capabilities=middleware_data.get("capabilities", []),
            routes=routes,
        )

        return cls(
            version=data.get("version", "0.0.0"),
            updated=data.get("updated", ""),
            branches=branches,
            branch_order=branch_order,
            merge_waves=waves,
            automation=automation,
            middleware_contract=middleware_contract,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the entire model back to a dictionary."""

        ordered_branches = [self.branches[branch_id] for branch_id in self.branch_order]
        return {
            "version": self.version,
            "updated": self.updated,
            "branches": [asdict(branch) for branch in ordered_branches],
            "merge_waves": [asdict(wave) for wave in self.merge_waves],
            "automation": {
                "hooks": [asdict(hook) for hook in self.automation.hooks],
                "notifications": [asdict(note) for note in self.automation.notifications],
            },
            "middleware_contract": self.middleware_contract.to_dict(),
        }

    def get_branch(self, branch_id: str) -> Optional[Branch]:
        """Retrieve a branch by identifier."""

        return self.branches.get(branch_id)

    def branches_summary(self) -> List[Dict[str, Any]]:
        """Return the list of branches in a stable order."""

        return [self.branches[branch_id].summary() for branch_id in self.branch_order]

    def plan_summary(self) -> List[Dict[str, Any]]:
        """Return the merge plan with branch metadata resolved."""

        plan: List[Dict[str, Any]] = []
        for wave in self.merge_waves:
            sources = [
                self.branches[source].merge_view()
                for source in wave.sources
                if source in self.branches
            ]
            plan.append(
                {
                    "id": wave.id,
                    "order": wave.order,
                    "description": wave.description,
                    "target": wave.target,
                    "sources": sources,
                    "preconditions": list(wave.preconditions),
                    "validation": list(wave.validation),
                }
            )
        return plan

    def automation_summary(self) -> Dict[str, Any]:
        """Return automation hooks and notification channels."""

        return {
            "hooks": [
                {
                    "id": hook.id,
                    "description": hook.description,
                    "entrypoint": hook.entrypoint,
                    "triggers": list(hook.triggers),
                }
                for hook in self.automation.hooks
            ],
            "notifications": [
                {
                    "channel": route.channel,
                    "events": list(route.events),
                    "summary_template": route.summary_template,
                }
                for route in self.automation.notifications
            ],
        }

    def middleware_summary(self) -> Dict[str, Any]:
        """Expose the middleware contract in API-friendly structure."""

        return self.middleware_contract.to_dict()


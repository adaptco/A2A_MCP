"""CI/CD monitor agent for tracking workflow health and release readiness."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class WorkflowRunSnapshot:
    """Normalized view of a workflow run event."""

    run_id: int
    name: str
    status: str
    conclusion: str
    head_sha: str
    head_branch: str
    html_url: str
    event: str
    run_number: int
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "name": self.name,
            "status": self.status,
            "conclusion": self.conclusion,
            "head_sha": self.head_sha,
            "head_branch": self.head_branch,
            "html_url": self.html_url,
            "event": self.event,
            "run_number": self.run_number,
            "updated_at": self.updated_at,
        }


class CICDMonitorAgent:
    """
    Aggregates workflow_run events and computes production readiness.

    A commit is considered production-ready when all required workflows are
    present, completed, and concluded successfully.
    """

    def __init__(
        self,
        required_workflows: Optional[List[str]] = None,
        production_branches: Optional[List[str]] = None,
    ) -> None:
        self.required_workflows = required_workflows or [
            "Agents CI/CD",
            "Python application",
            "A2A-MCP Integration Tests",
        ]
        self.production_branches = production_branches or ["main", "master", "production"]
        self._runs_by_id: Dict[int, WorkflowRunSnapshot] = {}
        self._runs_by_sha: Dict[str, Dict[str, WorkflowRunSnapshot]] = {}

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _extract_workflow_run(payload: Dict[str, Any]) -> Dict[str, Any]:
        if isinstance(payload.get("workflow_run"), dict):
            return payload["workflow_run"]
        return payload

    def ingest_github_workflow_event(
        self,
        payload: Dict[str, Any],
        event_type: str = "workflow_run",
    ) -> Dict[str, Any]:
        """
        Ingest a GitHub workflow event payload and return status snapshot.

        Supports workflow_run payloads and normalized workflow_run-like JSON.
        """
        if event_type not in {"workflow_run", "workflow_dispatch", "release"}:
            raise ValueError(f"Unsupported event type for CI/CD monitor: {event_type}")

        run = self._extract_workflow_run(payload)
        run_id = int(run.get("id", 0))
        if run_id <= 0:
            raise ValueError("workflow_run.id is required")

        name = str(run.get("name", "unknown-workflow"))
        status = str(run.get("status", "unknown"))
        conclusion = str(run.get("conclusion") or "unknown")
        head_sha = str(run.get("head_sha", "")).strip()
        if not head_sha:
            raise ValueError("workflow_run.head_sha is required")

        head_branch = str(run.get("head_branch") or "")
        html_url = str(run.get("html_url") or "")
        run_number = int(run.get("run_number", 0))
        event = str(run.get("event") or event_type)

        snapshot = WorkflowRunSnapshot(
            run_id=run_id,
            name=name,
            status=status,
            conclusion=conclusion,
            head_sha=head_sha,
            head_branch=head_branch,
            html_url=html_url,
            event=event,
            run_number=run_number,
            updated_at=self._now_iso(),
        )

        self._runs_by_id[snapshot.run_id] = snapshot
        self._runs_by_sha.setdefault(snapshot.head_sha, {})[snapshot.name] = snapshot
        return self.get_commit_status(snapshot.head_sha)

    def get_run_status(self, run_id: int) -> Optional[Dict[str, Any]]:
        run = self._runs_by_id.get(run_id)
        return run.to_dict() if run else None

    def get_commit_status(self, head_sha: str) -> Dict[str, Any]:
        by_workflow = self._runs_by_sha.get(head_sha, {})

        missing = [w for w in self.required_workflows if w not in by_workflow]
        incomplete = [
            w
            for w in self.required_workflows
            if w in by_workflow and by_workflow[w].status != "completed"
        ]
        failed = [
            w
            for w in self.required_workflows
            if w in by_workflow and by_workflow[w].conclusion != "success"
        ]

        ready = not missing and not incomplete and not failed
        branch = ""
        if by_workflow:
            branch = next(iter(by_workflow.values())).head_branch

        return {
            "head_sha": head_sha,
            "head_branch": branch,
            "required_workflows": self.required_workflows,
            "missing_workflows": missing,
            "incomplete_workflows": incomplete,
            "failed_workflows": failed,
            "ready_for_release": ready,
            "production_ready": ready and branch in self.production_branches,
            "workflows": {name: run.to_dict() for name, run in by_workflow.items()},
            "updated_at": self._now_iso(),
        }

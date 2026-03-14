"""Release orchestration model for managing Claude->bot review handoff."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional


class ReleasePhase(str, Enum):
    WAITING_FOR_CLAUDE = "waiting_for_claude"
    RUNNING_VALIDATION = "running_validation"
    RUNNING_BOT_REVIEW = "running_bot_review"
    READY_FOR_RELEASE = "ready_for_release"
    BLOCKED = "blocked"


@dataclass
class ReleaseSignals:
    """Signals used to decide the next phase."""

    claude_task_complete: bool = False
    tests_passed: bool = False
    conflicts_resolved: bool = False
    bot_review_complete: bool = False
    claude_checked_todos: int = 0
    claude_total_todos: int = 0
    handshake_initialized: bool = False
    runtime_assignment_written: bool = False
    runtime_workers_ready: int = 0
    token_stream_normalized: bool = False
    kernel_model_written: bool = False
    root_specs_scaffolded: bool = False
    api_token_release_controlled: bool = False
    blocking_reason: str = ""


class ReleaseOrchestrator:
    """State resolver used by the managing agent for release gating."""

    def __init__(self, model_name: str = "CWUG-v1") -> None:
        self.model_name = model_name

    def resolve_phase(self, signals: ReleaseSignals) -> ReleasePhase:
        if signals.blocking_reason:
            return ReleasePhase.BLOCKED
        if not signals.claude_task_complete:
            return ReleasePhase.WAITING_FOR_CLAUDE
        if not (signals.tests_passed and signals.conflicts_resolved):
            return ReleasePhase.RUNNING_VALIDATION
        if not (
            signals.kernel_model_written
            and signals.root_specs_scaffolded
            and signals.api_token_release_controlled
        ):
            return ReleasePhase.RUNNING_VALIDATION
        if not signals.bot_review_complete:
            return ReleasePhase.RUNNING_BOT_REVIEW
        return ReleasePhase.READY_FOR_RELEASE

    def system_state(self, signals: ReleaseSignals) -> Dict[str, object]:
        """Build a serializable state snapshot for workflows and dashboards."""
        phase = self.resolve_phase(signals)
        todo_progress = {
            "checked": signals.claude_checked_todos,
            "total": signals.claude_total_todos,
        }
        return {
            "model": self.model_name,
            "phase": phase.value,
            "bridge_schema": "runtime.assignment.v1",
            "claude": {
                "task_complete": signals.claude_task_complete,
                "todo_progress": todo_progress,
            },
            "validation": {
                "tests_passed": signals.tests_passed,
                "conflicts_resolved": signals.conflicts_resolved,
            },
            "runtime_bridge": {
                "handshake_initialized": signals.handshake_initialized,
                "runtime_assignment_written": signals.runtime_assignment_written,
                "runtime_workers_ready": signals.runtime_workers_ready,
                "token_stream_normalized": signals.token_stream_normalized,
                "kernel_model_written": signals.kernel_model_written,
                "root_specs_scaffolded": signals.root_specs_scaffolded,
                "api_token_release_controlled": signals.api_token_release_controlled,
            },
            "bot_review": {
                "complete": signals.bot_review_complete,
            },
            "blocked_reason": signals.blocking_reason or None,
            "next_action": self._next_action(phase),
        }

    @staticmethod
    def _next_action(phase: ReleasePhase) -> str:
        if phase == ReleasePhase.WAITING_FOR_CLAUDE:
            return "wait_for_claude_todos_to_complete"
        if phase == ReleasePhase.RUNNING_VALIDATION:
            return "run_ci_tests_and_conflict_checks"
        if phase == ReleasePhase.RUNNING_BOT_REVIEW:
            return "request_bot_review_and_finalize_pr"
        if phase == ReleasePhase.READY_FOR_RELEASE:
            return "publish_foundation_release_bundle"
        return "investigate_and_resolve_blocker"

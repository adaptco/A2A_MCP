from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, List

from ..schemas.task import CanonicalTask
from . import proposals


@dataclass
class GateResult:
    name: str
    ok: bool
    reason: str | None = None


def gate_cross_tool_completion(task: CanonicalTask, ctx: Dict) -> GateResult:
    if ctx.get("proposed_status") != "done":
        return GateResult("cross_tool_completion", True)
    external = ctx.get("external_statuses", {})
    if all(status == "done" for status in external.values()):
        return GateResult("cross_tool_completion", True)
    return GateResult("cross_tool_completion", False, "linked systems not done")


def gate_dependency_closure(task: CanonicalTask, ctx: Dict) -> GateResult:
    if ctx.get("dependencies_done", True):
        return GateResult("dependency_closure", True)
    return GateResult("dependency_closure", False, "dependencies incomplete")


def gate_date_sanity(task: CanonicalTask, ctx: Dict) -> GateResult:
    start = task.start_date
    due = task.due_date
    if start and due and start > due:
        return GateResult("date_sanity", False, "start after due")
    latest = ctx.get("latest_linked_due_date")
    if due and latest and due < latest:
        return GateResult("date_sanity", False, "due before linked due")
    return GateResult("date_sanity", True)


def gate_owner_parity(task: CanonicalTask, ctx: Dict) -> GateResult:
    if ctx.get("owner_resolvable", True):
        return GateResult("owner_parity", True)
    return GateResult("owner_parity", False, "owner not resolvable")


def gate_llm_advisory(task: CanonicalTask, ctx: Dict) -> GateResult:
    ok, note = proposals.fake_analyzer(task)
    if ok:
        return GateResult("llm_advisory", True)
    return GateResult("llm_advisory", False, note)


ALL_GATES = [
    gate_cross_tool_completion,
    gate_dependency_closure,
    gate_date_sanity,
    gate_owner_parity,
    gate_llm_advisory,
]


def evaluate_gates(task: CanonicalTask, ctx: Dict) -> List[GateResult]:
    return [gate(task, ctx) for gate in ALL_GATES]

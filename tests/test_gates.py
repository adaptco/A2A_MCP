from datetime import date

from app.schemas.task import CanonicalTask
from app.services import gates


def make_task(**kwargs):
    base = {
        "source": "monday",
        "name": "Test",
        "status": "todo",
    }
    base.update(kwargs)
    return CanonicalTask(**base)


def test_cross_tool_completion():
    task = make_task()
    ctx = {"proposed_status": "done", "external_statuses": {"airtable": "done"}}
    res = gates.gate_cross_tool_completion(task, ctx)
    assert res.ok
    ctx = {"proposed_status": "done", "external_statuses": {"airtable": "doing"}}
    res = gates.gate_cross_tool_completion(task, ctx)
    assert not res.ok


def test_dependency_closure():
    task = make_task()
    res = gates.gate_dependency_closure(task, {"dependencies_done": True})
    assert res.ok
    res = gates.gate_dependency_closure(task, {"dependencies_done": False})
    assert not res.ok


def test_date_sanity():
    task = make_task(start_date=date(2023, 1, 10), due_date=date(2023, 1, 5))
    res = gates.gate_date_sanity(task, {})
    assert not res.ok
    task = make_task(start_date=date(2023, 1, 1), due_date=date(2023, 1, 5))
    res = gates.gate_date_sanity(task, {"latest_linked_due_date": date(2023, 1, 6)})
    assert not res.ok


def test_owner_parity():
    task = make_task()
    res = gates.gate_owner_parity(task, {"owner_resolvable": True})
    assert res.ok
    res = gates.gate_owner_parity(task, {"owner_resolvable": False})
    assert not res.ok


def test_llm_advisory():
    task = make_task(name="Anomaly task")
    res = gates.gate_llm_advisory(task, {})
    assert not res.ok

"""
Dot — Task Graph Parser (agents/Dot/parse_graph.py)

Parses task-graph.a2a.json, resolves dependency order via topological sort,
and emits a JSON matrix for GitHub Actions strategy.matrix.
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict, deque
from pathlib import Path


def load_task_graph(graph_path: str) -> list[dict]:
    """Load the canonical task graph JSON."""
    data = json.loads(Path(graph_path).read_text(encoding="utf-8"))
    return data.get("tasks", [])


def build_dependency_map(task_list: list[dict]) -> dict[str, list[str]]:
    """Build a mapping of task_id -> list of task_ids it depends on."""
    output_to_task: dict[str, str] = {}
    for task in task_list:
        for output in task.get("outputs", []):
            output_to_task[output] = task["task_id"]

    deps: dict[str, list[str]] = defaultdict(list)
    for task in task_list:
        for inp in task.get("inputs", []):
            if inp in output_to_task:
                deps[task["task_id"]].append(output_to_task[inp])
    return deps


def topological_sort(task_list: list[dict]) -> list[dict]:
    """Sort tasks by dependency order (topological sort)."""
    deps = build_dependency_map(task_list)
    task_map = {t["task_id"]: t for t in task_list}
    in_degree: dict[str, int] = {t["task_id"]: 0 for t in task_list}

    for task_id, dep_list in deps.items():
        in_degree[task_id] = len(dep_list)

    queue = deque([tid for tid, deg in in_degree.items() if deg == 0])
    ordered: list[dict] = []

    while queue:
        tid = queue.popleft()
        ordered.append(task_map[tid])
        # Find tasks that depend on this one
        for other_id, dep_list in deps.items():
            if tid in dep_list:
                in_degree[other_id] -= 1
                if in_degree[other_id] == 0:
                    queue.append(other_id)

    if len(ordered) != len(task_list):
        raise RuntimeError("Cycle detected in task graph!")

    return ordered


def emit_matrix(task_list: list[dict]) -> str:
    """Emit the JSON matrix for GitHub Actions strategy.matrix."""
    matrix_entries = []
    for task in task_list:
        matrix_entries.append({
            "task_id": task["task_id"],
            "agent_card": task.get("agent_card", ""),
            "llm_target": task.get("llm_target", "any"),
            "boo_binding": task.get("boo_binding", ""),
        })
    return json.dumps(matrix_entries)


if __name__ == "__main__":
    graph_file = sys.argv[1] if len(sys.argv) > 1 else "task-graph.a2a.json"
    tasks = load_task_graph(graph_file)
    sorted_tasks = topological_sort(tasks)
    matrix_json = emit_matrix(sorted_tasks)

    # Set GitHub Actions output
    import os
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"tasks={matrix_json}\n")
    else:
        print(f"tasks={matrix_json}")

    print(f"[Dot] ✅ Parsed {len(sorted_tasks)} tasks in dependency order")

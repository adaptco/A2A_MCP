"""
Echo — Webhook Relay Broker (agents/Echo/relay.py)

Reads task output from artifacts/, wraps in an A2A signed envelope,
and POSTs to the next agent's webhook endpoint via the Echo MCP server.
All cross-LLM messages route through Echo.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx


def build_envelope(
    task_id: str,
    from_agent: str,
    to_agent: str,
    llm_hop: str,
    payload: dict,
) -> dict:
    """Build an A2A protocol signed envelope."""
    return {
        "envelope_version": "1.0",
        "task_id": task_id,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "llm_hop": llm_hop,
        "payload": payload,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "signature": None,  # Ed25519 signing placeholder
    }


def load_task_output(task_id: str) -> dict:
    """Load the output artifact for a completed task."""
    output_file = Path("artifacts") / task_id / "output.txt"
    if output_file.exists():
        return {
            "artifact_id": f"{task_id}-output",
            "data": output_file.read_text(encoding="utf-8"),
        }
    return {"artifact_id": f"{task_id}-empty", "data": ""}


def resolve_next_agent(task_id: str) -> tuple[str, str]:
    """Resolve the next agent in the task graph for relay routing."""
    graph_file = Path("task-graph.a2a.json")
    if not graph_file.exists():
        return ("unknown", "any")

    graph = json.loads(graph_file.read_text(encoding="utf-8"))
    tasks = graph.get("tasks", [])

    # Find current task and the next one
    current_idx = None
    for i, task in enumerate(tasks):
        if task["task_id"] == task_id:
            current_idx = i
            break

    if current_idx is not None and current_idx + 1 < len(tasks):
        next_task = tasks[current_idx + 1]
        return (
            next_task.get("boo_binding", "unknown"),
            next_task.get("llm_target", "any"),
        )
    return ("Luma", "any")  # Default: send to quality gate


def relay(task_id: str) -> None:
    """Relay a completed task's output to the next agent via webhook."""
    # Load output
    payload = load_task_output(task_id)

    # Resolve routing
    to_agent, next_llm = resolve_next_agent(task_id)

    # Determine current agent from receipt
    receipt_file = Path("receipts") / f"{task_id}.json"
    from_agent = "Echo"
    current_llm = "any"
    if receipt_file.exists():
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        from_agent = receipt.get("agent_card", "Echo").split("/")[-1].replace(".py", "")
        current_llm = receipt.get("llm_target", "any")

    # Build envelope
    llm_hop = f"{current_llm} → {next_llm}"
    envelope = build_envelope(task_id, from_agent, to_agent, llm_hop, payload)

    # Log the envelope to receipts
    relay_receipt_dir = Path("receipts")
    relay_receipt_dir.mkdir(parents=True, exist_ok=True)
    relay_file = relay_receipt_dir / f"{task_id}-relay.json"
    relay_file.write_text(json.dumps(envelope, indent=2), encoding="utf-8")

    # POST to Echo MCP endpoint (or GitHub repository_dispatch as fallback)
    github_token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if github_token and repo:
        # Use repository_dispatch as the OS-agnostic webhook
        dispatch_url = f"https://api.github.com/repos/{repo}/dispatches"
        resp = httpx.post(
            dispatch_url,
            headers={
                "Authorization": f"Bearer {github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={
                "event_type": f"agent-relay-{to_agent.lower()}",
                "client_payload": envelope,
            },
            timeout=30,
        )
        event = f"agent-relay-{to_agent.lower()}"
        print(
            f"[Echo] Dispatched to {repo} "
            f"event={event} status={resp.status_code}"
        )
    else:
        print(f"[Echo] Envelope logged to {relay_file} (no GitHub token for dispatch)")

    print(f"[Echo] ✅ Relayed {task_id}: {from_agent} → {to_agent} ({llm_hop})")


if __name__ == "__main__":
    tid = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("TASK_ID", "T-000")
    relay(tid)

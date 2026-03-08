"""Post-deployment smoke tests for MCP gateway and orchestrator APIs."""

from __future__ import annotations

import os
import sys
from typing import Any

import requests


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _assert_ok(response: requests.Response, label: str) -> None:
    if response.status_code >= 400:
        raise RuntimeError(f"{label} failed ({response.status_code}): {response.text}")


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> requests.Response:
    return requests.post(url, json=payload, headers=headers or {}, timeout=30)


def main() -> int:
    mcp_base_url = _require_env("MCP_BASE_URL").rstrip("/")
    orchestrator_base_url = _require_env("ORCHESTRATOR_BASE_URL").rstrip("/")
    authorization = os.getenv("SMOKE_AUTHORIZATION", "Bearer invalid").strip()

    print(f"Checking MCP health: {mcp_base_url}/healthz")
    health_mcp = requests.get(f"{mcp_base_url}/healthz", timeout=10)
    _assert_ok(health_mcp, "mcp health")

    print(f"Checking orchestrator health: {orchestrator_base_url}/healthz")
    health_orchestrator = requests.get(f"{orchestrator_base_url}/healthz", timeout=10)
    _assert_ok(health_orchestrator, "orchestrator health")

    worldline_payload = {
        "tool_name": "ingest_worldline_block",
        "arguments": {
            "worldline_block": {
                "snapshot": {"repository": "adaptco/A2A_MCP"},
                "infrastructure_agent": {
                    "embedding_vector": [0.1, 0.2],
                    "token_stream": [{"token": "hello", "token_id": "id-1"}],
                    "artifact_clusters": {"cluster_0": ["artifact::hello"]},
                    "lora_attention_weights": {"cluster_0": 1.0},
                },
            },
            "authorization": authorization,
        },
    }
    print(f"Checking /tools/call success path: {mcp_base_url}/tools/call")
    tool_response = _post_json(
        f"{mcp_base_url}/tools/call",
        worldline_payload,
        headers={"Authorization": authorization},
    )
    _assert_ok(tool_response, "tools/call success")
    body = tool_response.json()
    if not body.get("ok", False):
        raise RuntimeError(f"tools/call returned failure: {body}")

    print(f"Checking plan ingress scheduling: {orchestrator_base_url}/plans/ingress")
    ingress_response = _post_json(
        f"{orchestrator_base_url}/plans/ingress",
        {"plan_id": "smoke-plan"},
    )
    _assert_ok(ingress_response, "plan ingress")

    print(f"Checking OIDC rejection path: {mcp_base_url}/tools/call")
    reject_response = _post_json(
        f"{mcp_base_url}/tools/call",
        {
            "tool_name": "ingest_worldline_block",
            "arguments": {
                "worldline_block": worldline_payload["arguments"]["worldline_block"],
                "authorization": "Bearer invalid",
            },
        },
        headers={"Authorization": "Bearer invalid"},
    )
    if reject_response.status_code < 400:
        reject_body = reject_response.json()
        if reject_body.get("ok", True):
            raise RuntimeError(f"OIDC rejection check expected failure, got: {reject_body}")

    print("Smoke tests passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

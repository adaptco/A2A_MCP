#!/usr/bin/env python3
"""Validate the Charley Fox runtime contract and A2A skill-card handoff."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


REQUIRED_SCENARIO_KEYS = {
    "scenario_id",
    "execution_id",
    "mission",
    "avatars",
    "wasm_runtime",
    "lora_reward_mechanism",
    "rag_api_scaffold",
}


def sha16(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def ensure(condition: bool, message: str, issues: list[str]) -> None:
    if not condition:
        issues.append(message)


def validate_agents_md(path: Path, issues: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    required_strings = (
        "## Agent Charley Fox",
        "## Dot",
        "dot-runtime-rest-point",
        "build-and-test",
        "dot.tensor.exchange.v1",
        "GEMINI_API_KEY",
        "/gemini/chat",
        "/gemini/embeddings",
        "[0, 0, 0]",
        "dot_product",
    )
    for marker in required_strings:
        ensure(marker in text, f"{path}: missing marker '{marker}'", issues)


def validate_scenario(
    scenario_path: Path,
    module_path: Path,
    rest_point_after: str,
    rest_point_job: str,
    issues: list[str],
) -> None:
    data = json.loads(scenario_path.read_text(encoding="utf-8"))

    for key in REQUIRED_SCENARIO_KEYS:
        ensure(key in data, f"{scenario_path}: missing top-level key '{key}'", issues)

    avatars = data.get("avatars", [])
    agent_names = {avatar.get("agent_name") for avatar in avatars if isinstance(avatar, dict)}
    ensure("CharleyFox" in agent_names, f"{scenario_path}: avatar cast missing CharleyFox", issues)
    ensure("Dot" in agent_names, f"{scenario_path}: avatar cast missing Dot", issues)

    rest_point = data.get("mission", {}).get("rest_point", {})
    ensure(rest_point.get("job") == rest_point_job, f"{scenario_path}: expected rest-point job '{rest_point_job}'", issues)
    ensure(rest_point.get("after") == rest_point_after, f"{scenario_path}: expected rest point after '{rest_point_after}'", issues)

    exchange = data.get("rag_api_scaffold", {}).get("normal_format", {})
    ensure(exchange.get("exchange_id") == "dot.tensor.exchange.v1", f"{scenario_path}: exchange id must be dot.tensor.exchange.v1", issues)
    ensure(exchange.get("metric") == "dot_product", f"{scenario_path}: metric must be dot_product", issues)
    ensure(exchange.get("origin") == [0, 0, 0], f"{scenario_path}: origin must be [0, 0, 0]", issues)

    routes = data.get("rag_api_scaffold", {}).get("provider_routes", [])
    gemini_route = next((route for route in routes if route.get("provider") == "gemini"), None)
    ensure(gemini_route is not None, f"{scenario_path}: missing gemini provider route", issues)
    if gemini_route is not None:
        ensure(gemini_route.get("auth_env") == "GEMINI_API_KEY", f"{scenario_path}: Gemini route must use GEMINI_API_KEY", issues)
        ensure(gemini_route.get("chat_endpoint") == "/gemini/chat", f"{scenario_path}: Gemini chat endpoint must be /gemini/chat", issues)
        ensure(gemini_route.get("embedding_endpoint") == "/gemini/embeddings", f"{scenario_path}: Gemini embedding endpoint must be /gemini/embeddings", issues)

    ensure(module_path.exists(), f"{module_path}: WASD control module not found", issues)
    if module_path.exists():
        expected_hash = data.get("wasm_runtime", {}).get("wasd_control_module", {}).get("source_hash")
        actual_hash = sha16(module_path.read_text(encoding="utf-8"))
        ensure(expected_hash == actual_hash, f"{scenario_path}: source hash mismatch for {module_path}", issues)


def validate_workflow(path: Path, rest_point_after: str, rest_point_job: str, issues: list[str]) -> None:
    text = path.read_text(encoding="utf-8")
    ensure(f"{rest_point_job}:" in text, f"{path}: missing job '{rest_point_job}'", issues)
    ensure(f"needs: {rest_point_after}" in text, f"{path}: missing rest-point dependency on '{rest_point_after}'", issues)
    ensure("python scripts/validate_runtime_contract.py" in text, f"{path}: missing runtime contract validation step", issues)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate Charley Fox runtime handoff artifacts")
    parser.add_argument("--scenario", default="runtime/scenarios/charley_fox_gemini_dot.runtime.v1.json")
    parser.add_argument("--module", default="runtime/wasm/charley_fox_gemini_dot_wasd_control_module.ts")
    parser.add_argument("--agents", default="Agents.md")
    parser.add_argument("--workflow", action="append", default=[])
    parser.add_argument("--rest-point-after", default="build-and-test")
    parser.add_argument("--rest-point-job", default="dot-runtime-rest-point")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    scenario_path = (repo_root / args.scenario).resolve()
    module_path = (repo_root / args.module).resolve()
    agents_path = (repo_root / args.agents).resolve()
    workflows = [(repo_root / workflow).resolve() for workflow in args.workflow]

    issues: list[str] = []
    ensure(scenario_path.exists(), f"{scenario_path}: scenario file not found", issues)
    ensure(agents_path.exists(), f"{agents_path}: Agents.md not found", issues)

    if agents_path.exists():
        validate_agents_md(agents_path, issues)
    if scenario_path.exists():
        validate_scenario(
            scenario_path,
            module_path,
            args.rest_point_after,
            args.rest_point_job,
            issues,
        )
    for workflow_path in workflows:
        ensure(workflow_path.exists(), f"{workflow_path}: workflow not found", issues)
        if workflow_path.exists():
            validate_workflow(workflow_path, args.rest_point_after, args.rest_point_job, issues)

    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "scenario": str(scenario_path),
                "module": str(module_path),
                "agents": str(agents_path),
                "workflows": [str(path) for path in workflows],
                "rest_point_after": args.rest_point_after,
                "rest_point_job": args.rest_point_job,
                "status": "ok",
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate the MCP 3D agent execution v1 spec pack."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, FormatChecker
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator.multimodal_worldline import build_worldline_block
from schemas.runtime_bridge import RuntimeAssignmentV1


REQUIRED_RUNTIME_TOOLS = {
    "submit_runtime_assignment",
    "get_runtime_assignment",
    "list_runtime_assignments",
    "embed_submit",
    "embed_status",
    "embed_lookup",
    "embed_dispatch_batch",
    "route_a2a_intent",
}
EXPECTED_CHAIN = ["Planner", "Architect", "Coder", "Tester", "Reviewer"]
EXPECTED_NODE_IDS = [
    "N0_INGRESS",
    "N1_PLANNING",
    "N2_RAG_CONTEXT",
    "N3_EXECUTION",
    "N4_VALIDATION",
    "N5_RELEASE",
]


@dataclass(frozen=True)
class SchemaCase:
    schema_file: str
    valid_fixture: str
    invalid_fixture: str
    expected_surface_token: str


SCHEMA_CASES = [
    SchemaCase(
        schema_file="agent_execution_skill.v1.schema.json",
        valid_fixture="agent_execution_skill.valid.json",
        invalid_fixture="agent_execution_skill.invalid.json",
        expected_surface_token="mcp_tools",
    ),
    SchemaCase(
        schema_file="multimodal_rag_bundle.v1.schema.json",
        valid_fixture="multimodal_rag_bundle.valid.json",
        invalid_fixture="multimodal_rag_bundle.invalid.json",
        expected_surface_token="vector_store_size",
    ),
    SchemaCase(
        schema_file="client_runtime_assignment_envelope.v1.schema.json",
        valid_fixture="client_runtime_assignment_envelope.valid.json",
        invalid_fixture="client_runtime_assignment_envelope.invalid.json",
        expected_surface_token="workers",
    ),
    SchemaCase(
        schema_file="vector_direction_token_bundle.v1.schema.json",
        valid_fixture="vector_direction_token_bundle.valid.json",
        invalid_fixture="vector_direction_token_bundle.invalid.json",
        expected_surface_token="token",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate mcp_3d_agent_execution.v1 spec pack")
    parser.add_argument(
        "--spec-dir",
        default=str(ROOT / "specs" / "mcp_3d_agent_execution.v1"),
        help="Spec pack directory",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail on any warning-level issue",
    )
    return parser.parse_args()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_hash(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def error_surface(error: ValidationError) -> str:
    path = ".".join(str(part) for part in error.path) or "<root>"
    return f"path={path} message={error.message}"


def load_rag_workflow_module() -> Any:
    module_path = ROOT / "ghost-void" / "orchestrator" / "multimodal_rag_workflow.py"
    spec = importlib.util.spec_from_file_location("ghost_void_multimodal_rag_workflow", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load multimodal rag workflow module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def assert_true(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_schema_fixtures(spec_dir: Path) -> dict[str, Any]:
    schemas_dir = spec_dir / "schemas"
    examples_dir = spec_dir / "examples"
    report: dict[str, Any] = {"schemas": []}

    for case in SCHEMA_CASES:
        schema_path = schemas_dir / case.schema_file
        valid_path = examples_dir / case.valid_fixture
        invalid_path = examples_dir / case.invalid_fixture

        schema = load_json(schema_path)
        valid_doc = load_json(valid_path)
        invalid_doc = load_json(invalid_path)
        validator = Draft7Validator(schema, format_checker=FormatChecker())

        valid_errors = sorted(validator.iter_errors(valid_doc), key=lambda e: e.path)
        if valid_errors:
            raise AssertionError(
                f"{case.valid_fixture} failed validation: {error_surface(valid_errors[0])}"
            )

        invalid_errors = sorted(validator.iter_errors(invalid_doc), key=lambda e: e.path)
        assert_true(bool(invalid_errors), f"{case.invalid_fixture} unexpectedly passed validation")

        first_surface = error_surface(invalid_errors[0])
        assert_true(
            case.expected_surface_token in first_surface,
            (
                f"{case.invalid_fixture} failed with unexpected surface. "
                f"expected token '{case.expected_surface_token}', got '{first_surface}'"
            ),
        )

        report["schemas"].append(
            {
                "schema": case.schema_file,
                "valid_fixture": case.valid_fixture,
                "invalid_fixture": case.invalid_fixture,
                "invalid_surface": first_surface,
            }
        )

    return report


def validate_determinism() -> dict[str, Any]:
    rag_workflow = load_rag_workflow_module()
    kwargs = {
        "prompt": "MCP 3D agent execution production hardening",
        "repository": "adaptco-main/A2A_MCP",
        "commit_sha": "ad854486a840079f438a361b8fa584586fd2122f",
        "actor": "codex",
        "cluster_count": 4,
    }

    worldline_a = build_worldline_block(**kwargs)
    worldline_b = build_worldline_block(**kwargs)
    assert_true(worldline_a == worldline_b, "worldline block is not deterministic")

    bundle_a = rag_workflow.build_workflow_bundle(worldline_a, top_k=3, min_similarity=0.10)
    bundle_b = rag_workflow.build_workflow_bundle(worldline_b, top_k=3, min_similarity=0.10)
    hash_a = canonical_hash(bundle_a)
    hash_b = canonical_hash(bundle_b)
    assert_true(hash_a == hash_b, "workflow bundle hash is not deterministic")

    node_ids = [node["node_id"] for node in bundle_a["token_reconstruction"]["nodes"]]
    assert_true(node_ids == EXPECTED_NODE_IDS, f"unexpected token reconstruction nodes: {node_ids}")
    assert_true(
        bundle_a["token_reconstruction"]["vector_store_size"] > 0,
        "vector_store_size must be > 0",
    )

    return {
        "bundle_hash": hash_a,
        "node_ids": node_ids,
        "vector_store_size": bundle_a["token_reconstruction"]["vector_store_size"],
    }


def extract_runtime_server_tools() -> set[str]:
    runtime_server = ROOT / "runtime_mcp_server.py"
    content = runtime_server.read_text(encoding="utf-8")
    return set(re.findall(r"mcp\.tool\(\)\(([a-zA-Z0-9_]+)\)", content))


def validate_mcp_compatibility(spec_dir: Path) -> dict[str, Any]:
    examples_dir = spec_dir / "examples"
    skill_doc = load_json(examples_dir / "agent_execution_skill.valid.json")
    assignment_env = load_json(examples_dir / "client_runtime_assignment_envelope.valid.json")

    chain = skill_doc["deterministic_chain"]
    assert_true(chain == EXPECTED_CHAIN, f"unexpected deterministic chain ordering: {chain}")

    skill_tools = set(skill_doc["mcp_tools"])
    assignment_tools = set(assignment_env["runtime_assignment"]["mcp"]["runtime_tools"])
    runtime_server_tools = extract_runtime_server_tools()

    assert_true(REQUIRED_RUNTIME_TOOLS.issubset(skill_tools), "skill contract missing required tools")
    assert_true(REQUIRED_RUNTIME_TOOLS.issubset(assignment_tools), "runtime assignment missing required tools")
    assert_true(REQUIRED_RUNTIME_TOOLS.issubset(runtime_server_tools), "runtime server missing required tools")

    RuntimeAssignmentV1.model_validate(assignment_env["runtime_assignment"])

    worker_backends = {
        worker["render_backend"] for worker in assignment_env["runtime_assignment"]["workers"]
    }
    assert_true({"unity", "threejs"}.issubset(worker_backends), "dual runtime worker coverage is incomplete")

    return {
        "chain": chain,
        "runtime_tools": sorted(REQUIRED_RUNTIME_TOOLS),
        "runtime_server_tools": sorted(runtime_server_tools),
    }


def validate_token_lineage(spec_dir: Path) -> dict[str, Any]:
    examples_dir = spec_dir / "examples"
    token_bundle = load_json(examples_dir / "vector_direction_token_bundle.valid.json")
    events = token_bundle["token_events"]

    assert_true(len(events) > 0, "token_events must not be empty")
    assert_true(
        token_bundle["lineage"]["token_event_count"] == len(events),
        "lineage.token_event_count mismatch",
    )

    call_ids = {event["call_id"] for event in events}
    assert_true(len(call_ids) == 1, "all token events must share one call_id")

    seqs = [event["seq"] for event in events]
    assert_true(seqs == list(range(len(events))), f"token event sequence must be contiguous from 0: {seqs}")

    previous = events[0]["call_id"]
    for event in events:
        expected_token_hash = sha256_text(event["token"])
        assert_true(
            expected_token_hash == event["token_hash"],
            f"token_hash mismatch at seq {event['seq']}",
        )
        expected_cumulative = sha256_text(previous + event["token_hash"])
        assert_true(
            expected_cumulative == event["cumulative_hash"],
            f"cumulative_hash mismatch at seq {event['seq']}",
        )
        previous = event["cumulative_hash"]

    final_hash = token_bundle["lineage"]["final_cumulative_hash"]
    assert_true(final_hash == events[-1]["cumulative_hash"], "lineage.final_cumulative_hash mismatch")

    return {
        "call_id": events[0]["call_id"],
        "token_event_count": len(events),
        "final_cumulative_hash": final_hash,
    }


def main() -> int:
    args = parse_args()
    spec_dir = Path(args.spec_dir).resolve()

    report = {
        "spec_dir": str(spec_dir),
        "strict": bool(args.strict),
    }

    report["schema_validation"] = validate_schema_fixtures(spec_dir)
    report["determinism"] = validate_determinism()
    report["mcp_compatibility"] = validate_mcp_compatibility(spec_dir)
    report["token_lineage"] = validate_token_lineage(spec_dir)

    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, sort_keys=True))
        raise SystemExit(1)

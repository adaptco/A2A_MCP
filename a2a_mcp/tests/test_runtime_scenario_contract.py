import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from runtime_scenario_service import RuntimeScenarioService
from schemas.runtime_scenario import RuntimeScenarioEnvelope


def test_runtime_scenario_schema_lists_required_fields() -> None:
    schema_path = Path("schemas/runtime_scenario_envelope.schema.json")
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    required = set(schema["required"])
    assert {
        "schema_version",
        "tenant_id",
        "execution_id",
        "runtime_state",
        "scenario_trace",
        "retrieval_context",
        "lora_candidates",
        "embedding_dim",
        "hash_prev",
        "hash_current",
        "timestamp",
    }.issubset(required)


def test_runtime_scenario_envelope_accepts_valid_payload() -> None:
    envelope = RuntimeScenarioEnvelope(
        schema_version="1.0",
        tenant_id="tenant-a",
        execution_id="exec-1",
        runtime_state={"state": "ok"},
        scenario_trace=[],
        retrieval_context={},
        lora_candidates=[],
        embedding_dim=1536,
        hash_prev="",
        hash_current="abc123",
        timestamp="2026-02-19T00:00:00Z",
    )
    assert envelope.embedding_dim == 1536
    assert envelope.tenant_id == "tenant-a"


def test_runtime_scenario_envelope_rejects_invalid_embedding_dim() -> None:
    with pytest.raises(ValidationError):
        RuntimeScenarioEnvelope(
            schema_version="1.0",
            tenant_id="tenant-a",
            execution_id="exec-1",
            runtime_state={},
            scenario_trace=[],
            retrieval_context={},
            lora_candidates=[],
            embedding_dim=1024,  # type: ignore[arg-type]
            hash_prev="",
            hash_current="abc123",
            timestamp="2026-02-19T00:00:00Z",
        )


def test_runtime_hashing_is_deterministic_for_identical_payload() -> None:
    payload = {
        "schema_version": "1.0",
        "tenant_id": "tenant-a",
        "execution_id": "exec-1",
        "runtime_state": {"x": 1},
    }
    h1 = RuntimeScenarioService.hash_payload("", payload)
    h2 = RuntimeScenarioService.hash_payload("", payload)
    assert h1 == h2

from __future__ import annotations

from fastapi.testclient import TestClient

from app.multi_client_api import app, get_router, get_runtime_service
from orchestrator.settlement import Event


def _register(client: TestClient, api_key: str = "scenario-key") -> str:
    response = client.post("/mcp/register", params={"api_key": api_key})
    assert response.status_code == 200
    return response.json()["client_key"]


def _set_baseline(client: TestClient, client_key: str, tokens: list[float]) -> None:
    response = client.post(f"/mcp/{client_key}/baseline", json={"tokens": tokens})
    assert response.status_code == 200


def _build_scenario(client: TestClient, client_key: str, tokens: list[float]) -> dict:
    response = client.post(
        f"/a2a/runtime/{client_key}/scenario",
        json={
            "tokens": tokens,
            "runtime_hints": {
                "preset": "simulation",
                "agent_name": "TestAgent",
                "action": "hold safe lane",
            },
        },
    )
    assert response.status_code == 200
    return response.json()


def test_a2a_runtime_pipeline_happy_path() -> None:
    get_router.cache_clear()
    get_runtime_service.cache_clear()
    client = TestClient(app)

    key = _register(client)
    _set_baseline(client, key, [0.0] * 16)
    envelope = _build_scenario(client, key, [0.0] * 16)

    assert envelope["embedding_dim"] == 1536
    assert envelope["execution_id"]
    assert envelope["hash_current"]
    assert envelope["projection_metadata"]["source_dim"] == 16

    execution_id = envelope["execution_id"]

    rag_1 = client.post(
        f"/a2a/scenario/{execution_id}/rag-context",
        json={"top_k": 3},
    )
    assert rag_1.status_code == 200
    rag_payload_1 = rag_1.json()
    assert len(rag_payload_1["retrieval_context"]["chunks"]) == 3

    rag_2 = client.post(
        f"/a2a/scenario/{execution_id}/rag-context",
        json={"top_k": 3},
    )
    assert rag_2.status_code == 200
    rag_payload_2 = rag_2.json()
    chunk_ids_1 = [chunk["chunk_id"] for chunk in rag_payload_1["retrieval_context"]["chunks"]]
    chunk_ids_2 = [chunk["chunk_id"] for chunk in rag_payload_2["retrieval_context"]["chunks"]]
    assert chunk_ids_1 == chunk_ids_2

    lora = client.post(
        f"/a2a/scenario/{execution_id}/lora-dataset",
        json={"pvalue_threshold": 0.1},
    )
    assert lora.status_code == 200
    lora_payload = lora.json()
    assert lora_payload["dataset_commit"]
    assert lora_payload["lora_dataset"]
    assert all("provenance_hash" in row for row in lora_payload["lora_dataset"])

    verification = client.get(f"/a2a/executions/{execution_id}/verify")
    assert verification.status_code == 200
    assert verification.json()["valid"] is True


def test_mcp_stream_compatibility_routes_to_scenario_pipeline() -> None:
    get_router.cache_clear()
    get_runtime_service.cache_clear()
    client = TestClient(app)

    key = _register(client, api_key="compat-key")
    _set_baseline(client, key, [0.0] * 16)

    response = client.post(
        f"/mcp/{key}/stream",
        json={"tokens": [0.0] * 16},
    )
    assert response.status_code == 200
    payload = response.json()
    assert "execution_id" in payload
    assert "envelope_hash" in payload
    assert payload["embedding_dim"] == 1536


def test_lora_dataset_blocks_on_drift_gate_failure() -> None:
    get_router.cache_clear()
    get_runtime_service.cache_clear()
    client = TestClient(app)

    key = _register(client, api_key="drift-key")
    _set_baseline(client, key, [0.0] * 16)
    envelope = _build_scenario(client, key, [0.0] * 16)
    execution_id = envelope["execution_id"]

    client.post(f"/a2a/scenario/{execution_id}/rag-context", json={"top_k": 3})

    response = client.post(
        f"/a2a/scenario/{execution_id}/lora-dataset",
        json={
            "pvalue_threshold": 0.999999,
            "candidate_tokens": [10.0] * 16,
        },
    )
    assert response.status_code == 409
    assert "Drift gate failed" in response.json()["detail"]


def test_verify_endpoint_returns_409_on_tampered_execution() -> None:
    get_router.cache_clear()
    get_runtime_service.cache_clear()
    client = TestClient(app)

    key = _register(client, api_key="tamper-key")
    _set_baseline(client, key, [0.0] * 16)
    envelope = _build_scenario(client, key, [0.0] * 16)
    execution_id = envelope["execution_id"]

    service = get_runtime_service()
    record = service._records[execution_id]  # pylint: disable=protected-access
    last = record.events[-1]
    record.events[-1] = Event(
        id=last.id,
        tenant_id=last.tenant_id,
        execution_id=last.execution_id,
        state=last.state,
        payload=last.payload,
        hash_prev=last.hash_prev,
        hash_current="deadbeef",
        created_at=last.created_at,
    )

    response = client.get(f"/a2a/executions/{execution_id}/verify")
    assert response.status_code == 409
    assert response.json()["detail"]["valid"] is False

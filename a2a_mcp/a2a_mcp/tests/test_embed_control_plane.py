from __future__ import annotations

import copy

import pytest

from embed_control_plane import (
    ControlPlaneError,
    DISPATCH_GUARD_TOKEN,
    embed_dispatch_batch,
    embed_submit,
    get_receipt,
    reset_state,
    route_a2a_intent,
)


def _doc_ref() -> dict:
    return {
        "uri": "memory://doc-1",
        "content": "alpha beta gamma delta epsilon zeta eta theta",
        "meta": {"source": "unit"},
    }


def test_deterministic_job_id_and_stable_receipts():
    reset_state()
    payload = {
        "doc_ref": _doc_ref(),
        "canonicalizer_id": "docling.c14n.v1",
        "model_id": "mini-embed-v1",
    }

    first = embed_submit(**payload)
    second = embed_submit(**payload)

    assert first["job_id"] == second["job_id"]
    assert second["already_exists"] is True

    first_receipt = get_receipt(first["receipt_ref"])
    second_receipt = get_receipt(second["receipt_ref"])
    assert first_receipt["hashed_surface"]["job_id"] == second_receipt["hashed_surface"]["job_id"]
    assert first_receipt["hashed_surface"]["manifest_hash"] == second_receipt["hashed_surface"]["manifest_hash"]


def test_lock_free_idempotence_on_dispatch_batch():
    reset_state()
    submit = embed_submit(_doc_ref(), "docling.c14n.v1", "mini-embed-v1")
    batch = submit["plan"]["batches"][0]

    chunks = [
        {"chunk_hash": c_hash, "text": f"chunk-{idx}", "job_id": submit["job_id"]}
        for idx, c_hash in enumerate(batch["chunk_hashes"])
    ]

    first = embed_dispatch_batch(
        batch_id=batch["batch_id"],
        chunks=chunks,
        model_id="mini-embed-v1",
        seed_ref="seed-0",
        guard_token=DISPATCH_GUARD_TOKEN,
    )
    second = embed_dispatch_batch(
        batch_id=batch["batch_id"],
        chunks=copy.deepcopy(chunks),
        model_id="mini-embed-v1",
        seed_ref="seed-0",
        guard_token=DISPATCH_GUARD_TOKEN,
    )

    assert first["written"] > 0
    assert second["written"] == 0
    assert second["skipped"] == len(chunks)

    first_receipt = get_receipt(first["receipt_ref"])
    second_receipt = get_receipt(second["receipt_ref"])
    assert first_receipt["hashed_surface"]["artifact_hashes"] == second_receipt["hashed_surface"]["artifact_hashes"]


def test_router_fail_closed_on_unbacked_or_unpinned_claims():
    reset_state()

    with pytest.raises(ControlPlaneError) as model_forbidden:
        route_a2a_intent(
            {
                "intent": "EMBED_DOCUMENT",
                "payload": {
                    "doc_ref": _doc_ref(),
                    "canonicalizer_id": "docling.c14n.v1",
                    "model_id": "forbidden-model",
                },
            }
        )
    assert model_forbidden.value.code == "ERR.MODEL_FORBIDDEN"

    with pytest.raises(ControlPlaneError) as canon_unpinned:
        route_a2a_intent(
            {
                "intent": "EMBED_DOCUMENT",
                "payload": {
                    "doc_ref": _doc_ref(),
                    "canonicalizer_id": "docling.experimental",
                    "model_id": "mini-embed-v1",
                },
            }
        )
    assert canon_unpinned.value.code == "ERR.CANONICALIZER_UNPINNED"

    with pytest.raises(ControlPlaneError) as unbacked:
        route_a2a_intent(
            {
                "intent": "EMBED_DOCUMENT",
                "payload": {
                    "doc_ref": _doc_ref(),
                    "canonicalizer_id": "docling.c14n.v1",
                    "model_id": "mini-embed-v1",
                    "estimated_latency_ms": 123,
                },
            }
        )
    assert unbacked.value.code == "ERR.UNBACKED_METADATA"


def test_replay_fidelity_same_chunk_hashes_artifacts_and_chain_tip():
    payload = {
        "doc_ref": _doc_ref(),
        "canonicalizer_id": "docling.c14n.v1",
        "model_id": "mini-embed-v1",
    }

    reset_state()
    run1_submit = embed_submit(**payload)
    batch1 = run1_submit["plan"]["batches"][0]
    chunks1 = [
        {"chunk_hash": c_hash, "text": f"chunk-{idx}", "job_id": run1_submit["job_id"]}
        for idx, c_hash in enumerate(batch1["chunk_hashes"])
    ]
    run1_dispatch = embed_dispatch_batch(
        batch_id=batch1["batch_id"],
        chunks=chunks1,
        model_id="mini-embed-v1",
        seed_ref="seed-0",
        guard_token=DISPATCH_GUARD_TOKEN,
    )
    run1_chain_tip = get_receipt(run1_dispatch["receipt_ref"])["receipt_hash"]

    reset_state()
    run2_submit = embed_submit(**payload)
    batch2 = run2_submit["plan"]["batches"][0]
    chunks2 = [
        {"chunk_hash": c_hash, "text": f"chunk-{idx}", "job_id": run2_submit["job_id"]}
        for idx, c_hash in enumerate(batch2["chunk_hashes"])
    ]
    run2_dispatch = embed_dispatch_batch(
        batch_id=batch2["batch_id"],
        chunks=chunks2,
        model_id="mini-embed-v1",
        seed_ref="seed-0",
        guard_token=DISPATCH_GUARD_TOKEN,
    )
    run2_chain_tip = get_receipt(run2_dispatch["receipt_ref"])["receipt_hash"]

    assert run1_submit["job_id"] == run2_submit["job_id"]
    assert batch1["chunk_hashes"] == batch2["chunk_hashes"]
    assert run1_chain_tip == run2_chain_tip

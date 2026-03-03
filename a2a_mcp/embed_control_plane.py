"""Deterministic A2A→MCP embedding control-plane bindings.

This module provides a minimal corridor-grade surface:
- MCP-like tool functions for embed.submit/status/lookup/dispatch_batch
- A2A intent router with fail-closed governance checks
- Receipt chaining with hashed vs observed surfaces
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Dict, List

SEAL_PHRASE = "Canonical truth, attested and replayable."
ALLOWED_MODEL_IDS = {"mini-embed-v1", "nomic-embed-text-v1.5"}
PINNED_CANONICALIZER_IDS = {"docling.c14n.v1"}
DISPATCH_GUARD_TOKEN = "worker-guard-v1"


class ControlPlaneError(ValueError):
    """Typed error for explicit refusal grammar."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class Receipt:
    receipt_ref: str
    receipt_hash: str


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_obj(value: Any) -> str:
    return _sha256_bytes(_canonical_bytes(value))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_JOBS: Dict[str, Dict[str, Any]] = {}
_ARTIFACTS: Dict[str, Dict[str, Any]] = {}
_RECEIPTS: Dict[str, Dict[str, Any]] = {}
_RECEIPT_TIP = ""


def reset_state() -> None:
    _JOBS.clear()
    _ARTIFACTS.clear()
    _RECEIPTS.clear()
    global _RECEIPT_TIP
    _RECEIPT_TIP = ""


def _emit_receipt(stage: str, hashed_surface: Dict[str, Any], observed_surface: Dict[str, Any] | None = None) -> Receipt:
    global _RECEIPT_TIP
    observed = observed_surface or {}
    envelope = {
        "stage": stage,
        "hashed_surface": hashed_surface,
        "prev_hash": _RECEIPT_TIP,
        "seal_phrase": SEAL_PHRASE,
    }
    receipt_hash = _sha256_obj(envelope)
    receipt_ref = f"receipt://{receipt_hash}"
    _RECEIPTS[receipt_ref] = {
        "receipt_ref": receipt_ref,
        "receipt_hash": receipt_hash,
        "stage": stage,
        "hashed_surface": hashed_surface,
        "observed_surface": observed,
        "prev_hash": _RECEIPT_TIP,
        "seal_phrase": SEAL_PHRASE,
        "timestamp": _now_iso(),
    }
    _RECEIPT_TIP = receipt_hash
    return Receipt(receipt_ref=receipt_ref, receipt_hash=receipt_hash)


def _validate_model_and_canonicalizer(model_id: str, canonicalizer_id: str) -> None:
    if model_id not in ALLOWED_MODEL_IDS:
        raise ControlPlaneError("ERR.MODEL_FORBIDDEN", f"model_id '{model_id}' is not allowlisted")
    if canonicalizer_id not in PINNED_CANONICALIZER_IDS:
        raise ControlPlaneError("ERR.CANONICALIZER_UNPINNED", f"canonicalizer_id '{canonicalizer_id}' is not pinned")


def _canonical_manifest(doc_ref: Any) -> Dict[str, Any]:
    if isinstance(doc_ref, dict):
        return doc_ref
    return {"ref": str(doc_ref)}


def _chunk_content(doc_ref: Any, chunk_size: int = 32) -> List[Dict[str, Any]]:
    content = ""
    if isinstance(doc_ref, dict):
        content = str(doc_ref.get("content", ""))
    words = content.split()
    chunks: List[Dict[str, Any]] = []
    if not words:
        # Keep deterministic behavior for empty documents.
        empty_hash = _sha256_obj({"chunk_index": 0, "text": ""})
        return [{"chunk_index": 0, "text": "", "chunk_hash": empty_hash}]

    for index in range(0, len(words), chunk_size):
        chunk_index = index // chunk_size
        text = " ".join(words[index : index + chunk_size])
        chunk_hash = _sha256_obj({"chunk_index": chunk_index, "text": text})
        chunks.append({"chunk_index": chunk_index, "text": text, "chunk_hash": chunk_hash})
    return chunks


def _deterministic_embedding(chunk_text: str, model_id: str, width: int = 8) -> List[float]:
    digest = hashlib.sha256(f"{model_id}::{chunk_text}".encode("utf-8")).digest()
    return [round(int(digest[i]) / 255.0, 6) for i in range(width)]


def embed_submit(doc_ref: Any, canonicalizer_id: str, model_id: str, shard_key: str = "") -> Dict[str, Any]:
    _validate_model_and_canonicalizer(model_id, canonicalizer_id)

    manifest = _canonical_manifest(doc_ref)
    manifest_bytes = _canonical_bytes(manifest)
    manifest_hash = _sha256_bytes(manifest_bytes)
    job_id = _sha256_bytes(manifest_bytes + model_id.encode("utf-8") + canonicalizer_id.encode("utf-8"))

    already_exists = job_id in _JOBS
    if not already_exists:
        chunks = _chunk_content(doc_ref)
        batch_id = _sha256_obj({"job_id": job_id, "chunk_hashes": [c["chunk_hash"] for c in chunks]})
        plan = {
            "shards": [{"shard_id": shard_key or "default", "batch_ids": [batch_id]}],
            "batches": [{"batch_id": batch_id, "chunk_count": len(chunks), "chunk_hashes": [c["chunk_hash"] for c in chunks]}],
        }
        _JOBS[job_id] = {
            "job_id": job_id,
            "state": "queued",
            "model_id": model_id,
            "canonicalizer_id": canonicalizer_id,
            "manifest": manifest,
            "manifest_hash": manifest_hash,
            "chunks": chunks,
            "plan": plan,
            "created_at": _now_iso(),
        }
    else:
        plan = _JOBS[job_id]["plan"]

    receipt = _emit_receipt(
        "embed.submit",
        {
            "job_id": job_id,
            "manifest_hash": manifest_hash,
            "model_id": model_id,
            "canonicalizer_id": canonicalizer_id,
            "already_exists": already_exists,
        },
        {"timestamp": _now_iso(), "queue_latency_ms": 0},
    )

    return {
        "job_id": job_id,
        "already_exists": already_exists,
        "plan": plan,
        "receipt_ref": receipt.receipt_ref,
    }


def embed_status(job_id: str) -> Dict[str, Any]:
    job = _JOBS.get(job_id)
    if not job:
        return {"state": "failed", "counts": {"batches": 0, "artifacts": 0}, "receipt_chain_tip": _RECEIPT_TIP}

    artifact_count = sum(1 for value in _ARTIFACTS.values() if value["job_id"] == job_id)
    counts = {
        "batches": len(job["plan"]["batches"]),
        "chunks": len(job["chunks"]),
        "artifacts": artifact_count,
    }
    if artifact_count == len(job["chunks"]):
        job["state"] = "complete"
    elif artifact_count > 0:
        job["state"] = "running"

    _emit_receipt(
        "embed.status",
        {"job_id": job_id, "state": job["state"], "counts": counts},
        {"timestamp": _now_iso(), "memory_mb": 0},
    )
    return {"state": job["state"], "counts": counts, "receipt_chain_tip": _RECEIPT_TIP}


def embed_lookup(chunk_hash: str, model_id: str) -> Dict[str, Any]:
    artifact_id = _sha256_obj({"chunk_hash": chunk_hash, "model_id": model_id})
    artifact = _ARTIFACTS.get(artifact_id)
    if artifact is None:
        return {"found": False, "artifact_ref": "", "artifact_hash": ""}

    artifact_hash = _sha256_obj(artifact)
    return {
        "found": True,
        "artifact_ref": f"artifact://{artifact_id}",
        "artifact_hash": artifact_hash,
    }


def embed_dispatch_batch(batch_id: str, chunks: List[Dict[str, Any]], model_id: str, seed_ref: str, guard_token: str = "") -> Dict[str, Any]:
    if guard_token != DISPATCH_GUARD_TOKEN:
        raise ControlPlaneError("ERR.DISPATCH_FORBIDDEN", "dispatch batch is worker-only")

    written = 0
    skipped = 0
    receipt_artifact_hashes: List[str] = []

    for chunk in chunks:
        chunk_hash = chunk["chunk_hash"]
        artifact_id = _sha256_obj({"chunk_hash": chunk_hash, "model_id": model_id})
        if artifact_id in _ARTIFACTS:
            skipped += 1
            receipt_artifact_hashes.append(artifact_id)
            continue

        artifact = {
            "artifact_id": artifact_id,
            "job_id": chunk.get("job_id", ""),
            "chunk_hash": chunk_hash,
            "model_id": model_id,
            "seed_ref": seed_ref,
            "embedding": _deterministic_embedding(chunk.get("text", ""), model_id),
            "worker_version": "embed-worker.v1",
            "canonicalization_spec": "docling.c14n.v1",
            "timestamp": _now_iso(),
        }
        _ARTIFACTS[artifact_id] = artifact
        written += 1
        receipt_artifact_hashes.append(artifact_id)

    receipt = _emit_receipt(
        "embed.dispatch_batch",
        {
            "batch_id": batch_id,
            "model_id": model_id,
            "seed_ref": seed_ref,
            "written": written,
            "skipped": skipped,
            "artifact_hashes": sorted(receipt_artifact_hashes),
        },
        {"timestamp": _now_iso(), "retry_count": 0},
    )

    return {"written": written, "skipped": skipped, "receipt_ref": receipt.receipt_ref}


def get_receipt(receipt_ref: str) -> Dict[str, Any]:
    receipt = _RECEIPTS.get(receipt_ref)
    if receipt is None:
        raise ControlPlaneError("ERR.RECEIPT_NOT_FOUND", f"Unknown receipt_ref '{receipt_ref}'")

    envelope = {
        "stage": receipt["stage"],
        "hashed_surface": receipt["hashed_surface"],
        "prev_hash": receipt["prev_hash"],
        "seal_phrase": receipt["seal_phrase"],
    }
    recomputed = _sha256_obj(envelope)
    if recomputed != receipt["receipt_hash"]:
        raise ControlPlaneError("ERR.RECEIPT_TAMPERED", "Receipt hash mismatch")
    return receipt


def route_a2a_intent(message: Dict[str, Any]) -> Dict[str, Any]:
    intent = message.get("intent", "")
    payload = message.get("payload", {})
    if not isinstance(payload, dict):
        raise ControlPlaneError("ERR.INVALID_PAYLOAD", "payload must be an object")

    if intent == "EMBED_DOCUMENT":
        allowed = {"doc_ref", "canonicalizer_id", "model_id", "shard_key"}
        unknown = set(payload.keys()) - allowed
        if unknown:
            raise ControlPlaneError("ERR.UNBACKED_METADATA", f"Unsupported fields: {sorted(unknown)}")
        return {"tool": "embed.submit", "result": embed_submit(**payload)}

    if intent == "EMBED_STATUS":
        allowed = {"job_id"}
        unknown = set(payload.keys()) - allowed
        if unknown:
            raise ControlPlaneError("ERR.UNBACKED_METADATA", f"Unsupported fields: {sorted(unknown)}")
        return {"tool": "embed.status", "result": embed_status(**payload)}

    if intent == "FETCH_EMBEDDING":
        allowed = {"chunk_hash", "model_id"}
        unknown = set(payload.keys()) - allowed
        if unknown:
            raise ControlPlaneError("ERR.UNBACKED_METADATA", f"Unsupported fields: {sorted(unknown)}")
        return {"tool": "embed.lookup", "result": embed_lookup(**payload)}

    raise ControlPlaneError("ERR.UNKNOWN_INTENT", f"Unsupported intent '{intent}'")

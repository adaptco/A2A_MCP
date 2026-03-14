"""Contracts and gate validators for the sovereign replay corridor."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ValidationError, validator

PSP_DOMAIN_TAG = b"PSP.MerkleRoot.v1"
PSP_ALG_DESCRIPTOR = "sha256(domain0_left_right)_odd_selfdup_leaves_tickhash32"
HASH_REGEX = re.compile(r"^sha256:[0-9a-f]{64}$")


class ReplayReceipt(BaseModel):
    tick: int
    tick_hash: str
    prev_tick_hash: Optional[str] = None


class ReplayCapsule(BaseModel):
    world_id: str
    capsule_digest: str
    receipts: List[ReplayReceipt]

    class Config:
        extra = "allow"


class ExtractorAttestation(BaseModel):
    extractor_version: str
    timestamp_utc_ms: int


class InvariantSet(BaseModel):
    world_id: str
    capsule_digest: str
    merkle_root: str
    tick_count: int
    invariants: Dict[str, Any] = Field(default_factory=dict)
    attestation: ExtractorAttestation


class KernelToken(BaseModel):
    world_id: str
    capsule_digest: str
    merkle_root: str
    tick_count: int
    psp_alg: str
    created_at_utc: str


class BindingLiterals(BaseModel):
    domain_tag: str = "PSP.MerkleRoot.v1"
    leaf_order: str = "ascending_tick"
    leaf_content: str = "tick_hash_sha256_bytes"
    merkle_rule: str = "H(domain_tag||0x00||left32||right32)"
    odd_leaf_rule: str = "odd_selfdup"


class CIEV2Plug(BaseModel):
    world_id: str
    capsule_digest: str
    baseline_merkle_root: str
    tick_count: int
    extractor_version: str
    kernel_token: KernelToken
    invariant_set: InvariantSet
    binding_literals: BindingLiterals = Field(default_factory=BindingLiterals)
    capsule_ref: Optional[str] = None
    engine_hash: Optional[str] = None


class IngestResult(BaseModel):
    status: str
    plug_digest: Optional[str] = None
    errors: List[str] = Field(default_factory=list)


class AgentReceipt(BaseModel):
    schema_version: str = "AgentReceipt.v1"
    receipt_id: str
    timestamp_utc_ms: int
    tick: int
    prev_mode: str
    next_mode: str
    action_profile: str
    cie_verdict: str
    reason_code: Optional[str] = None
    observed_tick_hash: Optional[str] = None
    psp_merkle_root: Optional[str] = None
    invariant_set_digest: Optional[str] = None
    extractor_version: Optional[str] = None
    receipt_digest: str

    @validator("timestamp_utc_ms", "tick")
    def ensure_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("timestamp_utc_ms and tick must be non-negative")
        return value


@dataclass(frozen=True)
class AgentReceiptContext:
    tick: int
    plug_baseline_merkle_root: str
    plug_digest: Optional[str] = None


@dataclass(frozen=True)
class AgentReceiptObservation:
    observed_tick_hash: Optional[str]
    psp_merkle_root: Optional[str]
    invariant_set_digest: Optional[str]
    extractor_version: Optional[str]


@dataclass(frozen=True)
class AgentReceiptDecision:
    prev_mode: str
    next_mode: str
    action_profile: str
    cie_verdict: str
    reason_code: Optional[str] = None


class GateError(ValueError):
    """Raised when a gate verification fails."""


def stable_stringify(data: Any) -> str:
    """Serialize data deterministically for digest surfaces."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _normalize_hash(value: str) -> bytes:
    if value.startswith("sha256:"):
        hex_value = value.split(":", 1)[1]
    else:
        hex_value = value
    if len(hex_value) != 64 or not all(ch in "0123456789abcdef" for ch in hex_value.lower()):
        raise GateError(f"tick_hash must be 32-byte hex or sha256: prefix, got '{value}'")
    return bytes.fromhex(hex_value)


def _hash_pair(left: bytes, right: bytes) -> bytes:
    payload = PSP_DOMAIN_TAG + b"\x00" + left + right
    return hashlib.sha256(payload).digest()


def _psp_merkle_root(receipts: List[ReplayReceipt]) -> str:
    if not receipts:
        return f"sha256:{sha256_hex(b'')}"
    leaves = [_normalize_hash(receipt.tick_hash) for receipt in receipts]
    level = leaves[:]
    while len(level) > 1:
        if len(level) % 2 == 1:
            level.append(level[-1])
        level = [_hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return f"sha256:{level[0].hex()}"


def extract_invariants(
    capsule: ReplayCapsule,
    extractor_version: str,
    timestamp_utc_ms: Optional[int] = None,
) -> InvariantSet:
    """Gate: ReplayCapsule.v1 -> InvariantSet.v1 (EXTRACT_INVARIANTS)."""
    if not capsule.receipts:
        raise GateError("ReplayCapsule must include at least one receipt")
    sorted_ticks = [receipt.tick for receipt in capsule.receipts]
    if sorted_ticks != sorted(sorted_ticks):
        raise GateError("Receipts must be sorted by ascending tick")
    if len(sorted_ticks) != len(set(sorted_ticks)):
        raise GateError("Receipts must not include duplicate ticks")
    for index, receipt in enumerate(capsule.receipts):
        if index == 0:
            continue
        prev = capsule.receipts[index - 1]
        if receipt.prev_tick_hash != prev.tick_hash:
            raise GateError("Receipt chain integrity failure: prev_tick_hash mismatch")
    merkle_root = _psp_merkle_root(capsule.receipts)
    attestation = ExtractorAttestation(
        extractor_version=extractor_version,
        timestamp_utc_ms=timestamp_utc_ms
        if timestamp_utc_ms is not None
        else int(datetime.now(tz=timezone.utc).timestamp() * 1000),
    )
    return InvariantSet(
        world_id=capsule.world_id,
        capsule_digest=capsule.capsule_digest,
        merkle_root=merkle_root,
        tick_count=len(capsule.receipts),
        invariants={},
        attestation=attestation,
    )


def fossilize_token(invariant_set: InvariantSet, created_at_utc: Optional[str] = None) -> KernelToken:
    """Gate: InvariantSet.v1 -> KernelToken.v1 (FOSSILIZE_TOKEN)."""
    if not HASH_REGEX.match(invariant_set.capsule_digest):
        raise GateError("capsule_digest must match sha256:<hex>")
    if not HASH_REGEX.match(invariant_set.merkle_root):
        raise GateError("merkle_root must match sha256:<hex>")
    if invariant_set.tick_count < 0:
        raise GateError("tick_count must be non-negative")
    created_at = created_at_utc or datetime.now(tz=timezone.utc).isoformat()
    return KernelToken(
        world_id=invariant_set.world_id,
        capsule_digest=invariant_set.capsule_digest,
        merkle_root=invariant_set.merkle_root,
        tick_count=invariant_set.tick_count,
        psp_alg=PSP_ALG_DESCRIPTOR,
        created_at_utc=created_at,
    )


def assemble_plug(
    kernel_token: KernelToken,
    invariant_set: InvariantSet,
    extractor_version: str,
    capsule_ref: Optional[str] = None,
    engine_hash: Optional[str] = None,
) -> CIEV2Plug:
    """Gate: KernelToken.v1 (+InvariantSet.v1) -> CIE-V2 plug (ASSEMBLE_PLUG)."""
    if kernel_token.world_id != invariant_set.world_id:
        raise GateError("world_id mismatch between kernel token and invariant set")
    if kernel_token.capsule_digest != invariant_set.capsule_digest:
        raise GateError("capsule_digest mismatch between kernel token and invariant set")
    if kernel_token.merkle_root != invariant_set.merkle_root:
        raise GateError("merkle_root mismatch between kernel token and invariant set")
    if kernel_token.tick_count != invariant_set.tick_count:
        raise GateError("tick_count mismatch between kernel token and invariant set")
    if invariant_set.attestation.extractor_version != extractor_version:
        raise GateError("extractor_version mismatch between invariant set and plug")
    return CIEV2Plug(
        world_id=kernel_token.world_id,
        capsule_digest=kernel_token.capsule_digest,
        baseline_merkle_root=kernel_token.merkle_root,
        tick_count=kernel_token.tick_count,
        extractor_version=extractor_version,
        kernel_token=kernel_token,
        invariant_set=invariant_set,
        capsule_ref=capsule_ref,
        engine_hash=engine_hash,
    )


def ingest_plug(raw: Dict[str, Any]) -> IngestResult:
    """Gate: CIE-V2 plug -> Agent State Machine (INGEST)."""
    try:
        plug = CIEV2Plug.parse_obj(raw)
    except ValidationError as exc:
        return IngestResult(status="Quarantine", errors=[str(exc)])
    errors = []
    if plug.world_id != plug.kernel_token.world_id or plug.world_id != plug.invariant_set.world_id:
        errors.append("world_id binding mismatch")
    if (
        plug.capsule_digest != plug.kernel_token.capsule_digest
        or plug.capsule_digest != plug.invariant_set.capsule_digest
    ):
        errors.append("capsule_digest binding mismatch")
    if (
        plug.baseline_merkle_root != plug.kernel_token.merkle_root
        or plug.baseline_merkle_root != plug.invariant_set.merkle_root
    ):
        errors.append("baseline_merkle_root binding mismatch")
    if plug.kernel_token.tick_count != plug.invariant_set.tick_count:
        errors.append("tick_count binding mismatch")
    if plug.invariant_set.attestation.extractor_version != plug.extractor_version:
        errors.append("extractor_version binding mismatch")
    if errors:
        return IngestResult(status="Quarantine", errors=errors)
    plug_digest = f"sha256:{sha256_hex(stable_stringify(plug.dict()).encode())}"
    return IngestResult(status="Loaded", plug_digest=plug_digest)


def make_agent_receipt(
    context: AgentReceiptContext,
    observation: AgentReceiptObservation,
    decision: AgentReceiptDecision,
    receipt_id: str,
    timestamp_utc_ms: Optional[int] = None,
) -> AgentReceipt:
    """Gate: Agent State Machine -> AgentReceipt.v1 (ATTEST)."""
    timestamp = timestamp_utc_ms or int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    if observation.psp_merkle_root is None:
        if decision.cie_verdict not in {"INDETERMINATE", "FAIL"}:
            raise GateError("PSP not computed requires INDETERMINATE or FAIL verdict")
        if decision.reason_code is None:
            raise GateError("PSP not computed requires a reason_code")
    elif observation.psp_merkle_root != context.plug_baseline_merkle_root:
        raise GateError("Observed PSP merkle root does not match plug baseline")
    receipt_payload = {
        "schema_version": "AgentReceipt.v1",
        "receipt_id": receipt_id,
        "timestamp_utc_ms": timestamp,
        "tick": context.tick,
        "prev_mode": decision.prev_mode,
        "next_mode": decision.next_mode,
        "action_profile": decision.action_profile,
        "cie_verdict": decision.cie_verdict,
        "reason_code": decision.reason_code,
        "observed_tick_hash": observation.observed_tick_hash,
        "psp_merkle_root": observation.psp_merkle_root,
        "invariant_set_digest": observation.invariant_set_digest,
        "extractor_version": observation.extractor_version,
    }
    receipt_digest = sha256_hex(stable_stringify(receipt_payload).encode())
    receipt_payload["receipt_digest"] = f"sha256:{receipt_digest}"
    return AgentReceipt.parse_obj(receipt_payload)


__all__ = [
    "AgentReceipt",
    "AgentReceiptContext",
    "AgentReceiptDecision",
    "AgentReceiptObservation",
    "BindingLiterals",
    "CIEV2Plug",
    "ExtractorAttestation",
    "GateError",
    "InvariantSet",
    "KernelToken",
    "ReplayCapsule",
    "ReplayReceipt",
    "extract_invariants",
    "fossilize_token",
    "assemble_plug",
    "ingest_plug",
    "make_agent_receipt",
    "stable_stringify",
]

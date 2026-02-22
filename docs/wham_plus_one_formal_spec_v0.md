# WHAM+1 Formal Spec v0

**Status:** Draft (v0)

## 1. Purpose

WHAM+1 defines a deterministic, auditable control layer that sequences a primary
workload (WHAM) with a single, bounded follow-up action (+1). The goal is to
ensure that each WHAM transaction has exactly one explicit post-condition that
is validated, logged, and sealed for replay and compliance.

## 2. Scope

- **In scope**: Formal ordering, validation gates, and ledger recording for the
  WHAM phase and its +1 phase.
- **Out of scope**: Model-specific internals, domain-specific policies beyond
  the validation gates described here.

## 3. Definitions

- **WHAM Transaction**: The primary workload request with a deterministic input
  contract and acceptance criteria.
- **+1 Action**: A single, explicit post-condition step that must be executed
  immediately after a successful WHAM transaction.
- **Gate**: A deterministic acceptance rule applied before, during, or after
  execution.
- **Ledger Record**: An append-only audit entry capturing inputs, outputs,
  hashes, and gate outcomes.

## 4. Input Contract

Each WHAM+1 request MUST include:

```json
{
  "wham": {
    "request_id": "string",
    "payload": "object",
    "sha256_payload": "string"
  },
  "plus_one": {
    "action_id": "string",
    "payload": "object",
    "sha256_payload": "string"
  },
  "metadata": {
    "run_id": "string",
    "source_registry": "string",
    "attestation_id": "string"
  }
}
```

### 4.1 Required Fields

- `wham.request_id` and `plus_one.action_id` MUST be unique within a run.
- `sha256_payload` MUST be the hash of the respective payload object encoded in
  canonical JSON (see §4.2).
- `metadata.attestation_id` MUST reference a pre-approved governance record.

### 4.2 Canonical JSON Encoding

Payloads MUST be encoded using the following canonicalization rules before
hashing:

- UTF-8 encoding.
- Object keys sorted lexicographically.
- No insignificant whitespace.
- No NaN/Infinity values.
- Arrays preserve original ordering.

## 5. Execution Order

1. **Ingress validation**
   - Verify schema completeness and hash integrity.
   - Verify `source_registry` allowlist membership.
2. **WHAM phase**
   - Execute `wham.payload` under the declared gates.
3. **+1 phase**
   - Execute `plus_one.payload` only if WHAM gates pass.
4. **Ledger sealing**
   - Write a single ledger record for the combined run.

## 6. Gates

### 6.1 Ingress Gates

- `schema_valid` MUST be true.
- `payload_hash_valid` MUST be true for both WHAM and +1 payloads.
- `source_registry_allowed` MUST be true.

### 6.2 WHAM Gates

- `wham_acceptance` MUST be true to proceed to +1.

### 6.3 +1 Gates

- `plus_one_acceptance` MUST be true for a run to be marked `pass`.

## 7. Ledger Record

Each run MUST write exactly one ledger record containing:

```json
{
  "timestamp": "RFC3339",
  "run_id": "string",
  "wham_request_id": "string",
  "plus_one_action_id": "string",
  "gate_results": {
    "schema_valid": true,
    "payload_hash_valid": true,
    "source_registry_allowed": true,
    "wham_acceptance": true,
    "plus_one_acceptance": true
  },
  "artifact_refs": {
    "wham_output": "uri",
    "plus_one_output": "uri"
  },
  "status": "pass|fail"
}
```

### 7.1 Ledger Hashes

- The ledger record MUST include `sha256_payload` values that match §4.2.
- If an implementation stores a ledger hash, it MUST be computed over the
  canonical JSON encoding of the entire ledger record.

## 8. Failure Modes

- If any ingress gate fails, the run MUST be rejected and the +1 phase MUST NOT
  execute.
- If WHAM gates fail, the +1 phase MUST NOT execute.
- If +1 gates fail, the run MUST be marked `fail` with all gate results recorded.

## 9. Compliance and Replay

- All inputs, outputs, and gate outcomes MUST be replayable from the ledger
  record without external dependencies.
- Any deviation from the execution order MUST be treated as a `fail`.

## 10. Idempotency

- Replaying the same `run_id` with identical payloads MUST produce identical
  gate outcomes and ledger hashes.
- If a `run_id` is re-submitted with different payload hashes, the run MUST be
  rejected.

## 11. Versioning

- This document is **WHAM+1 Formal Spec v0**.
- Breaking changes MUST increment the major version (v1, v2, ...).
- Minor clarifications MAY update the v0 document with a dated revision note.

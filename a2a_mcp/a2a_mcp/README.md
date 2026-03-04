### README

---

# Core Orchestrator

[![CI](https://github.com/Q-Enterprises/core-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/Q-Enterprises/core-orchestrator/actions/workflows/ci.yml)

**Purpose**  
The Core Orchestrator is a sovereign, deterministic runtime for multi‑agent systems. It provides a secure handshake surface, an append‑only witness layer, deterministic canonicalization and hashing, Merkle anchoring, and CI enforcement to guarantee replay‑court admissibility and tamper evidence.

**Scope**  
This repository implements the Sovereignty Chain v1 substrate: **handshake**, **witness emission**, **Merkle sealing**, **validation**, and **CI** that enforces invariants end to end.

---

## Architecture Overview

**Components**

- **API Surface**  
  - `POST /swarm/spawn` — privileged spawn endpoint guarded by the handshake flow.

- **Handshake Service**  
  - `core_orchestrator/services/handshake.py` — RFC8785 canonicalization, VANGUARD JWT validation, payload fingerprinting, Han Eigen derivation, NDJSON receipt emission, replay protection.

- **Witness Layer**  
  - Append‑only NDJSON file at `WITNESS_LOG_PATH` containing canonical receipts.

- **Merkle Anchorer**  
  - `core_orchestrator/services/merkle_anchor.py` — deterministic Merkle tree builder and anchor emitter to `ANCHOR_LOG_PATH`.

- **Verification Tools**  
  - CLI and test harnesses for offline verification of receipts and anchors.

- **CI Pipeline**  
  - `.github/workflows/sovereignty-ci.yml` — runs deterministic tests, schema validation, Merkle anchoring, and artifact uploads.

**Design Principles**

- **Determinism** — canonicalization and hashing are stable and idempotent.  
- **Minimal Attack Surface** — RBAC and JWT validation at the edge.  
- **Tamper Evidence** — Merkle anchoring of witness receipts.  
- **Auditability** — NDJSON receipts are the primary admissibility artifact.  
- **Separation of Concerns** — API surface, handshake logic, and anchoring are modular.

---

## Handshake Contract

**High Level**

1. **VANGUARD issues JWT** with `han_eigen`, `jti`, `role` or explicit `capabilities`.  
2. **Client canonicalizes payload** using RFC8785 and computes `payload_hash = sha256(payload_canonical)`.  
3. **Client POSTs MCP envelope** containing `vanguard_jwt`, `payload_canonical`, `payload_hash`, `envelope_id`, and `client_meta`.  
4. **MCP verifies JWT** (signature, `exp`, `iat`, `jti`, `role`/capability).  
5. **MCP computes payload_hash** and compares to client value.  
6. **MCP registers replay index**, computes Han Eigen, builds canonical receipt preimage, signs it, appends NDJSON receipt, and returns `receipt_ref`.

**Deterministic Rules**

- All canonicalization uses RFC8785 semantics.  
- Hashing uses SHA‑256 hex lowercase.  
- Receipt preimage canonicalization is used for receipt hashing and signing.  
- Replay protection uses `envelope_id` + `vanguard_jti` uniqueness within a configured window.

**Error Codes**

- `INVALID_JWT`  
- `ROLE_DENIED`  
- `INVALID_CANONICAL`  
- `HASH_MISMATCH`  
- `REPLAY_DETECTED`  
- `INVALID_ENVELOPE`  
- `INTERNAL_ERROR`

---

## API Reference

**Endpoint**

```
POST /swarm/spawn
Authorization: Bearer <VANGUARD_JWT>
Content-Type: application/json
```

**Request Body Schema (MCP Envelope)**

```json
{
  "envelope_id": "string",
  "vanguard_jwt": "string",
  "payload_canonical": "string",
  "payload_hash": "string",
  "client_meta": {
    "client_id": "string",
    "origin": "string"
  },
  "timestamp": "string (optional)"
}
```

**Successful Response**

```json
{
  "status": "accepted",
  "receipt_ref": "<mcp_receipt_id>"
}
```

**Notes**

- `payload_canonical` must be RFC8785 canonical JSON string.  
- `payload_hash` must be lowercase SHA‑256 hex of `payload_canonical`.  
- The endpoint enforces `role=admin` or explicit capability `spawn:agent`.

---

## Witness Format

**NDJSON Receipt Line**

Each line is a single canonical JSON object with deterministic fields:

```json
{
  "mcp_receipt_id": "string",
  "envelope_id": "string",
  "payload_hash": "string",
  "vanguard_kid": "string",
  "vanguard_jti": "string",
  "binding": { "method": "sha256", "value": "string" },
  "receipt_hash": "string",
  "signature_kid": "string",
  "signature": "string",
  "han_eigen": "string"
}
```

**Rules**

- Append only. No in‑place edits.  
- Each line is canonicalized before append.  
- `receipt_hash` is `sha256(RFC8785(canonical_receipt_preimage))`.  
- `signature` is base64url of the MCP signature over the canonical preimage.

---

## Merkle Anchoring

**Behavior**

- Read witness NDJSON lines, canonicalize each receipt, compute leaf hash = `sha256(canonical_receipt)`.  
- Build deterministic Merkle tree: left‑to‑right ordering, no padding; odd leaf promoted.  
- Emit anchor object:

```json
{
  "version": "v1",
  "merkle_root": "<hex>",
  "leaf_count": <int>,
  "timestamp": "<UTC ISO8601>"
}
```

- Append anchor as canonical NDJSON to `ANCHOR_LOG_PATH`.

**Invocation**

- `python -m core_orchestrator.services.merkle_anchor`  
- CI runs anchoring on schedule and on push to `main`.

---

## Schemas and Samples

**Schema File**

- `schemas/mcp_envelope.schema.json` — JSON Schema for MCP envelope.

**Sample Envelope**

- `schemas/mcp_envelope.sample.json` — minimal valid sample used in CI validation.

---

## Tests and CI

**Test Coverage**

- `tests/test_canonicalization.py` — canonicalization determinism and hash consistency.  
- `tests/test_handshake.py` — handshake success path, hash mismatch, replay detection.  
- `tests/test_merkle_anchor.py` — Merkle root computation and anchor emission.

**CI Workflow**

- `.github/workflows/sovereignty-ci.yml` runs:
  - Lint and type checks
  - Deterministic unit tests
  - Schema validation
  - Merkle anchoring
  - Artifact upload (anchor and witness snapshot)

**Enforcement**

- Require CI pass for `main` merges.  
- Protect `main` with branch protection rules.

---

## Security and Key Management

**JWT Validation**

- Use JWKS discovery for VANGUARD public keys.  
- Enforce `kid` header and validate `exp`, `iat`, `nbf`, and `jti`.  
- Prefer explicit capability claims over coarse roles.

**MCP Signing Keys**

- Store MCP private key in secure secret store.  
- Use `kid` for MCP signing key reference in receipts.  
- Rotate keys with versioned `signature_kid` and record rotation events in anchor metadata.

**Replay Protection**

- Short window in memory or persistent index (Redis or DB recommended for multi‑process).  
- `envelope_id` + `vanguard_jti` uniqueness enforced.

**Operational Hardening**

- Run witness and anchor logs on append‑only storage.  
- Periodically Merkle anchor and archive witness snapshots to immutable storage.  
- Audit logs must be retained and accessible to replay court.

---

## Developer Guide

**Local Setup**

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Run Tests**

```bash
pytest -q
```

**Run Merkle Anchor Locally**

```bash
export WITNESS_LOG_PATH=./witness.ndjson
export ANCHOR_LOG_PATH=./anchor.ndjson
python -m core_orchestrator.services.merkle_anchor
```

**Run Handshake Unit Test Flow**

- Use the test harness in `tests/test_handshake.py` which mocks external keys and writes witness lines to a temp file.

---

## Contribution Guidelines

**Code Style**

- Follow repository linting rules: `black`, `ruff`, `mypy`.  
- Keep canonicalization deterministic and avoid nondeterministic fields in receipts.

**Pull Request Requirements**

- All PRs must include tests for new deterministic behavior.  
- Schema changes require sample updates and CI schema validation.  
- Security changes must include threat model notes and key rotation plan.

**Release Process**

- Anchors produced by CI can be used to create signed release tags.  
- Maintain an audit trail of anchor metadata and witness snapshots for each release.

---

## Appendix

**Key Files**

- `core_orchestrator/services/handshake.py`  
- `core_orchestrator/api/swarm.py` (route wrapper)  
- `core_orchestrator/services/merkle_anchor.py`  
- `schemas/mcp_envelope.schema.json`  
- `tests/` (deterministic test suite)  
- `.github/workflows/sovereignty-ci.yml`

**Contact**

- **Repository Maintainers**: See `MAINTAINERS.md` in repo root for owner and security contact.

---

## Quick Start Summary

1. Install dependencies.  
2. Run tests.  
3. Configure JWKS and MCP signing key secrets.  
4. Start FastAPI and ensure `WITNESS_LOG_PATH` is writable.  
5. Trigger `POST /swarm/spawn` with a valid VANGUARD JWT and canonical payload.  
6. Verify NDJSON receipt appended and Merkle anchor produced by CI or manual run.

---

**This README is intended to be dropped into the repository root as `README.md`.**

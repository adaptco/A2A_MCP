# Avatar Token Contract v1

**Status:** Active (canonical for embedded-avatar ingestion)  
**Version:** `v1`  
**Effective date:** 2026-02-23  
**Primary consumers:** `ingest_worldline_block_impl` in `app/mcp_tooling.py` and downstream embedding/indexing jobs.

This document defines the **versioned bearer/OIDC token claims** and **avatar payload schema** for embedded-avatar ingestion. It is the normative contract for any client producing payloads that include:

- `embedding_vector`
- `token_stream`
- `artifact_clusters`
- `lora_attention_weights`

---

## 1) Authentication and Authorization Claims (Bearer/OIDC)

A request MUST present a bearer token that is either a signed JWT access token or ID token issued by the platform IdP.

### 1.1 Required claims

| Claim | Type | Requirement | Validation rule |
|---|---|---|---|
| `iss` | string | REQUIRED | Must exactly match one configured trusted issuer URI. |
| `aud` | string or string[] | REQUIRED | Must contain configured ingestion audience (e.g., `a2a-avatar-ingest`). |
| `repository` | string | REQUIRED | Canonical repo slug (`org/name`) initiating ingest. |
| `actor` | string | REQUIRED | Principal identifier (human, service account, or workload identity). |

### 1.2 Recommended companion claims

- `sub` (stable identity)
- `iat`, `exp` (time-bounded token validity)
- `jti` (replay-detection correlation)

### 1.3 Rejection rules

Requests MUST be rejected with `401`/`403` when any required claim is missing, malformed, expired, or unauthorized for the specified `repository`.

---

## 2) Avatar Payload Schema (Request Body)

The ingestion body MUST include the following top-level fields.

```json
{
  "schema_version": "v1",
  "avatar_id": "coder",
  "embedding_vector": [0.012, -0.338, 0.901],
  "token_stream": ["optimize", "query", "plan"],
  "artifact_clusters": [
    {
      "cluster_id": "c-001",
      "artifact_ids": ["doc:123", "code:abc"],
      "weight": 0.82
    }
  ],
  "lora_attention_weights": {
    "adapter_release": 0.31,
    "adapter_arch": 0.69
  },
  "metadata": {
    "source": "avatar-runtime",
    "trace_id": "4a74f9a4-..."
  }
}
```

### 2.1 Required top-level fields

| Field | Type | Required | Constraints |
|---|---|---|---|
| `schema_version` | string | REQUIRED | Must be exactly `v1` for this contract. |
| `avatar_id` | string | REQUIRED | Non-empty, max 128 chars, regex `^[a-zA-Z0-9._:-]+$`. |
| `embedding_vector` | number[] | REQUIRED | 1..4096 finite float values before shaping. |
| `token_stream` | string[] | REQUIRED | 1..8192 items; each token 1..256 UTF-8 chars. |
| `artifact_clusters` | object[] | REQUIRED | 0..1024 cluster objects; schema below. |
| `lora_attention_weights` | object | REQUIRED | Map of adapter key -> float in `[0.0, 1.0]`. |

### 2.2 `artifact_clusters` object schema

Each entry in `artifact_clusters` MUST follow:

| Field | Type | Required | Constraints |
|---|---|---|---|
| `cluster_id` | string | REQUIRED | Non-empty, max 128 chars. |
| `artifact_ids` | string[] | REQUIRED | 1..4096 items, each non-empty. |
| `weight` | number | OPTIONAL | Float in `[0.0, 1.0]`; defaults to `1.0` if absent. |

### 2.3 `lora_attention_weights` constraints

- Keys MUST match regex `^[a-zA-Z0-9._:-]{1,128}$`.
- Values MUST be finite float in `[0.0, 1.0]`.
- Sum is allowed to be any positive value at ingest (normalization happens during shaping).

---

## 3) Canonical Token-Shaping Output Schema

Before persistence/indexing, ingestion MUST emit a canonical normalized envelope.

```json
{
  "schema_version": "v1",
  "normalized": {
    "embedding_vector": {
      "dimension": 1536,
      "values": [0.01, -0.02, 0.03],
      "source_dimension": 1024,
      "shape_policy": "pad_with_zeros"
    },
    "token_stream": {
      "max_tokens": 4096,
      "tokens": ["optimize", "query"],
      "truncated": false
    },
    "artifact_clusters": {
      "clusters": [],
      "max_clusters": 256,
      "truncated": false
    },
    "lora_attention_weights": {
      "weights": {
        "adapter_release": 0.31,
        "adapter_arch": 0.69
      },
      "normalized_sum": 1.0,
      "normalization_method": "sum_to_one"
    }
  },
  "hashes": {
    "embedding_sha256": "...",
    "token_stream_sha256": "...",
    "artifact_clusters_sha256": "...",
    "lora_attention_weights_sha256": "...",
    "canonical_payload_sha256": "..."
  }
}
```

### 3.1 Canonical normalization rules

1. **Embedding dimension target**: `1536` dimensions.
   - If input dimension `< 1536`: right-pad with `0.0`.
   - If input dimension `> 1536`: truncate tail values beyond index `1535`.
   - Non-finite values (`NaN`, `Inf`) MUST fail validation.
2. **Token stream**:
   - Keep stable order.
   - Max canonical length `4096` tokens.
   - If longer, truncate tail and set `truncated=true`.
3. **Artifact clusters**:
   - Max canonical cluster count `256`.
   - Preserve input order; truncate tail if over limit.
   - Within each cluster, keep up to first `1024` `artifact_ids`.
4. **LoRA weights**:
   - Drop keys with value `0.0` only if explicitly configured; default is retain-all.
   - Normalize by sum-to-one when total > 0.
   - If all zeros, keep zeros and mark `normalized_sum=0.0`.

### 3.2 Hash metadata rules

- Hash algorithm: `SHA-256`.
- Serialization for hashing MUST be canonical JSON:
  - UTF-8 encoding
  - Deterministic key ordering
  - No insignificant whitespace
- `canonical_payload_sha256` is computed over the full canonical envelope excluding the `hashes` object itself.

---

## 4) Backward Compatibility and Deprecation Policy

### 4.1 Accepted input versions

- **Current:** `v1` (fully supported)
- **Legacy unversioned payloads:** accepted temporarily via compatibility adapter only.

### 4.2 Compatibility behavior for legacy payloads

If `schema_version` is missing:

1. Treat as `legacy` input profile.
2. Attempt field mapping into `v1` (`embedding_vector`, `token_stream`, `artifact_clusters`, `lora_attention_weights`).
3. Emit warning telemetry tag: `avatar_contract_legacy_payload=true`.
4. Canonical output MUST still be emitted as `schema_version: "v1"`.

### 4.3 Deprecation timeline

- **T0 (publish date):** contract published; all new clients must send `schema_version="v1"`.
- **T0 + 30 days:** legacy payloads produce warning-level ingest logs.
- **T0 + 60 days:** legacy payloads produce error-level logs + metric alert.
- **T0 + 90 days:** legacy payloads are rejected (`400 Bad Request`).

### 4.4 Breaking changes

Any future breaking changes require a new contract file (`avatar_token_contract_v2.md`) and explicit dual-read migration window.

---

## 5) Ownership and Change Control

- **Contract owners:** Avatar platform + ingestion platform maintainers.
- Changes to field semantics/ranges MUST be versioned and announced in release notes.
- Runtime and deployment documentation MUST link this document as the canonical source.

## 6) Cross-links

- Deployment integration: [GKE Release Deployment Contract Reference](../deployment/GKE_RELEASE_DEPLOYMENT.md)
- Avatar architecture reference: [Avatar System](../AVATAR_SYSTEM.md)

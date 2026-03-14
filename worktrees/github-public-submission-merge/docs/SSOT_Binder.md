# SSOT Binder — `ssot.registry.v1`

This binder defines how the Qube Sovereign Archive seals, audits, and replays every capsule. It expands the registry capsule into executable procedures so contributors and agents can operate without drifting from the sovereign source of truth (SSOT).

---

## 1. Merkle-Bound Architecture

| Layer | Responsibility | Key Artifacts |
| --- | --- | --- |
| **Entry Leaves** | Canonical JSON payloads for scripts, storyboards, assets, clips, and checkpoints. | `entry.script`, `entry.storyboard`, `entry.asset`, `entry.clip`, `entry.checkpoint` |
| **Merkle Builder** | Hashes leaf payloads (`sha256`) and assembles a deterministic Merkle tree per capsule batch. | `merkle_root`, `merkle_path[]` |
| **Council Attestation** | Captures quorum signatures once the Merkle root is frozen. | `council_attestation.signatures[]`, `quorum_rule` |
| **Fossilized Capsule** | Final immutable packet stored offline and mirrored across registries. | `registry.manifest`, `capsule_bundle.tgz` |

* Every artifact leaf includes the full JSON body and its canonical hash (`canonical_sha256`).
* The Merkle builder emits proofs for each leaf, enabling independent verification without the full dataset.
* Council signatures seal the Merkle root, preventing mutation while still allowing forks under governance rules.

---

## 2. Entry Class Specifications

All entries inherit the base fields below and add type-specific metadata.

```json
{
  "artifact_id": "<type>.<slug>.v<semver>",
  "type": "script|storyboard|asset|clip|checkpoint",
  "author": "<human_or_agent>",
  "created_at": "<ISO-8601 UTC>",
  "canonical_sha256": "sha256:<digest>",
  "merkle_root": "merkle:<digest>",
  "council_attestation": {
    "signatures": ["sig:queen_boo_router", "sig:cici_stabilizer"],
    "quorum_rule": "2-of-3"
  }
}
```

### 2.1 Script Capsules — `entry.script`

| Field | Description |
| --- | --- |
| `story_scope` | Narrative bounds (e.g., `monza.2025.race`) |
| `beats[]` | Ordered beat sheet references (`beat_id`, `summary`, `duration_s`) |
| `dependencies[]` | Linked storyboard or asset IDs required for execution |

### 2.2 Storyboard Capsules — `entry.storyboard`

| Field | Description |
| --- | --- |
| `panels[]` | Frame descriptors with composition notes and camera metadata |
| `linked_script` | Canonical script ID validated before sealing |
| `style_tokens[]` | Visual grammar and cadence descriptors |

### 2.3 Asset Capsules — `entry.asset`

| Field | Description |
| --- | --- |
| `asset_type` | e.g., `lego_model`, `sound_pack`, `shader_profile` |
| `storage_uri` | Content-addressed location (IPFS, S3, or offline vault hash) |
| `integrity_checksums` | Additional digests (`md5`, `blake3`) for redundancy |

### 2.4 Clip Capsules — `entry.clip`

| Field | Description |
| --- | --- |
| `duration_s` | Rendered clip length |
| `fps_nominal` | Target cadence (e.g., `12`) |
| `source_capsules[]` | Script/storyboard/asset IDs that produced the clip |
| `post_processing` | Applied filters (jitter, exposure drift, etc.) |

### 2.5 Checkpoint Capsules — `entry.checkpoint`

| Field | Description |
| --- | --- |
| `flow_state` | Serialized orchestrator state machine snapshot |
| `resume_token` | Deterministic handle used by `qube.orchestrator.v1` |
| `conditions[]` | Preconditions for replay (e.g., `maker_checker`, `no_drift`) |

---

## 3. Sealing Workflow

1. **Draft Capsule Payload**  
   Prepare the JSON payload for the entry class, ensuring all cross-references point to previously sealed artifacts.
2. **Hash & Normalize**  
   Normalize JSON (sorted keys, UTF-8, LF line endings) and compute `sha256`. Store as `canonical_sha256`.
3. **Merkle Enrollment**  
   Submit the payload to the Merkle builder with batch ID (e.g., `2025-09-23.storyboard`). Receive `merkle_root` and `merkle_path` proof.
4. **Council Review**  
   Present canonical hash + Merkle root to council members (Queen Boo, CiCi, plus optional third seat). Collect signatures until quorum is met.
5. **Fossilize Capsule**  
   Package payload, proof, and signatures into a signed bundle (`capsule_bundle.tgz`). Store offline and publish manifest entry.
6. **Registry Update**  
   Append the sealed entry to `registry.manifest.json` and emit a lineage delta referencing parent/fork entries.

Each step is auditable; skipping any stage invalidates `replay.authorized` checks in downstream services.

---

## 4. Replay & Fork Protocols

* **Standard Replay**: Allowed when `capsule.integrity == valid` and quorum signatures are intact. Orchestrator verifies both conditions via SSOT hooks before dispatching work.
* **Maker–Checker Override**: Checkpoint capsules encode override conditions. A checker must countersign before replaying a flow branch.
* **Fork Creation**: Use `lineage.forks[]` to declare new experimental paths. Forks inherit parent Merkle proofs but must obtain fresh council signatures before activation.
* **Revocation**: Invalidate a capsule by publishing a superseding entry with `immutable: false` and `revoked_by` metadata. The registry retains historical proofs for audit.

---

## 5. Contributor Checklist

1. Confirm you are operating in an air-gapped or read-only network segment before handling sealed bundles.
2. Use the provided CLI (`registry seal <payload.json>`) to normalize, hash, and enroll payloads—manual edits after hashing are prohibited.
3. Verify signatures with `registry attestation verify --artifact <id>` prior to pushing manifests.
4. Update lineage references atomically: parent linkage, fork declarations, and immutability flags must match the governance decision log.
5. Publish updated manifests to both online mirror and offline vault, keeping checksums identical.

---

## 6. Integration Touchpoints

* **Core Orchestrator (`qube.orchestrator.v1`)** uses checkpoint capsules to resume flows and validates every payload against `canonical_sha256` + `merkle_root`.
* **PreViz Executor (`sol.f1.previz.v1`)** requires asset and storyboard capsules to match the SSOT manifest before rendering animatics or ledgers.
* **CI Automation**: Every commit triggers a manifest diff check ensuring no sealed capsule has been mutated. Diffs are blocked until a superseding capsule with new lineage is registered.
* **Telemetry Hooks**: Emit `registry.event` logs whenever a new capsule is sealed or replayed; downstream systems subscribe for governance dashboards.

---

## 7. Reference Bundle Layout

```text
ssot/
├── registry.manifest.json   # Consolidated list of sealed artifacts
├── capsules/
│   ├── storyboards/
│   │   └── storyboard.monza.v1.json
│   ├── scripts/
│   │   └── script.monza.v1.json
│   ├── assets/
│   │   └── asset.ferrari_sf23.v1.json
│   ├── clips/
│   │   └── clip.monza.overtake.v1.json
│   └── checkpoints/
│       └── checkpoint.qube_router.v1.json
└── proofs/
    ├── merkle/
    │   └── 2025-09-23.storyboard.proof.json
    └── attestations/
        └── storyboard.monza.v1.sigbundle.json
```

This structure mirrors the Git repository and the offline vault so manifests, payloads, and proofs stay synchronized.

---

By adopting this binder, any contributor or autonomous agent can register, verify, or replay capsules without threatening the sovereign lineage of the F1 Lego project.
All five entry classes remain anchored to the same Merkle root, delivering tamper-evident provenance across the **expanded relay braid (Proof → Flow → Execution → Vault)**.

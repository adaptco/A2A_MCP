# Migration Plan (Minimal Disruption Sequence)

## Phase 0 — Access and freeze window
1. Obtain read access to both repos and snapshot current heads.
2. Freeze non-critical merges during boundary migration window.
3. Baseline scans (size, file extensions, import graph, secret scan).

## Phase 1 — Interfaces first (no heavy assets moved yet)
1. Define shared schemas:
   - `DatasetManifest`
   - `BuildManifest`
   - `ArtifactReceipt`
   - `CommitProof`
2. Define MCP/A2A tool surfaces:
   - `rag.query(index_id, query, top_k)`
   - `artifact.fetch(artifact_id)`
   - `receipt.verify(receipt_id)`
3. Add compatibility shims so AGENTS_HOST consumes IDs/URIs only.
4. Add append-only ledger interface (write-once, no update/delete semantics).

## Phase 2 — Move pipelines/assets to MODELS_HOST
1. Move embeddings/index build pipelines to MODELS_HOST.
2. Move LoRA/data prep/training/checkpoint management to MODELS_HOST.
3. Publish artifacts to external immutable store.
4. Emit commitments per build:
   - `dataset_manifest_commit = sha256(canonical_manifest_json)`
   - `build_manifest_commit   = sha256(canonical_build_json)`
   - `artifact_commit         = sha256(bytes)`
5. Register tuple in append-only ledger:
   - `{artifact_id, index_id?, dataset_manifest_commit, build_manifest_commit, artifact_commit, uri, timestamp}`

## Phase 3 — Enforce CI gates in AGENTS_HOST
1. Fail CI if disallowed weight files exist:
   - `*.safetensors`, `*.pt`, `*.bin`, `*.ckpt`, oversized `*.onnx`
2. Fail CI if disallowed corpora dirs exist:
   - `datasets/`, `corpus/`, `prompts_dump/`, `embeddings_dump/`
3. Fail CI on vector index snapshots:
   - qdrant/faiss/milvus dump signatures
4. Fail CI on large files over threshold unless allowlisted in ignored data locations.
5. Fail CI if runtime imports training modules (static import scan).
6. Fail CI if direct artifact bytes enter prompt builder paths.

## Phase 4 — Cutover and verification
1. Flip runtime to read-only commitment verification path.
2. Disable legacy in-repo artifact paths.
3. Backfill historical artifacts into ledger with immutable commits.
4. Run incident drill: tampered artifact should fail `receipt.verify`.

## PR PLAN (Two PRs)

### PR1: enforce boundaries + tool surfaces
**File list (representative):**
- `schemas/dataset_manifest.*`
- `schemas/build_manifest.*`
- `schemas/artifact_receipt.*`
- `mcp/tools/rag_query.*`
- `mcp/tools/artifact_fetch.*`
- `mcp/tools/receipt_verify.*`
- `.github/workflows/agents-boundary-gates.yml`
- `scripts/scan_disallowed_assets.*`
- `scripts/scan_runtime_imports.*`

**High-level diff summary:**
- Adds strict runtime contracts (IDs + commits + URIs).
- Adds MCP tool APIs returning proofs and concise verdicts.
- Adds CI gates blocking contamination patterns in AGENTS_HOST.

### PR2: move assets + wire commitments + CI gates
**File list (representative):**
- `pipelines/index_build/*` (to MODELS_HOST)
- `pipelines/lora_train/*` (to MODELS_HOST)
- `pipelines/dataset_prep/*` (to MODELS_HOST)
- `ledger/append_only_writer.*`
- `ledger/verify_receipt.*`
- `.github/workflows/models-artifact-attestation.yml`
- `docs/migration/asset-relocation-map.md`

**High-level diff summary:**
- Relocates asset-heavy pipelines to MODELS_HOST.
- Writes sha256 commitments for dataset/build/artifact.
- Publishes immutable URIs and verifies proofs in runtime path.
- Enforces CI for attestation presence and integrity checks.

## Implementation readiness gates (must pass before Phase 1)
- Read/write access validated for both repos.
- `scripts/pr_preflight_check.sh` returns PASS in both repos.
- Interface spec v1 approved (canonicalization + versioning + error codes).
- CI thresholds and allowlists approved (file size + import scan scope).
- Rollback criteria approved for each migration phase.

# Takeover Clarifications (PR #3 follow-up)

This document addresses the follow-up request asking what additional takeover work remains and what “other significant clusters from adaptco repos” refers to.

## 1) Additional changes made during takeover (this branch)

On this branch, the takeover added only planning/decision documents:

- `REPORT.md`
- `RECOMMENDATION.md`
- `MIGRATION_PLAN.md`
- `PR_PLAN.md`

No Terraform, CI workflow, or Unity runtime code was modified in this branch.

## 2) Clarification: “significant clusters from adaptco repos”

The phrase refers to **model/data-plane clusters** that should be hosted in `adaptco/core-orchestrator` (MODELS_HOST) and exposed to runtime via strict interfaces.

### Cluster A — RAG data & index build systems
- Dataset preparation/chunking flows
- Embedding generation jobs
- Vector index build + refresh jobs
- Index snapshot publication metadata

### Cluster B — Training systems (LoRA / RL / fine-tuning)
- Training dataset manifests
- Build/run manifests and hyperparameter receipts
- Checkpoint/weight publication and model registry metadata

### Cluster C — Artifact/provenance pipeline
- Canonical manifest generation
- Commitments (`dataset_manifest_commit`, `build_manifest_commit`, `artifact_commit`)
- Append-only ledger publishing
- Receipt verification service endpoints

### Cluster D — Model-serving MCP endpoints
- `rag.query(index_id, query, top_k)`
- `artifact.fetch(artifact_id)`
- `receipt.verify(receipt_id)`

## 3) What should remain in AGENTS_HOST

Keep only control-plane logic:

- Orchestrator/agent runtime loops
- MCP/A2A bridge + tool schemas
- Policy/theta gates
- Proof verification and allow/deny routing

No corpora, index snapshots, prompt dumps, checkpoints, or model weight binaries.

## 4) Integration order to reduce risk

1. Freeze interfaces and schemas.
2. Move model/data clusters to MODELS_HOST.
3. Switch runtime to ID+proof calls only.
4. Enforce CI policy gates in AGENTS_HOST.
5. Make proof-gate mandatory before runtime retrieval.

## 5) Concrete handoff request for integration team

When integrating from adaptco repos, request these bundles explicitly:

- **Bundle 1:** RAG build pipeline code + index publication metadata.
- **Bundle 2:** Training pipelines (LoRA/RL) + registry publication metadata.
- **Bundle 3:** Ledger writer/verifier services + canonicalization helpers.
- **Bundle 4:** MCP server surfaces for query/fetch/verify with proof payloads.

This enables incremental migration without coupling runtime prompts to raw model assets.

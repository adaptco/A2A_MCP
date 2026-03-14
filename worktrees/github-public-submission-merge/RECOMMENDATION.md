# Recommendation: Split to Minimize Context Contamination and Token Waste

## Recommended split
- **AGENTS_HOST:** `adaptco/core-orchestrator`
- **MODELS_HOST:** `Q-Enterprises/core-orchestrator`

## Why this split minimizes contamination and token waste
1. Runtime prompts should only include compact tool schemas, IDs, and verdicts.
2. Training/index assets are high-entropy payloads (corpora, checkpoints, vectors) and should be physically separated from runtime orchestration code.
3. Separate release trains reduce accidental coupling: runtime hotfixes stay fast; model/index updates stay governed.
4. Blast radius is reduced: compromise of AGENTS_HOST does not expose full corpora/weights if only IDs+commits+URIs are present.

## Hard boundaries (forbidden in AGENTS_HOST)
Do **not** commit or store:
- model weights/checkpoints (`*.safetensors`, `*.pt`, `*.bin`, `*.ckpt`, large `*.onnx`)
- corpora/datasets (`datasets/`, `corpus/`)
- prompt dumps/eval transcripts (`prompts_dump/`, raw chat logs)
- vector DB snapshots/index files (FAISS/Qdrant/Milvus dumps)
- embedding dumps (`embeddings_dump/`)
- long-lived spool/log payloads with sensitive context

## ZKP-style (lightweight) commitment requirements
For each RAG build and LoRA build:
- `dataset_manifest_commit = sha256(canonical_manifest_json)`
- `build_manifest_commit   = sha256(canonical_build_json)`
- `artifact_commit         = sha256(bytes)`

Store commitment tuples in an append-only ledger. AGENTS_HOST consumes only IDs, commits, and URIs.

## Runtime data contract (AGENTS_HOST consumes only)
- `index_id`, `artifact_id`, `receipt_id`
- `dataset_manifest_commit`
- `build_manifest_commit`
- `artifact_commit`
- immutable artifact URI

No raw corpora or raw weights in agent prompts or AGENTS_HOST repository content.

## Token optimization contract
LLM context is limited to:
- tool schemas
- compact IDs
- short verdict summaries

All heavy retrieval must flow through MCP tools:
- `rag.query(index_id, query, top_k) -> snippets + commit proofs`
- `artifact.fetch(artifact_id) -> payload + commit proofs`
- `receipt.verify(receipt_id) -> pass/fail + reason`

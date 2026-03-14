# Docling Pipeline Release v1.0.0

**Release Date**: 2026-01-26  
**Status**: Release Candidate

---

## Overview

Deterministic, hash-anchored document processing pipeline using IBM Docling, PyTorch embeddings, and local-first Docker Compose deployment.

## Release Components

### Core Services

- **Ingest API** (FastAPI) - File upload and task queueing
- **Docling Worker** - Document parsing and normalization
- **Embed Worker** - Batch embedding generation with PyTorch
- **Redis** - Task queue backend
- **Qdrant** - Vector database

### Libraries

- **canonical.py** - RFC8785 JSON canonicalization and SHA256 hashing
- **normalize.py** - Text normalization (NFKC) and L2 vector normalization

---

## Determinism Anchors

All processing is deterministic and cryptographically anchored:

| Component | Version/ID | Hash |
|-----------|------------|------|
| Pipeline Version | v1.0.0 | - |
| Docling | 2.9.0 | - |
| Normalizer | norm.v1 | - |
| Chunker | chunk.v1 | - |
| Embedder Model | sentence-transformers/all-mpnet-base-v2 | sha256:4509c1ee... |
| Embedding Dimension | 768 | - |

---

## Key Features

✅ **RFC8785 Canonical JSON** - Deterministic serialization for stable hashing  
✅ **Append-Only Ledger** - Tamper-evident hash chain in `ledger.jsonl`  
✅ **Model Version Pinning** - Fixed semantic embedding space  
✅ **L2 Normalization** - Standardized embedding vectors  
✅ **Batch Processing** - Efficient PyTorch batch inference  
✅ **Docker-First** - Reproducible deployment

---

## Architecture

```
┌─────────────┐
│ Ingest API  │ ← HTTP POST /ingest
└──────┬──────┘
       │ enqueue
       ▼
┌─────────────┐
│   Redis     │ (parse_queue)
└──────┬──────┘
       │ consume
       ▼
┌─────────────┐
│   Docling   │ → Parse, Normalize, Chunk
│   Worker    │
└──────┬──────┘
       │ enqueue batches
       ▼
┌─────────────┐
│   Redis     │ (embed_queue)
└──────┬──────┘
       │ consume
       ▼
┌─────────────┐
│   Embed     │ → Generate Embeddings
│   Worker    │ → Store in Qdrant
└──────┬──────┘ → Append to Ledger
       │
       ▼
┌─────────────┐
│  Qdrant +   │
│  Ledger     │
└─────────────┘
```

---

## Deployment

### Prerequisites

- Docker & Docker Compose
- 4GB+ RAM (for embedding model)

### Quick Start

```bash
cd pipeline
docker-compose up --build
```

### Ingest a Document

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@document.pdf" \
  -F "pipeline_version=v1.0.0" \
  -F 'metadata={"source":"test"}'
```

---

## Determinism Verification

### Replay Test

The replay test verifies deterministic processing by:

1. Ingesting a document
2. Capturing all hashes from the ledger
3. Re-ingesting the same document
4. Comparing hashes for exact match

```bash
python replay_test.py test_document.txt
```

**Expected Result**: All chunk integrity hashes match across runs.

### Hash Chain Verification

Each ledger entry contains:

- `integrity_hash` - SHA256 of canonical JSON (excluding this field)
- `prev_ledger_hash` - Hash of previous entry (chain link)

Any modification breaks the chain and is immediately detectable.

---

## Upgrade Notes

### v1.0.0 Changes

- **Embedding Model**: Upgraded from `all-MiniLM-L6-v2` (384-dim) to `all-mpnet-base-v2` (768-dim)
- **Quality**: Improved semantic understanding and retrieval performance
- **Breaking**: Incompatible with v0.x embeddings (different dimension)

### Migration from v0.x

If upgrading from a previous version:

1. Create new Qdrant collection for 768-dim vectors
2. Re-process all documents through the pipeline
3. Verify determinism with replay test

---

## Known Limitations

- **Model Weights Hash**: Currently placeholder, needs computation
- **Status Tracking**: `/status/{bundle_id}` endpoint not implemented
- **Cleanup**: Temporary file cleanup not automated
- **Scalability**: Single worker per service (not horizontally scaled)

---

## License

[Specify License]

---

## References

- [RFC 8785 - JCS Canonical JSON](https://www.rfc-editor.org/rfc/rfc8785)
- [IBM Docling](https://github.com/DS4SD/docling)
- [Sentence Transformers](https://www.sbert.net/)
- [Qdrant Vector Database](https://qdrant.tech/)

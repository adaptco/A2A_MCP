# Docling Cluster Pipeline

Deterministic, hash-anchored document processing pipeline using IBM Docling, PyTorch embeddings, and local-first Docker Compose deployment.

## Quick Start

```bash
# Build and start all services
docker-compose up --build

# Ingest a document
curl -X POST http://localhost:8000/ingest \
  -F "file=@document.pdf" \
  -F "pipeline_version=v1.0.0" \
  -F 'metadata={"source":"test"}'

# Check health
curl http://localhost:8000/health
```

## Architecture

- **Ingest API** (FastAPI) - Accepts file uploads, enqueues to Redis
- **Docling Worker** - Parses documents with IBM Docling, normalizes text, chunks content
- **Embed Worker** - Generates PyTorch embeddings with L2 normalization, stores in Qdrant
- **Redis** - Queue backend for task distribution
- **Qdrant** - Vector database for embeddings
- **Ledger** - Append-only hash chain for audit trail

## Determinism Anchors

All processing is deterministic and hash-anchored:

| Key | Value |
|-----|-------|
| pipeline_version | v1.0.0 |
| docling_version | 0.4.0 |
| normalizer_version | norm.v1 |
| chunker_version | chunk.v1 |
| embedder_model_id | sentence-transformers/all-mpnet-base-v2 |

## Directory Structure

```
pipeline/
├── docker-compose.yml
├── schemas/
│   ├── doc.normalized.v1.schema.json
│   └── chunk.embedding.v1.schema.json
├── lib/
│   ├── canonical.py       # JCS hash + ledger
│   └── normalize.py       # L2 norm + text policy
├── ingest_api/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py
├── docling_worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── worker.py
├── embed_worker/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── worker.py
└── ledger/
    └── ledger.jsonl       # Append-only hash chain
```

## Verification

Run the replay test to verify determinism:

```bash
# Submit a document
BUNDLE_ID=$(curl -X POST http://localhost:8000/ingest \
  -F "file=@test.pdf" | jq -r '.bundle_id')

# Wait for processing, then capture hashes
# Re-process and verify identical hashes
```

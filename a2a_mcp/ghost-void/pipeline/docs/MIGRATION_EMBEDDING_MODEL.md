# Embedding Model Migration Guide

## Overview
This document describes the migration from mock embeddings to `sentence-transformers/all-mpnet-base-v2`.

## Model Change

| Aspect | Before | After |
|--------|--------|-------|
| Model | Mock (seeded random) | `all-mpnet-base-v2` |
| Dimension | 768 | 768 |
| Framework | PyTorch (mock) | PyTorch + sentence-transformers |
| Normalization | L2 | L2 |
| Weights Hash | `sha256:mock_weights_hash_for_scaffolding` | Computed from actual weights |

## Breaking Changes

⚠️ **All existing embeddings are invalidated** because:
- The model changed from deterministic mock to real semantic embeddings
- The weights hash changed, making old vectors incompatible

## Migration Steps

### 1. Backup Current Ledger
```bash
cp pipeline/ledger/ledger.jsonl pipeline/ledger/ledger.jsonl.backup
```

### 2. Clear Qdrant Collection
```bash
docker-compose exec qdrant curl -X DELETE http://localhost:6333/collections/document_chunks
```

### 3. Update Environment
```bash
# In docker-compose.yml or .env
EMBEDDER_MODEL_ID=sentence-transformers/all-mpnet-base-v2
WEIGHTS_HASH=<computed_sha256>
```

### 4. Re-ingest Documents
All documents must be re-processed through the pipeline to generate new embeddings.

## Verification

Run the determinism test:
```bash
python pipeline/tests/test_determinism.py
```

Expected output:
```
✓ doc_id matches across runs
✓ chunk_ids match across runs  
✓ embedding hashes match across runs
✓ Determinism verified
```

## Rollback

If issues occur:
1. Restore ledger: `cp pipeline/ledger/ledger.jsonl.backup pipeline/ledger/ledger.jsonl`
2. Revert `EMBEDDER_MODEL_ID` to previous value
3. Restart workers: `docker-compose restart embed-worker`

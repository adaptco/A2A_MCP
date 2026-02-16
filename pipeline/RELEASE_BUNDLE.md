# Docling Pipeline v1.0.0 - Release Bundle

## Release Artifacts

### Core Files

- `RELEASE.md` - Release documentation
- `README.md` - Quick start guide
- `docker-compose.yml` - Service orchestration
- `.env.example` - Configuration template

### Services

- `ingest_api/` - FastAPI ingestion service
- `docling_worker/` - Document parsing worker
- `embed_worker/` - Embedding generation worker

### Libraries

- `lib/canonical.py` - RFC8785 canonicalization
- `lib/normalize.py` - Text and vector normalization

### Schemas

- `schemas/doc.normalized.v1.schema.json`
- `schemas/chunk.embedding.v1.schema.json`

### Testing

- `test_determinism.py` - Comprehensive test suite
- `replay_test.py` - Simple replay test
- `test_document.txt` - Test data
- `compute_weights_hash.py` - Model hash utility

## Cryptographic Anchors

### Model Weights

```
Model: sentence-transformers/all-mpnet-base-v2
SHA256: 4509c1ee9d2c8edeefc99bd9ca58668916bee2b9b0cf8bf505310e7b64baf670
Parameters: 199
Embedding Dimension: 768
```

### Pipeline Configuration

```
PIPELINE_VERSION=v1.0.0
DOCLING_VERSION=2.9.0
NORMALIZER_VERSION=norm.v1
CHUNKER_VERSION=chunk.v1
EMBEDDER_MODEL_ID=sentence-transformers/all-mpnet-base-v2
WEIGHTS_HASH=sha256:4509c1ee9d2c8edeefc99bd9ca58668916bee2b9b0cf8bf505310e7b64baf670
```

## Deployment Instructions

### 1. Prerequisites

- Docker & Docker Compose
- 4GB+ RAM
- Python 3.11+ (for testing)

### 2. Deploy Pipeline

```bash
cd pipeline
docker-compose up --build -d
```

### 3. Verify Health

```bash
curl http://localhost:8000/health
```

### 4. Run Determinism Tests

```bash
# Install test dependencies
pip install requests

# Run test suite
python test_determinism.py test_document.txt
```

## Expected Test Results

### Replay Determinism Test

- ✓ Same document ingested twice
- ✓ Identical chunk counts
- ✓ Identical chunk integrity hashes
- ✓ Deterministic processing verified

### Hash Chain Integrity Test

- ✓ All entries have integrity_hash
- ✓ Chain links verified (prev_ledger_hash)
- ✓ No tampering detected

## Verification Checklist

- [ ] Docker services start successfully
- [ ] Health check returns 200 OK
- [ ] Document ingestion completes
- [ ] Embeddings stored in Qdrant
- [ ] Ledger entries created
- [ ] Replay test passes
- [ ] Hash chain integrity verified

## Known Issues

None at release time.

## Support

For issues or questions, refer to:

- `RELEASE.md` - Full release documentation
- `README.md` - Usage guide
- Ledger file - Audit trail

---

**Release Date**: 2026-01-26  
**Version**: v1.0.0  
**Status**: Release Candidate

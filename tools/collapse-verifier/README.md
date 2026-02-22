# Collapse Verifier

Minimal verifier for CollapseReceipt batches: canonicalize, merkle root,
proof verification, optional signature check.

## Install
Node 18+ required.

```bash
npm ci
```

## Quick test (CI-friendly)
1. Populate `test/fixtures/batch.json` with real `merkle_root` and per-item
   `merkle.proof_path` if available.
2. Run:

```bash
node src/index.js --batch test/fixtures/batch.json --expect test/expected/receipt.json
```

Exit codes:
- `0` success (expected match)
- `3` verification mismatch
- `2` usage error

## CI snippet (example)

```yaml
- name: Verify collapse batch
  run: |
    npm ci
    node src/index.js --batch test/fixtures/batch.json --expect test/expected/receipt.json
```

## Notes
- Canonicalization follows a deterministic key-sorted JSON approach.
- Merkle uses SHA-256(left+right) pairing; odd nodes are duplicated.
- Signature verification expects a DER/SPKI public key; adapt as needed for raw ed25519 keys.

# Sentinel ledger

Ledger assets capture immutable audit trails for capsule freezes and CI attestations.

## Staging directories
- `batches/` – destination for Merkle-rooted capsule batches produced by `hash_gen_scroll.py`. Each run creates a dated folder
  containing `manifest.json`, per-artifact `.sha256` files, and the canonical capsule payload.
- `events/` – append-only NDJSON logs used by CI pipelines to record governance events, step transitions, and approvals.
- `proofs/` – reserved for higher-level ledger snapshots or signatures derived from batch runs.

Empty `.gitkeep` files live in each directory to document the intended structure without committing generated artifacts.

## Handshake ledger target convention
Handshake witnesses should be written under `sentinel/ledger/events/` using an append-only file such as:

- `sentinel/ledger/events/handshake.ndjson`

Each appended line is one canonical UTF-8 JSON object plus a trailing `\n` (NDJSON). Writers must emit each line in a single write
call and reject partial writes.

### Expected NDJSON line schema
Each line should represent one chained handshake receipt:

```json
{
  "type": "handshake.receipt",
  "digest": "<sha256 hex digest>",
  "prev": "<sha256 hex digest or null>",
  "payload": { "...": "wall-clock fields excluded" },
  "witness": {
    "handshake.bound": {
      "digest": "<sha256 hex digest>",
      "canonical_payload": "<canonical JSON string>",
      "prev": "<sha256 hex digest or null>"
    }
  }
}
```

Hashed surfaces (payload canonicalization + digest inputs) must exclude wall-clock fields.

## Generating a batch
Use the provided helper to hash inputs and emit ledger entries:

```bash
python3 hash_gen_scroll.py public/hud --out-dir sentinel/ledger/batches --events sentinel/ledger/events/events.ndjson
```

The script computes file digests, derives a Merkle root, writes the canonical capsule manifest, and appends an event record. All
outputs land under the directories above to preserve an immutable trail for the Sentinel.

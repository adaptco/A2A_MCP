# Sovereignty Log + Hash Chain

## Event schema
Each emitted transition or gate event is recorded as a deterministic sovereignty event:

```json
{
  "sequence": 7,
  "event_type": "gate.c5",
  "state": "validated",
  "payload": {"passed": true},
  "prev_hash": "<sha256 hex>",
  "hash_current": "<sha256 hex>"
}
```

## Canonicalization rules
1. Serialize only logical fields (`sequence`, `event_type`, `state`, `payload`, `prev_hash`).
2. Use canonical JSON with sorted keys and compact separators.
3. Compute `hash_current = sha256(canonical_json(event_without_hash_current))`.
4. Do not include wall-clock timestamps in the fingerprint payload.
5. Never use Python `hash()` for deterministic IDs/seeding.

## Verification procedure
1. Start `expected_prev_hash = ""`.
2. Iterate events by `sequence` order.
3. Confirm `event.prev_hash == expected_prev_hash`.
4. Recompute hash from canonical payload and compare with `hash_current`.
5. Set `expected_prev_hash = hash_current` and continue.
6. Fail verification on the first mismatch (broken chain or tampered payload).

## Operational guidance
- Emit sovereignty events for **all** state transitions and all gate results.
- Emit `pipeline.halted` when any hard-stop gate fails.
- Emit `export.completed` and `commit.complete` only after `validation.passed`.
- Include sovereignty chain and verification result in each run bundle.

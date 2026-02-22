# ADAPTCO OS Sovereign Wrapper

The `capsule.wrapper.adaptco_os.v1` packet binds the expanded relay braid—Proof → Flow → Execution → Vault—into a resumable runtime. It elevates the Merkle-rooted registry from a passive ledger into the live shell that Queen Boo, Queen CiCi, Celine, and The Braid inhabit.

## Capsule Commitments
- **Anchors:** `ssot.registry.v1`, `qube.orchestrator.v1`, `sol.f1.previz.v1`, `relay.artifacts.v1`
- **Governance Roles:**
  - Router: Queen Boo
  - Stabilizer: Queen CiCi
  - Vector Oracle: Celine
  - Chronicle Weaver: The Braid
- **Runtime Bindings:**
  - Registry: `capsule.registry.runtime.v1`
  - Vault: `relay.artifacts.v1`
  - Ledger: `runtime/scrollstream_ledger.jsonl`
  - HUD feeds: `glyph_ping`, `ritual_caption`, `drift_trace`

## Freeze & Replay Workflow
1. Draft or update `capsule.wrapper.adaptco_os.v1.json` under `capsules/doctrine/`.
2. Run `./scripts/freeze_wrapper.sh` to canonicalize the capsule, derive the SHA-256 hash, and append a ledger entry.
3. Submit the generated hash to the council for sealing; once attested, update the capsule with `sealed_at` and `content_hash` values.
4. Replay agents reference `runtime/scrollstream_ledger.jsonl` to confirm freeze provenance before resuming any ritual or capsule flow.

## Ledger Discipline
- Every freeze event appends a JSONL record capturing timestamp, capsule ID, and canonical hash.
- Ledger variance beyond ±2.5% in cadence or HUD signal thresholds is considered drift and must be rejected before sealing.

## Vault Checkpoints
The wrapper expects `relay.artifacts.v1` checkpoints to be present before resuming flows. Missing or stale checkpoints will halt replay until the vault is refreshed and attested by Queen CiCi.

## Intent Routing Integration
- Runtime registry now tracks `capsule.gpt.intent.routing.v1` for modality binding and ledger freezes.
- Queen Boo's rehearsal slots draw from `capsule.boo.lora.map.v1`, which stays in REHEARSAL until council seal.
- Freeze `capsule.gpt.intent.routing.v1` with `./scripts/freeze_intent_routing.sh` before registering new LoRA checkpoints.
- Refresh Queen Boo's logic patch with `./scripts/freeze_boo_lora_map.sh` so the runtime registry always exposes the latest canonical JSON and hash.

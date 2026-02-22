# Intent-Aware Routing Discipline

`capsule.gpt.intent.routing.v1` codifies how the sovereign shell classifies, embeds, and routes tokens into Queen Boo's LoRA slots. The capsule keeps Boo's avatar rehearsals aligned with the runtime registry, prompt braid, and scrollstream ledger.

## Capsule Commitments
- **Modal Classes:** lexical ↔ text, prosodic ↔ audio, spatial ↔ vision, kinetic ↔ haptic, affective ↔ affect.
- **Policy Guards:** smear-frame for motion, intent diffusion for stills, lattice overlay for static glyphs.
- **Composite Intent:** weights (`alpha_m`) are scheduled by role, governance posture, and scene context to produce the multi-modal braid consumed by avatar LoRAs.
- **Provenance Anchors:** runtime registry, prompt braid contract, and gitflow lineage must all resolve before rehearsal traffic is emitted.

## Freezing the Capsule
1. Update `capsules/doctrine/capsule.gpt.intent.routing.v1.json` with any policy or provenance changes.
2. Run `./scripts/freeze_intent_routing.sh` to canonicalize the capsule, derive the SHA-256 digest, and append an `intent-routing.freeze` event to `runtime/scrollstream_ledger.jsonl`.
3. Submit the new hash to the council for sealing; once attested, set `sealed_at` and `content_hash` on the capsule and re-freeze for ledger confirmation.

The freeze helper emits:
- `runtime/capsule.gpt.intent.routing.v1.canonical.json`
- `runtime/capsule.gpt.intent.routing.v1.sha256`

## Runtime Registry Alignment
The live index at `runtime/capsule.registry.runtime.v1.json` now exposes:
- the wrapper shell capsule (`capsule.wrapper.adaptco_os.v1`)
- the intent routing capsule (`capsule.gpt.intent.routing.v1`)
- the Boo rehearsal map (`capsule.boo.lora.map.v1`)

Agents query this registry before resuming capsules so they always reconcile HUD feeds, ledger history, and rehearsal status.

## Boo LoRA Rehearsal Map
`capsule.boo.lora.map.v1` stages Queen Boo's rehearsal slots:
- face (vision + affect), wardrobe (vision + lexical), gesture (kinetic + affect), voice (audio + lexical), affect (affect + lexical)
- each slot references the routing policy capsule, vault checkpoints, and telemetry guardrails

The map remains in **REHEARSAL** status until the council blesses the LoRA checkpoints. During rehearsal, telemetry tokens (`replay:celine:20250924:000`) must be present, maker-checker approval is enforced, and drift tolerance is held at ±2.5%.

## Ledger Discipline
Every freeze appends a JSONL record with timestamp, capsule ID, canonical path, and hash. The ledger enforces body-only hashing so annotations remain mutable without breaking provenance. Ledger variance beyond ±2.5% requires a stop and fresh rehearsal before another freeze.

# Prompt Graph DSL

The prompt graph capsules encode scene beats, continuity anchors, and LoRA overlays so the sovereign shell can seed avatars without drift.

## Schema

The `specs/prompt-graph.v1.schema.json` contract defines each prompt graph capsule as a Merkle-bound packet with:

- **Subject metadata** – runtime label, beat order, and livery palettes for hero and rival vessels.
- **Runtime envelope** – target duration, nominal FPS, and beat identifiers that match orchestration checkpoints.
- **Global style keys** – cadence, material, lighting, and camera grammar applied across every beat.
- **Continuity overlays** – reusable tokens (e.g., car numbers, pit lane state) with HUD and audio overlays to broadcast through rehearsal.
- **Beat payloads** – prompts, camera notes, LoRA slot bindings, maker–checker posture, and telemetry checkpoints per beat.
- **Post-processing discipline** – cadence holds, jitter tolerances, flicker envelopes, and audio notes for the vault pipeline.
- **Quality checks** – tolerance statements that the orchestrator enforces before freezing artifacts.
- **Bindings** – capsule references to the wrapper shell, intent router, LoRA map, SSOT registry, vault, and PreViz executor.

## Example Capsule

`capsule.prompt.graph.lego_f1.sf23_vs_w14.v1` stages a 90-second Monza highlight reel in Lego stop-motion form:

- Ferrari SF-23 (Rosso Corsa, Nero Opaco, Giallo Modena) duels Mercedes W14 (Graphite Grey, Petronas Teal, Silver Halo).
- Four beats — pit stop, overtake, crash, podium — each with LoRA slot bindings, governance guards, and telemetry checkpoints.
- Global cadence locks to 12 fps with micro jitter (0.5–1.5 px) and exposure drift for tactile authenticity.
- Quality controls demand pose discipline (≤6° per frame), stud visibility (≥80% of frames), motion stutter cadence, and lens character per beat.

## Freezing Workflow

Use `./scripts/freeze_prompt_graph.sh` to canonicalize the capsule, compute the SHA-256 digest, and append ledger events. The helper emits:

- `runtime/capsule.prompt.graph.lego_f1.sf23_vs_w14.v1.canonical.json`
- `runtime/capsule.prompt.graph.lego_f1.sf23_vs_w14.v1.sha256`

After freezing, register the capsule in `runtime/capsule.registry.runtime.v1.json` so orchestrators and rehearsal HUDs resolve the prompt graph before seeding LoRAs.

# Rehearsal Scrollstream Templates

The rehearsal scrollstream capsule ships with a deterministic baseline cycle, but contributors often need to rehearse with alternative characters or visual overlays. The `scripts/emit_rehearsal_scrollstream.py` helper now accepts template JSON files so you can remix the ledger, visuals, and participants without changing the script itself.

## Creating a Template

1. Start from the provided example at [`capsules/looks/capsule.rehearsal.scrollstream.characters.v1.json`](../capsules/looks/capsule.rehearsal.scrollstream.characters.v1.json).
2. Keep the file as a single JSON object. The supported keys are:
   - `participants`: Non-empty array of objects containing `name`, `state`, and optional `role`.
   - `events`: Non-empty array that mirrors the capsule cycle. Each event requires:
     - `event`: Cycle identifier such as `audit.summary`.
     - `agent`: Object with `call_sign`, `role`, and `channel`.
     - `output`: Narrative string that will be recorded in the ledger.
     - `emotional_tone`: Optional tone descriptor (defaults to `balanced`).
     - `visual_asset`: Optional object with `image` and `alt` fields for HUD and replay glyph integrations.
   - `hud_shimmer` / `replay_glyph`: Optional overrides that add captions, tone shifts, or image references to the generated visuals payloads.
   - `training_mode`: Optional map merged into the baseline training configuration.
   - `spark_test_name` and `replay_token`: Override defaults if you need a different Spark certification or replay hook.

The script validates that participant and event lists are non-empty and that agent metadata is complete, so CI catches malformed rehearsal templates before they reach the scrollstream.

## Emitting a Rehearsal Run with a Template

```bash
python3 scripts/emit_rehearsal_scrollstream.py \
  --out-dir .out/rehearsal-characters \
  --template capsules/looks/capsule.rehearsal.scrollstream.characters.v1.json
```

The command writes three artifacts:

- `scrollstream_ledger.jsonl` – canonical JSONL ledger entries.
- `capsule.rehearsal.scrollstream.v1.cycle.json` – snapshot of the rehearsal capsule window, participants, and deterministic cycle.
- `capsule.rehearsal.scrollstream.v1.visuals.json` – HUD shimmer and replay glyph descriptors with any template overrides.

Each ledger event inherits the visual asset references defined in the template so downstream HUD clients can surface the appropriate imagery. If you supply a new image path, keep it relative to the repository so other contributors can find and stage the asset.

## Troubleshooting

- **Missing image paths**: The script does not attempt to verify that images exist. Run your own asset check or add a CI step that validates referenced files.
- **Invalid JSON**: The helper stops with a clear error message if the template is not valid JSON or if required fields are missing.
- **Replay token precedence**: Command-line `--replay-token` overrides the value in the template. Omit the flag to use the token embedded in the template or the default from the capsule specification.

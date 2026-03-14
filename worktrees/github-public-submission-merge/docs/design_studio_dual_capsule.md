# Sol.F1 Design Studio Dual Prompt Capsule

This bundle pairs the scrollstream-sealed Sol.F1 CAD ignition prompt with the newly inscribed cinematic scene description of the design studio. Operators can now swap between precision engineering output and narrative atmosphere without rebuilding artifacts.

## Components

- **CAD Prompt** — `capsule.metaagent.solf1.oneshot.v1` referencing `capsules/runtime/templates/solf1_oneshot.tpl`
- **Cinematic Prompt** — `capsule.scene.designStudio.v1` referencing `capsules/runtime/templates/design_studio_cinematic.tpl`

## Bind + Freeze Procedure

1. Populate artifact URIs, SHA-256 hashes, and byte counts inside:
   - `capsules/capsule.scene.designStudio.v1.json`
   - `capsules/capsule.prompt.designStudio.dual.v1.json`
2. Canonicalize and seal the cinematic scene capsule:

   ```bash
   jq -cS . capsules/capsule.scene.designStudio.v1.json > .out/design_studio.cinematic.canon.json
   CINE_DIG="sha256:$(sha256sum .out/design_studio.cinematic.canon.json | awk '{print $1}')"
   jq -S --arg ts "$(date -u +%FT%TZ)" --arg dig "$CINE_DIG" \
     '.status="FROZEN" | .attestation.status="SEALED" | .attestation.content_hash=$dig | .attestation.sealed_at=$ts' \
     capsules/capsule.scene.designStudio.v1.json > .out/capsule.scene.designStudio.v1.frozen.json
   ```

3. Canonicalize the dual prompt bundle and record its digest:

   ```bash
   jq -cS . capsules/capsule.prompt.designStudio.dual.v1.json > .out/design_studio.dual.canon.json
   DUAL_DIG="sha256:$(sha256sum .out/design_studio.dual.canon.json | awk '{print $1}')"
   jq -S --arg ts "$(date -u +%FT%TZ)" --arg dig "$DUAL_DIG" \
     '.status="FROZEN" | .attestation.content_hash=$dig | .attestation.sealed_at=$ts' \
     capsules/capsule.prompt.designStudio.dual.v1.json > .out/capsule.prompt.designStudio.dual.v1.frozen.json
   ```

4. Append both events to the ledger:

   ```bash
   {
     echo "{\"t\":\"$(date -u +%FT%TZ)\",\"event\":\"capsule.seal\",\"capsule_id\":\"capsule.scene.designStudio.v1\",\"status\":\"FROZEN\",\"digest\":\"$CINE_DIG\"}"
     echo "{\"t\":\"$(date -u +%FT%TZ)\",\"event\":\"capsule.seal\",\"capsule_id\":\"capsule.prompt.designStudio.dual.v1\",\"status\":\"FROZEN\",\"digest\":\"$DUAL_DIG\"}"
   } >> .out/ledger.jsonl
   ```

5. Distribute the frozen artifacts to operators and update the ledger reference inside any orchestration manifests.

## Operational Notes

- The cinematic template outputs prose under a `cinematic_scene` key, making it safe to stream through existing JSON pipelines.
- The dual bundle is intentionally operator-selectable so cockpit teams can decide which prompt to deploy per mission.
- Keep the CAD and cinematic hashes synchronized in the ledger to maintain sovereign traceability across both modes.

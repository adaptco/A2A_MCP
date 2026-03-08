# Sol.F1 One-Shot Capsule Runbook

This runbook captures the staging scaffold for `capsule.metaagent.solf1.oneshot.v1` and the steps required to freeze it once the artifact URIs and hashes are bound.

## Capsule Scaffold

The staged manifest lives at [`capsules/capsule.metaagent.solf1.oneshot.v1.json`](../capsules/capsule.metaagent.solf1.oneshot.v1.json). Update the placeholder S3 URIs, SHA-256 digests, and byte sizes with the production artifact values prior to freezing.

The prompt template referenced by the manifest is stored at [`capsules/runtime/templates/solf1_oneshot.tpl`](../capsules/runtime/templates/solf1_oneshot.tpl). Render systems should upload this template to object storage and record the resulting location and digest under the capsule's `artifacts` block.

## Bind Weights and Artifacts

1. Select final mixture weights (defaults are `w_cici = 0.55`, `w_boo = 0.45`).
2. Generate the expert embedding vectors and upload them alongside the prompt template and manifest artifacts.
3. Replace the `REPLACE_WITH_*` placeholders in the capsule JSON with the deployed artifact URIs and digests.

## Freeze Procedure

With placeholders resolved, execute the canonical freeze sequence to seal the capsule:

```bash
jq -cS . capsules/capsule.metaagent.solf1.oneshot.v1.json > .out/solf1.oneshot.canon.json
DIG="sha256:$(sha256sum .out/solf1.oneshot.canon.json | awk '{print $1}')"
jq -S --arg ts "$(date -u +%FT%TZ)" --arg dig "$DIG" \
  '.status="FROZEN" | .attestation.sealed_at=$ts | .attestation.content_hash=$dig' \
  capsules/capsule.metaagent.solf1.oneshot.v1.json \
  > .out/capsule.metaagent.solf1.oneshot.v1.frozen.json

echo "{\"t\":\"$(date -u +%FT%TZ)\",\"event\":\"capsule.seal\",\"capsule_id\":\"capsule.metaagent.solf1.oneshot.v1\",\"status\":\"FROZEN\",\"digest\":\"$DIG\"}" \
  >> .out/ledger.jsonl
```

The resulting frozen manifest captures the authoritative digest and timestamps required for ledger attestation.

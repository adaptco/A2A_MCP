#!/usr/bin/env bash
# Run local rehearsal checks prior to generating a preview sequence.
set -euo pipefail

python scripts/validate_ssot.py manifests/ssot.yaml
python scripts/check_drift.py manifests/ssot.yaml manifests/deployed.yaml || true

cat <<'MSG'
Preview rehearsal scaffolding is ready.
Use your preferred renderer to materialize the selector.preview.bundle.v1 prompts:
  - rupture.flare (irony shimmer + spark trace)
  - restoration.loop (breath sync + glyph fidelity)
  - mesh.response (empathy shimmer + echo match)
MSG

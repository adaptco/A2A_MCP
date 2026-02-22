# World Engine Epoch Release Artifact (Draft)

This draft provides a structured, neutral, and auditable "epoch release" artifact
with a minimal YAML spec and companion bash + Python scaffolds. It is intentionally
bounded to avoid speculative physics metaphors and aligns with ZERO-DRIFT practices
by keeping inputs, outputs, and invariants explicit.

## 1. Natural-Language Summary

**Goal**: Define an epoch release for a sandboxed agentic platform that can run a
physics-backed game simulation ("Parker's Sandbox: Jurassic Pixels"), expose a
websocket interface, and be embedded in a React/HTML container for HITL
verification.

**Scope**:
- Declarative YAML describing the release.
- Minimal bash runner that generates a kernel stub and starts a websocket server.
- Python stub for kernel metadata + deterministic seed logging.

**Out of scope**:
- Any non-deterministic or undefined physical metaphors.
- Real user data or personalization.

## 2. Epoch Release YAML (Artifact)

```yaml
release:
  name: "jurassic-pixels-epoch-0"
  version: "0.1.0"
  epoch: "2025-01"
  status: "draft"
  description: "Sandboxed physics-game OS kernel scaffold with websocket I/O."

inputs:
  registries:
    - "ssot://registry/truthful_inputs"
    - "ssot://registry/trusted_uris"
  payload_contract:
    required:
      - "kernel_seed"
      - "simulation_profile"
      - "client_caps"
    metadata_fields:
      - "content_id"
      - "sha256_payload"
      - "council_attestation_id"
      - "run_id"

kernel:
  name: "game-os-kernel"
  determinism:
    seed_source: "kernel_seed"
    drift_threshold: 0.0
  physics_engine:
    name: "lightweight-physics"
    mode: "deterministic"
  modules:
    - id: "world.simulation"
      purpose: "step world state"
    - id: "agent.lifecycle"
      purpose: "task scheduling + tool routing"

network:
  websocket:
    host: "0.0.0.0"
    port: 8787
    path: "/ws"

ui:
  react_embed:
    enabled: true
    container: "html-docker"
    assets_path: "ui/jurassic-pixels"

verification:
  hitl:
    enabled: true
    checklist:
      - "deterministic seed logged"
      - "schema validated"
      - "websocket handshake verified"
```

## 3. Bash Runner (Scaffold)

```bash
#!/usr/bin/env bash
set -euo pipefail

KERNEL_DIR="runtime/jurassic_pixels"
ARTIFACT_DIR="artifacts/jurassic_pixels"

mkdir -p "$KERNEL_DIR" "$ARTIFACT_DIR"

python "$KERNEL_DIR/kernel_stub.py" \
  --seed "demo-seed-001" \
  --out "$ARTIFACT_DIR/kernel_manifest.json"

echo "[ok] kernel manifest written to $ARTIFACT_DIR/kernel_manifest.json"
```

## 4. Python Kernel Stub (Scaffold)

```python
import argparse
import json
from datetime import datetime
from hashlib import sha256


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    payload = {
        "kernel": "game-os-kernel",
        "seed": args.seed,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }
    payload["sha256"] = sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


if __name__ == "__main__":
    main()
```

## 5. Next Step

If this draft is acceptable, we can:
1. Register the release YAML under a manifest entry (e.g., `manifests/`).
2. Create the kernel stub file in `runtime/`.
3. Add a minimal websocket server and a React container stub.

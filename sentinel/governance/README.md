# Sentinel governance

Governance assets define how manifests are frozen, signed, and promoted.

## Canonical artifacts
`governance/` stores the canonicalized payloads, their SHA-256 scrolls, and detached signatures:
- `avatar_bindings.v1.canonical.json` – canonical JSON produced by the freeze scripts.
- `avatar_bindings.v1.hash` – the Merkle root anchor emitted during freeze.
- `avatar_bindings.v1.sig` – Ed25519 signature written with the protocol test key at `governance/test-ed25519.pem`.

## Tooling
The shell and Python helpers in `scripts/` automate canonicalization and signing:
- `canonicalize_manifest.py` performs deterministic deep sorting for JSON manifests.
- `freeze_avatar_bindings.sh` coordinates canonicalization, hashing, and ledger append steps.
- `sign_bindings.sh` signs manifests using Ed25519 keys.

## Automated enforcement
`.github/workflows/` contains CI pipelines that replay the freeze steps, enforce schema validation, and emit governance proofs
before merges. This directory should be updated alongside any changes to the governance scripts.

# VH2 Ledger Verifier v0.1 (Normative Snapshot)

This document freezes the v0.1 byte-source and genesis contracts for independent ledger verification.

## Canonical Byte Sources

- `DRIFT_CANON_BYTES = UTF8(JCS(artifact.judgment))`
- `CORPUS_CANON_BYTES` supports:
  - Embedded mode: `UTF8(JCS(artifact.inputs.observed_corpus))`
  - External mode: blob bytes from `artifact.inputs.corpus_ref.uri`, where blob content must be canonical JCS UTF-8 bytes for corpus object.

## Genesis Constant (Frozen)

`prev_line_sha256` for line 0 is:

`GENESIS_VH2_DRIFT_LEDGER_V1`

This value is intentionally domain-specific to reduce cross-ledger confusion.

## Schema Artifacts

Normative JSON Schema files for this contract:

- `pipeline/schemas/vh2_drift_ledger_checkpoint.v1.schema.json`
- `pipeline/schemas/vh2_drift_ledger_line.v1.schema.json`
- `pipeline/schemas/vh2_drift_artifact.v2.schema.json`

## Notes

- Canonicalization spec is constrained to `RFC8785_JCS`.
- Signature mode is constrained to `VERIFIABLE_NONDETERMINISTIC` with canonical-bytes-only scope.
- The artifact schema includes conditional requirements for corpus representation:
  - `EMBEDDED` => `observed_corpus` required and `corpus_ref` absent.
  - `EXTERNAL_REF` => `corpus_ref` required and `observed_corpus` absent.

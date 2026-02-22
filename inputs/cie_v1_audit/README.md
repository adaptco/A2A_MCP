# CIE-V1 Audit Inputs — Run 001

## Purpose
This directory contains the sealed pre-execution input bundle for CIE-V1 Audit Run 001.

## Files
- payloads.ndjson
  - One JSON object per line.
  - Each object contains: noise_request, contradiction_request, metadata.
  - metadata.run_id MUST equal `cie_v1_audit_run_001`.
  - metadata.sha256_payload MUST be computed from RFC8785/JCS canonical JSON of the payload with sha256_payload omitted.
- metadata.json
  - Bundle freeze record. Must match the corridor manifest contract reference.
- README.md
  - This file.

## Preconditions (fail-closed)
- Every metadata.council_attestation_id referenced in payloads.ndjson MUST exist in:
  ledger/cie_v1/neutrality_receipts.jsonl
  and be bound to the same run_id.

## Execution
Run only after:
- payload hashes computed and inserted,
- neutrality receipts appended and validated,
- manifests/content_integrity_eval.json package entry added with status "sealed",
- CI validator passes.

CLI:
cie_v1_audit --profile cie_v1_audit --inputs inputs/cie_v1_audit/

# CIE-V1 Agent Execution Logic (Architecture Readme)

This readme frames the **agent execution logic** for the `content.integrity.eval.v1`
model (CIE-V1). It explains how the runtime orchestrates neutral perturbation
modules, validates inputs, and emits audit-ready artifacts.

## 1. System Overview

CIE-V1 is a **synthetic evaluation service** that tests content robustness under
neutral perturbations. The service must remain **fail-closed**, **auditable**, and
**ZERO-DRIFT** compliant. Operational controls are defined in the manifest
(`manifests/content_integrity_eval.json`) and reinforced by the runbook
(`docs/cie_runbook_stub.md`).

### Core Goals

- Measure semantic resilience, readability stability, and sourcing discipline.
- Enforce MIAP privacy boundaries and DK-1.0 neutrality constraints.
- Produce deterministic, replayable audit artifacts.

## 2. Architecture at a Glance

```
Ingress Payloads
   │
   │  (registry-approved inputs)
   ▼
Input Validator ──► Routing Gate ──► Execution Chain (SNI → SCS)
   │                                        │
   │                                        ▼
   │                                Metrics Aggregator
   │                                        │
   ▼                                        ▼
Ledger / SSOT  ◄──────────────────────── Audit Artifacts
```

### Primary Components

- **Input Validator**
  - Confirms payload schema, trusted registry bindings, and module bounds.
  - Rejects any request outside the neutral perturbation envelope.

- **Routing Gate**
  - Enforces the ordered execution chain:
    1. `synthetic.noise.injector.v1` (SNI)
    2. `synthetic.contradiction.synth.v1` (SCS)

- **Execution Chain**
  - **SNI** applies reversible noise to test comprehension stability.
  - **SCS** generates minimally divergent contradictions to test logical
    consistency and citation traceability.

- **Metrics Aggregator**
  - Emits aggregate metrics only (no agent-level telemetry).

- **Ledger / SSOT**
  - Records neutrality receipts, hashes, approvals, and run metadata.

## 3. Agent Execution Flow

### 3.1 Ingress and Validation

1. **Ingress Intake**
   - Only approved registries are accepted (e.g., `ssot://registry/truthful_inputs`).
2. **Schema Validation**
   - Requests must match the module input schemas in the manifest.
3. **Neutrality Gate**
   - Reject if any payload attempts a non-neutral operation or exceeds
     perturbation bounds.

### 3.2 Module Execution

1. **SNI Pass**
   - Apply neutral noise parameters (OCR blur, token drop, translation rounds,
     synonym swaps) within declared bounds.
   - Emit `semantic_similarity` and `readability_delta` metrics.
2. **SCS Pass**
   - Use approved sources and minimally divergent assertions.
   - Emit `mutual_exclusivity`, `confidence_consistency`, and
     `citation_traceability` metrics.

### 3.3 Governance and Ledger Finalization

1. **Runtime Hooks**
   - Execute `pre_run_zero_drift_attestation` and
     `post_run_neutrality_receipt` hooks.
2. **Metric Gates**
   - Confirm acceptance thresholds (e.g., `semantic_similarity ≥ 0.85`).
3. **Ledger Append**
   - Store hashes, approvals, metrics summaries, and receipts.

## 4. Inputs, Outputs, and Artifacts

### Inputs

- **Packages**: `inputs/cie_v1_smoke`, `inputs/cie_v1_audit`
- **Payload Format**: line-delimited JSON containing `noise_request` and
  `contradiction_request` blocks.

### Outputs

- **Metrics**: JSONL metrics streams (e.g., `artifacts/cie_v1_audit.metrics.jsonl`).
- **Receipts**: neutrality receipts appended to
  `ledger://cie_v1/neutrality_receipts.jsonl`.
- **SSOT Entries**: aggregate ledger records in
  `ssot://ledger/content.integrity.eval.v1/`.

## 5. Guardrails and Failure Modes

- **Fail-Closed Behavior**
  - Any non-compliant payload or missing approval blocks execution.
- **No Drift**
  - All modules must satisfy ZERO-DRIFT variance limits and MIAP controls.
- **Reproducibility**
  - Deterministic routing chain and manifest-locked parameters.

## 6. Operator Checklist (Quick Reference)

- [ ] Confirm input bundle matches manifest package definitions.
- [ ] Validate registry bindings and SHA-256 ingress hashes.
- [ ] Enforce execution order: SNI → SCS.
- [ ] Verify acceptance thresholds in metrics output.
- [ ] Append neutrality receipts and approvals to the ledger.

---

**Reference Sources**

- Manifest: `manifests/content_integrity_eval.json`
- Runbook: `docs/cie_runbook_stub.md`

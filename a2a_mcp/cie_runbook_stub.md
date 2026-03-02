# Content Integrity Evaluation (CIE-V1) Runbook

## Overview
CIE-V1 validates content robustness while honoring the ZERO-DRIFT mandate. The stack now runs on **neutral perturbation models** only:
- **synthetic.noise.injector.v1** adds bounded, neutral perturbations to gauge drift sensitivity.
- **synthetic.contradiction.synth.v1** generates labeled contradictions to pressure-test claims without introducing unlabeled misinformation.

Everything is treated as a ceremony: **intake → ignition → binding → settlement** with receipts, hashes, and council attestations recorded at each gate.

## Operating modes
- **Evaluate**: Ingest source content, apply neutral noise, measure drift, and synthesize contradictions for robustness scoring.
- **Export**: Emit capsule events and robustness metrics to downstream audit ledgers.

## Inputs
- `source_content`: canonical text or structured payload under evaluation (canonicalize before ingestion).
- `perturbation_profile`: constraints for noise injection (entropy budget, allowed token scopes).
- `claim_graph`: optional structured claims for contradiction synthesis.
- `contradiction_policy`: labeling and guardrails for synthetic contradictions.

## Outputs
- `content_with_neutral_noise`: perturbed but semantically aligned payload plus SHA-256 hash.
- `synthetic_contradictions`: labeled contradiction set with linkage to original claims and per-item hashes.
- `robustness_score`: roll-up metric derived from drift sensitivity and contradiction coverage.
- Capsule events with lineage (`capsule_id`, `capsule_ref`), Merkle anchors, and council attestations for audit.

## Ritual flow (per batch)
1. **Intake**: Normalize inputs, capture SHA-256 digests, and register capsule IDs.
2. **Ignition**: Run `synthetic.noise.injector.v1` within entropy budget; emit perturbation receipts and neutrality verdicts.
3. **Binding**: Run `synthetic.contradiction.synth.v1` against normalized claim graph; enforce coherence gates and label contradictions.
4. **Settlement**: Fold receipts into Merkle roots, obtain dual council attestations, and emit ledger entries with capsule refs.

## First CIE-V1 audit run
1. Validate manifest deployment: confirm both modules are active and have `replaces` tags for legacy CNE/FSV paths.
2. Prepare inputs: supply `source_content`, tuned `perturbation_profile`, and optional `claim_graph` plus `contradiction_policy`.
3. Execute evaluate flow via `capsules/content-integrity/eval.v1` interface.
4. Confirm outputs: review `robustness_score`, neutrality verdicts, and contradiction labels.
5. Verify audit artifacts: ledger emits capsule events with hashes, Merkle roots, and ZERO-DRIFT compliance notes.

### Input definitions for the first official run
- `source_content` (required): Canonical JSON payload with deterministic ordering and UTF-8 normalization; include `capsule_id` an
d pre-run SHA-256 hash.
- `perturbation_profile` (required): Entropy budget ≤0.15 bits/token, permitted scopes (whitespace, punctuation), and neutraliza
tion labels for the noise injector.
- `claim_graph` (optional): Directed acyclic graph of claim nodes with stable IDs for contradiction synthesis.
- `contradiction_policy` (required when `claim_graph` provided): Label set for synthetic contradictions plus rejection rules for
 unlabeled inversions.

### Evidence to retain
- Intake receipt with capsule_id, capsule_ref, and hashes.
- Ignition receipt showing entropy budget proof for `synthetic.noise.injector.v1`.
- Binding receipt listing contradictions, labels, and per-item hashes.
- Settlement receipt with Merkle root and dual council attestations.

## Observability
- Metrics: `drift_score`, `neutral_noise_rate`, `contradiction_coverage`, `audit_pass_rate`, `merkle_settlement_latency`.
- Logging: Module invocations must include module id, input capsule references, guardrail outcomes, and hashes.
- Alerts: trigger on `drift_score` > threshold-neutral, missing neutrality tags on contradictions, or Merkle settlement lag.

## Safety and rollback
- If neutrality violations occur, disable the offending module and revert to the last settled Merkle root.
- Record rollback events and council approvals in the ledger for traceability.
- Re-run audit after remediation to confirm ZERO-DRIFT compliance.

## Change management
- Any model updates must retain neutral perturbation guarantees and pass contradiction labeling checks.
- Update the manifest and re-run the first-audit procedure for every model promotion, including regeneration of Merkle receipts.

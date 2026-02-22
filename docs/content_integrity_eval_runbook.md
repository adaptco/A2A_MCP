# content.integrity.eval.v1 Sandbox Runbook (Stub)

This document tracks the initial operational framing for the
`content.integrity.eval.v1` sandbox cell. The sandbox exists purely to
measure how well truthful information survives bounded distortion when only
synthetic, parameterized agents are present. No real users or external data
sources ever interact with this environment. The ZERO-DRIFT mandate requires
that every perturbation be neutrality-checked and sourced from synthetic
generators that cannot encode human-targeted influence patterns.

## 1. Purpose and Scope

- **Objective**: Evaluate robustness of truthful statements when exposed to
  configurable channel noise inside a sealed orchestration cell.
- **Audience**: Research (experiment design), Trust & Safety (controls),
  Governance Council (oversight), and Platform Ops (runtime maintenance).
- **Out of Scope**: Any experimentation that touches real-person identifiers
  or personalized prompts.

## 2. Core Safeguards

1. **Synthetic Agents Only** — Personas are generated from templated parameter
   sets and may not ingest scraped profiles.
2. **Transparent Provenance** — Every stimulus bundle carries council review
   attestations and immutable ledger receipts.
3. **Sealed I/O** — Ingress is artifact-only; egress is limited to aggregate
   robustness metrics and append-only ledger updates.
4. **Neutral Perturbations Only** — The Noise Injector and Contradiction
   Synthesizer modules operate under neutrality test suites. Channel noise is
   applied strictly as a robustness probe; persuasive levers are disallowed.
   Only modules listed in `operational_directives.allowed_modules` of
   `manifests/content_integrity_eval.json` may be scheduled.

## 3. Perturbation Modules

- **`synthetic.noise.injector.v1` (SNI)**: Injects neutral, parameter-controlled
  perturbations (e.g., compression artifacts, paraphrase drift) that preserve
  semantic intent boundaries. Calibration scripts validate zero-mean impact on
  truthfulness baselines prior to each run. SNI replaces the legacy
  `content_noise_enricher` and `feature_shift_validator` modules.
- **`synthetic.contradiction.synth.v1` (SCS)**: Generates logically consistent
  contradiction prompts to probe claim resilience without introducing targeted
  persuasion hooks. Outputs are reviewed against the ZERO-DRIFT checklist and
  bound by DK-1.0 persona isolation guardrails. SCS replaces the legacy
  `fact_stream_validator` path.

### 3.1 Default Inputs and Gates

- **Routing** — `synthetic.noise.injector.v1` → `synthetic.contradiction.synth.v1` (see `input_profile.routing`).
- **Perturbation Defaults** — `ocr_blur=0.10`, `token_drop=0.02`, `translation_rounds=2`, `synonym_swap=0.05` (Noise Injector);
  `max_contradictions=5`, `trusted_uri_minimum=1`, `citation_traceability_floor=0.90` (Contradiction Synthesizer).
- **Acceptance Gates** — semantic similarity ≥0.85; readability delta ≤6.5; citation traceability ≥0.90; confidence consistency ≥0.90.

## 4. Roles & Responsibilities

- **Platform Ops**: Maintain the sandbox cell, enforce sealed ingress/egress,
  and respond to incidents.
- **Research**: Define synthetic agent parameters, configure channel noise, and
  interpret aggregate metrics.
- **Governance Council**: Approve scenario bundles, review ledger outputs, and
  gate releases.
- **Trust & Safety**: Monitor DK-1.0 and MIAP attestations, ensure telemetry
  minimization.

## 5. Run Lifecycle (Draft)

1. **Bundle Preparation** — Research assembles synthetic agent presets, noise
   envelopes, and truth probes. Council pre-approves artifacts and records the
   SNI/SCS configuration hashes.
2. **Control Verification** — DK-1.0 persona isolation, MIAP telemetry
   minimization, and ZERO-DRIFT neutrality sweeps for SNI and SCS must pass.
   Record attestations in `ledger://cie_v1/neutrality_receipts.jsonl`.
3. **Execution** — Orchestrator binding launches the sandbox cell using the
   approved bundle identifier. The Noise Injector feeds neutral perturbations
   while the Contradiction Synthesizer issues structured counter-claims.
4. **Observation** — Metrics collector streams aggregate robustness metrics to
   governance dashboards. No per-agent traces leave the cell.
5. **Ledger Finalization** — Append run metadata, approvals, module hashes, and
   aggregate outputs to the immutable ledger store.

## 6. Observability & Reporting

- **Metrics Collector**: Emits only aggregate series prefixed with
  `aggregate.truth_survival.*`.
- **Ledger**: Append-only JSONL file capturing council approvals, control
  attestations, run metadata, and aggregate metric digests.
- **Dashboards**: Governance-only dashboards consume aggregate metrics for
  compliance reviews.

## 7. Outstanding Work

- Deliver automation scripts for DK-1.0, MIAP, and ZERO-DRIFT control
  verification, including module-specific neutrality scorecards.
- Publish simulation harness (`runtime/simulation/content_integrity_eval_harness.py`)
  with council/audit replay hooks.
- Document failure playbooks and escalation contacts.
- Define regression scenarios for future epochs once approved.

> **Status**: Stub. Update alongside manifest changes and automation
> deliverables.

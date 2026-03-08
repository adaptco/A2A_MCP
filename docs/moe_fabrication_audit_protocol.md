# MoE Fabrication & Reclamation Layer Audit Protocol

This protocol governs how the Mixture-of-Experts (MoE) Fabrication and Reclamation Layer
verifies large physical assets inside the simulated manufacturing environment before
they are released to the field. It maps the Kinetic Expert, Geometric Expert, and the
Inference/Gating console to repeatable controls so the white SUV exemplar remains the
canonical audit reference.

## 1. Objectives & Scope

- **Asset Integrity** – Confirm the manufactured asset's geometry and materials align
  with sealed design specifications to within the permitted tolerances.
- **Expert Cohesion** – Ensure the Kinetic (manipulation) and Geometric (inspection)
  experts execute in lockstep under the gating network's supervision with ZERO-DRIFT
  drift tolerance.
- **Release Readiness** – Produce a compliance score and artifact bundle that allows
  Council review to approve or reject asset deployment.

The protocol applies to every MoE fabrication run that hands a reclaimed or newly
fabricated asset to downstream capsules. No exceptions exist for priority or
expedited runs.

## 2. Roles & Responsibilities

| Role | Responsibilities |
| ---- | ---------------- |
| **Kinetic Expert** | Executes physical manipulations, torque tests, and dynamic alignment probes. Captures force telemetry, alignment error readings, and actuation logs. |
| **Geometric Expert** | Conducts high-resolution scans, validates surface topology, and tags structural stress indicators. Generates geometric deviation maps and confidence bands. |
| **Inference / Gating Console** | Orchestrates expert sequencing, verifies DK-1.0 persona isolation for automated subroutines, and aggregates metrics into the compliance dashboard. |
| **Governance Council** | Reviews audit bundles, verifies ledger integrity, and signs off on pass/fail outcomes (quorum: 4 of 6). |

## 3. Pre-Audit Checklist

1. **Ledger Lock** – Register the asset identifier, design revision hash, and
   manufacturing batch in `ssot://ledger/moe_fab_rec/ingress.jsonl`.
2. **Calibration Sweep** – Run the Kinetic and Geometric calibration suite. Record
   baseline alignment error (<0.25 mm) and scanner fidelity (>99.2% point cloud
   completeness).
3. **Safety Envelope** – Validate collision bounds, torque limits, and emergency stop
   bindings. Confirm auto-reset scripts are armed.
4. **Design Source Verification** – Pull the sealed CAD model and material bill from
   the approved registry. Compare SHA-256 digests against the ingress ledger entry.

Do not proceed until all checklist items are signed by both experts and acknowledged by
the gating console.

## 4. Audit Sequence

1. **Static Geometry Scan**
   - Geometric Expert runs a full-lattice lidar sweep.
   - Record `geometric_deviation` (target ≤0.8 mm mean, ≤1.5 mm max) and
     `surface_integrity_score` (target ≥0.96).
2. **Dynamic Alignment Test**
   - Kinetic Expert articulates doors, suspension, and steering subsystems while the
     Geometric Expert tracks positional deltas.
   - Capture `alignment_error` (target ≤0.6° rotational drift, ≤0.4 mm translational).
3. **Material Stress Profiling**
   - Apply controlled torsion/pressure pulses at predefined chassis nodes.
   - Measure `material_stress_ratio` (observed stress ÷ rated stress, target ≤0.82).
4. **Systems Validation Loop**
   - Inference console compares real-time readings to digital twin expectations.
   - Any deviation beyond thresholds forces an automatic rework ticket and halts the
     release track.
5. **Compliance Synthesis**
   - Gating console calculates the composite `compliance_score` using weighted metrics:
     40% alignment, 35% material stress, 25% geometric deviation.
   - Score ≥0.92 and zero outstanding anomalies → asset passes. Otherwise flag for
     remediation.

## 5. Observability & Logging

- **Telemetry Channels** – Log force/position vectors at 200 Hz for the Kinetic Expert
  and 120 Hz point clouds for the Geometric Expert. Down-sample to aggregate stats
  before exit to honor MIAP aggregate-only reporting.
- **Audit Metrics Dashboard** – The gating console UI must display the following in
  real time: `Alignment Error`, `Material Stress`, `Geometric Deviation`,
  `Compliance Score`, and `Anomaly Count`.
- **Augmented Reality Capture** – Generate an AR overlay frame set showing green
  wireframes for validated regions, red highlights for stress points, and numerical
  readouts synchronized with the dashboard metrics. Store renders in
  `relay.artifacts.v1/moe_fab_rec/audit_overlays/` with timestamp and SHA-256 hash.
- **Immutable Ledger Update** – Upon completion, append a record with metrics,
  overlays, and expert signatures to `ssot://ledger/moe_fab_rec/audit.jsonl`.

## 6. Decision & Escalation Logic

| Condition | Action |
| --------- | ------ |
| All metrics within thresholds and compliance ≥0.92 | Approve release; council quorum signs ledger entry. |
| Any metric breaches threshold but compliance ≥0.85 | Flag `REWORK_REQUIRED`; loop asset back to fabrication queue with anomaly report. |
| Compliance <0.85 or multiple hard threshold breaches | Issue `HOLD_RELEASE`, initiate forensic review, and notify Council Chair immediately. |

Escalated cases require an additional peer audit before a new run can proceed.

## 7. Outstanding Tasks

- Automate AR overlay generation pipeline and store preview thumbnails for council
  dashboards.
- Integrate ZERO-DRIFT drift detection hooks for the Kinetic and Geometric experts.
- Extend the simulation harness to replay audit runs for regression analysis.
- Draft remediation playbooks for common anomaly classes (alignment drift,
  torsion hotspots, lidar occlusions).

> **Status** – Operational protocol pending automation enhancements. Update once
> AR overlay captures and drift hooks are deployed.

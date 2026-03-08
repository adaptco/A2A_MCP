# Foundation Model Release Spec

## Objective
Establish a release-ready control plane for agent orchestration with explicit roles, milestone breakpoints, and auditable state transitions.

## Scope
- Import/bootstrap normalization for deterministic runtime behavior.
- Dependency baseline for MCP and validation execution.
- Action-kernel transition contract across `IDLE -> TERMINATED_*`.
- Traceability contract for ledger-ready event export.
- Role/rule/responsibility model for multi-agent operation.

## Status Milestones
1. `M0_BOOTSTRAP`: import normalization active.
2. `M1_DEPENDENCY_BASELINE`: `fastmcp` test/runtime parity.
3. `M2_ACTIONS_KERNEL`: trigger + transition contract validated.
4. `M3_LEDGER_TRACEABILITY`: append-only state-change event schema defined.
5. `M4_SYNTHETIC_COWORKER`: skills-index and intake token contract finalized.

Source of truth: `specs/release_milestones.yaml`.

## Breakpoint Gates
1. `Gate A (Foundation Ready)`: `M0`, `M1` passed.
2. `Gate B (Control Plane Ready)`: `M2` passed with stateflow test pass.
3. `Gate C (Audit Plane Ready)`: `M3` passed with commit-log payload validation.
4. `Gate D (Swarm Ready)`: `M4` passed with role/rule matrix and seed instructions.

## Roles, Rules, Responsibilities
1. `AgenticManager`
   - Role: dispatch + prioritization.
   - Rule: no execution without validated intake token.
   - Responsibility: enforce bounded retry and escalation.
2. `DecisionAgent`
   - Role: evaluate against criteria and policy constraints.
   - Rule: all terminal transitions require scored decision context.
   - Responsibility: emit signed decision payload for ledger log.
3. `KernelExecutor`
   - Role: action execution in orchestrated phases.
   - Rule: only runs from `SCHEDULED` or `RETRY`.
   - Responsibility: persist artifacts and event telemetry.
4. `TelemetryAgent`
   - Role: observe drift, structural gaps, and timing.
   - Rule: append-only event semantics.
   - Responsibility: produce deterministic report bundle.

## Ledger Event Contract (Blockchain Adapter Ready)
Required fields for each state-change event:
- `event_id`
- `plan_id`
- `from_state`
- `to_state`
- `event`
- `timestamp_utc`
- `actor`
- `commit_sha`
- `reason`
- `input_hash`
- `output_hash`

Rules:
1. Append-only.
2. Immutable hash-chain linking via previous event hash.
3. No in-place mutation of historical records.
4. Missing `why` or `where` is allowed; `who/what/when/how` is mandatory.

## Chat Intake Token Contract
Minimal fields:
- `request_id`
- `request_text`
- `requested_avatar`
- `skills_query`
- `estimated_compute_ms`
- `policy_constraints`
- `origin_timestamp`

Routing:
1. Intake token enters `IDLE`.
2. Skills marketplace lookup computes capability match.
3. Manager emits `OBJECTIVE_INGRESS` to move `IDLE -> SCHEDULED`.


## PR Validation Requirement (CI/CD Artifact Gate)
For every pull request targeting `main`, CI must validate each non-merge commit in the PR range and publish a testing artifact bundle.

Requirement:
1. Determine commit range from PR `base.sha..head.sha`.
2. Execute the designated validation suite for each commit independently.
3. Persist a commit-level report artifact containing commit SHA, pass/fail result, exit code, and runtime.
4. Fail the workflow if any commit-level validation fails.

Artifact contract:
- `artifacts/commit-validation/commit_validation_report.json`
- `artifacts/commit-validation/commit_validation_report.md`

This requirement is additive to milestone bundle/draft monitor artifacts and is used as a release-readiness signal for PR generation workflows.

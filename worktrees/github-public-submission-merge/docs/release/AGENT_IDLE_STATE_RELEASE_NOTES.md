# Agent Idle-State Release Notes

## Release
- Name: Foundation Control Plane Prep
- Date: 2026-02-12
- Target state: `IDLE` as default agent posture

## What Changed
1. Added bootstrap-based import normalization for test and runtime entrypoints.
2. Added dependency alignment to include `fastmcp` in base requirements.
3. Updated CI integration workflow to execute MCP handshake validation.
4. Added milestone/breakpoint release spec bundle for phase transitions.
5. Added workflow `.github/workflows/milestone_autopublish.yml` to autopublish milestone artifacts and monitor draft PRs.

## Idle-State Seed Instructions
Agents in `IDLE` must preload the following seed context:
1. Role profile: manager, decision, executor, telemetry.
2. Constraints: safety, spec alignment, latency, intent fidelity.
3. Transition trigger map: ingress, dispatch, evaluate, retry, terminate.
4. Tooling map: internal skills index first, external call second.

## Phase-Change Trigger Seeds
1. `Seed A`: Intake token validated and normalized.
2. `Seed B`: Skill lookup completes with compute estimate.
3. `Seed C`: Manager emits `OBJECTIVE_INGRESS`.
4. `Seed D`: Kernel action selected and logged.

## Milestone Mapping
- `IDLE -> SCHEDULED`: requires `M0`, `M1`.
- `SCHEDULED -> EXECUTING`: requires `M2`.
- `EXECUTING -> EVALUATING`: requires validation test pass.
- `EVALUATING -> TERMINATED_*`: requires decision + audit log write.

## Validation Status
This release expects:
1. `tests/test_stateflow.py` passing.
2. `tests/test_mcp_agents.py` passing with `fastmcp` installed.
3. CI workflows installing from `requirements.txt`.

## Operator Notes
If a failure occurs:
1. Keep agents in `IDLE`.
2. Append a diagnostic record (do not overwrite prior entries).
3. Re-seed with corrected constraints and retry dispatch.

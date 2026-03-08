# Mission Oversight HUD Widgets

This reference pairs with `specs/mission.oversight.hud.contract.v1.json` and defines the operator-facing widgets for live mission oversight.

## Widget Catalog

| Widget ID | Type | Purpose | Primary Data Sources | Fail-Closed Response |
| --- | --- | --- | --- | --- |
| `mission_phase` | State Pill | Surface the current mission phase and transition reason at a glance. | `mission.state` (`state_machine.state`, `state_machine.transition_cause`) | Lock the cockpit controls and prompt council acknowledgement when upstream data is stale. |
| `bundle_health` | Status Summary | Monitor choreo.bundle version, hash, and synchronization health. | `mission.telemetry.aggregate` (`bundle.version`, `bundle.hash`, `sync.offset_ms`, `uptime_seconds`) | Raise a critical alert and halt promotion workflows if telemetry is missing or exceeds thresholds. |
| `live_ledger` | Activity Feed | Display the most recent ledger entries for human audit. | `mission.ledger.entries` | Replace with an explanatory placeholder while maintaining immutable ledger logging. |
| `alerts` | Alert Marquee | Aggregate fail-closed alerts and track acknowledgement. | `mission.alerts` | Escalate to council primary and secondary when alerts are unacknowledged. |

## Action Bar Buttons

| Button ID | Label | Action Topic | Guardrails |
| --- | --- | --- | --- |
| `freeze_protocol` | Freeze Mission | `mission.freeze` | Requires confirmation modal; disabled automatically on data loss. |
| `retarget` | Retarget | `mission.retarget` | Available only when retarget policy guard passes; disabled on fail-closed triggers. |
| `rollback` | Rollback | `mission.rollback` | Disabled until rollback trigger conditions are present; re-enabled post-verification. |

## Data Integrity Notes

- All widgets consume data through the contract’s declared streams to ensure determinism and auditability.
- Any stream marked `fail_closed` halts interactive controls until the Council clears the issue.
- Widget telemetry thresholds are mirrored in the mission meta directive to avoid drift between protocol and HUD enforcement.

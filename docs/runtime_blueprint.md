# Runtime Blueprint: Canonical Thread for Orchestrator + Agents + Schemas

This blueprint turns the repository into one runtime truth-path by introducing a canonical contract spine, orchestrator-owned composition root, and append-only event thread.

## 1) Canonical contract spine (`schemas/`)

- Add canonical intent/event contracts in `schemas/runtime_event.py`.
- Keep explicit contract versions with `ContractVersion` (`v1`, `v2`) for compatibility.
- Require all internal modules to exchange canonical payloads only; adapters translate at boundaries.

## 2) Orchestrator composition root (`orchestrator/`)

- `orchestrator/runtime_thread.py` is the control-plane root for startup wiring and runtime routing.
- Agents do not directly discover or call each other; they exchange intents/events through this root.
- Runtime flow emits events across phases:
  - `control_plane` (routing, scheduling, arbitration)
  - `data_plane` (inference/tool execution)
  - `gate` (schema/policy/drift checks)

## 3) Event-first runtime thread

Every meaningful state change emits `RuntimeEvent` with:

- `trace_id`, `span_id`
- `actor`, `intent`, `artifact_id`
- `schema_version`, `timestamp`
- phase + event_type

Persist events append-only (production DB, queue, or log). Build current state from replay or projection.

## 4) Stateflow alignment

Use `orchestrator/stateflow.py` transitions as FSM authority, and emit a matching runtime event per transition.

For each state stage define:

- entry criteria
- timeout
- retry policy
- fallback path
- emitted canonical event

## 5) Runtime gates as first-class events

Before promotion/deployment/handoff, run gates for:

- schema validity
- provenance/policy (OIDC)
- drift and performance thresholds

Gate outcomes must emit `gate.*` events (not logs-only).

## 6) Anti-corruption adapters

Keep adapters at boundaries only:

- MCP tools
- HTTP/FastAPI
- DB/ORM
- model vendor APIs

Adapters translate external formats to canonical schemas.

## 7) Golden-path telemetry

Dashboard and SLOs should follow one path:

`intent.received -> dataplane.dispatched -> artifact.delivered -> gate.* passed`

This enables deterministic debugging, replay, and canary comparison across versions.

## 8) Suggested phased refactor steps

1. Adopt canonical contracts in new orchestrations and gateways first.
2. Backfill adapter wrappers around legacy agent inter-calls.
3. Emit runtime events from existing stateflow transitions.
4. Add projections for operational views (latency, gate failures, artifact throughput).
5. Enable feature flags + canary routing for any `v2` contract rollout.

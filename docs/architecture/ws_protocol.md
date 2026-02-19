# PRIME_DIRECTIVE WebSocket Protocol (`/ws/pipeline`)

## Control-plane contract
The WebSocket handler is **transport-only**. It validates envelope shape, forwards to `PipelineEngine`, and streams engine events back to the client. Gate logic must remain in the engine/validators.

## Required inbound message types

### 1) `render_request`
```json
{
  "type": "render_request",
  "request_id": "req-001",
  "run_id": "run-abc",
  "payload": {
    "assets": ["staging/input/mock.png"],
    "profile": "banner"
  }
}
```

### 2) `get_chain`
```json
{
  "type": "get_chain",
  "request_id": "req-002",
  "run_id": "run-abc"
}
```

### 3) `get_state`
```json
{
  "type": "get_state",
  "request_id": "req-003",
  "run_id": "run-abc"
}
```

### 4) `ping`
```json
{
  "type": "ping",
  "request_id": "req-004",
  "ts": "2026-01-01T00:00:00Z"
}
```

## Required emitted events

### Lifecycle + render events
- `state.transition`
- `render.started`
- `render.completed`

### Gate events
- `gate.preflight`
- `gate.c5`
- `gate.rsm`
- `gate.provenance` (optional)
- `validation.passed` **or** `pipeline.halted`

### Output events
- `export.completed`
- `commit.complete`
- `pipeline.pass`

## Example success stream
```json
{"type":"state.transition","run_id":"run-abc","from":"idle","to":"rendered"}
{"type":"render.completed","run_id":"run-abc","artifact":"staging/run-abc/render.png"}
{"type":"gate.preflight","run_id":"run-abc","passed":true}
{"type":"gate.c5","run_id":"run-abc","passed":true}
{"type":"gate.rsm","run_id":"run-abc","passed":true}
{"type":"validation.passed","run_id":"run-abc"}
{"type":"export.completed","run_id":"run-abc","artifact":"exports/run-abc/banner.pdf"}
{"type":"commit.complete","run_id":"run-abc","sha":"abc123"}
{"type":"pipeline.pass","run_id":"run-abc"}
```

## Example failure stream (no export)
```json
{"type":"state.transition","run_id":"run-def","from":"rendered","to":"validated"}
{"type":"gate.preflight","run_id":"run-def","passed":true}
{"type":"gate.c5","run_id":"run-def","passed":false,"reason":"missing_bleed_margin"}
{"type":"pipeline.halted","run_id":"run-def","at_gate":"c5"}
```

`export.completed` and `commit.complete` MUST NOT appear in failure streams.

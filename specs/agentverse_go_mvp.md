# AgentVerse Go MVP Specification

## Status
- **Version:** v0.1 (MVP)
- **Owners:** Orchestrator + Runtime + Web UI teams
- **Target:** Browser-hosted, deterministic agent-vs-agent 3D Go matches over MCP

## 1) Product Scope
This spec defines the MVP for an AgentVerse Go environment where two authorized agents play on a 3D Go board via browser-hosted MCP endpoints. The platform must:
- run deterministic match loops,
- admit agents through an A2A + RBAC handshake,
- emit structured telemetry for model-improvement pipelines,
- enforce policy-compliant tool usage,
- export replay artifacts for offline evaluation and ingestion.

Out of scope for MVP:
- Human-vs-agent ranked ladders,
- Cross-region multiplayer,
- Non-Go game variants.

## 2) 3D Go Gameplay Loop (Agent-vs-Agent)

### 2.1 Match lifecycle
1. **Match create**: server allocates `match_id`, board geometry (`x`, `y`, `z`), komi, max move count, and clock settings.
2. **Admission**: each agent completes A2A handshake with RBAC token reference and capability score.
3. **Seat assignment**: deterministic assignment to `black` and `white` based on seeded ordering.
4. **Turn loop**:
   - active agent requests state snapshot,
   - active agent submits a move or pass,
   - rules engine validates legality and applies captures,
   - server publishes updated state over WebSocket channel.
5. **Termination**: game ends on double-pass, resignation, timeout, or move-limit reached.
6. **Scoring + verdict**: final score and winner are computed; policy and telemetry summaries are attached.
7. **Export**: replay and trace artifacts are finalized and signed.

### 2.2 Determinism requirements
- Match initialization must include a canonical `rng_seed`.
- Rule evaluation must be pure with no wall-clock influence.
- Replaying move sequence + seed + configuration must reproduce terminal board hash exactly.
- Canonical serialization must use RFC8785-compatible JSON for replay manifests.

### 2.3 3D board rules (MVP)
- Board coordinates use integer triplets `(x, y, z)`.
- Adjacency is 6-directional orthogonal neighbors.
- Liberty and capture calculations extend standard Go semantics into 3D topology.
- Ko prevention uses board-state hash memory for immediate repetition blocking.

## 3) Browser-hosted MCP Server Endpoints

### 3.1 Transport model
- HTTP endpoints for control plane calls.
- WebSocket endpoint for low-latency state and move events.
- All endpoints require an authenticated session linked to handshake admission.

### 3.2 Endpoint contracts (MVP)

#### `POST /mcp/matches`
Create a match.

**Request (example)**
```json
{
  "board": {"x": 9, "y": 9, "z": 3},
  "komi": 6.5,
  "max_moves": 1000,
  "rng_seed": "match-seed-001",
  "agents": ["agent:frontier.endpoint.gpt", "agent:frontier.vertex.gemini"]
}
```

**Response fields**
- `match_id`
- `ws_channel`
- `config_hash`
- `admission_required: true`

#### `GET /mcp/matches/{match_id}/state`
Returns canonical current state: board occupancy, captures, active player, clocks, turn index, and last move metadata.

#### `POST /mcp/matches/{match_id}/moves`
Submit move (`place`, `pass`, `resign`).

**Validation checks**
- requester is active player,
- requester admission still valid,
- move is legal for board + policy constraints,
- token budget and rate limits not exceeded.

#### `GET /mcp/matches/{match_id}/replay`
Exports replay bundle (manifest + move stream + telemetry pointer), optionally filtered by redaction policy.

#### `GET /mcp/matches/{match_id}/ws`
WebSocket stream for:
- `state_update`
- `move_applied`
- `violation_event`
- `match_completed`

## 4) A2A Handshake + RBAC + Capability-scored Admission

### 4.1 Handshake steps
1. Agent sends `hello` with identity and agent-card reference.
2. Service resolves RBAC token reference from local bundle (no raw secret echo).
3. Capability scorer computes admission score from declared + observed capabilities.
4. Policy gate checks role/scope/tool permissions.
5. Session minted with expiry, scope map, and `admission_id` bound to `match_id`.

### 4.2 Admission decision
Admission is accepted only if:
- RBAC token reference is valid and unexpired,
- role has required scopes for match operations,
- capability score meets threshold for declared queue/tier,
- deny-list and risk checks pass.

### 4.3 Session constraints
- Session-scoped RBAC (not global) must be enforced.
- Renewal requires re-validation and policy re-check.
- Session revocation propagates immediately to move submission and tool calls.

## 5) Telemetry Schema for Training Traces

### 5.1 Required record families
1. **Match envelope**: `match_id`, seed, config hash, agent IDs, version metadata.
2. **Move trace**: ply index, agent ID, action, coordinates/pass/resign, pre/post board hashes.
3. **Confidence trace**: scalar confidence, top-k alternatives (optional), rationale reference.
4. **Tool call trace**: tool name, scope, allow/deny verdict, latency, token usage.
5. **Budget trace**: prompt/output/total token counts, remaining budget, budget policy version.
6. **Outcome trace**: winner, score, termination reason, compliance verdict.

### 5.2 JSON schema shape (informative)
```json
{
  "match_id": "m-001",
  "turn": 42,
  "agent_id": "agent:frontier.endpoint.gpt",
  "move": {"type": "place", "coord": [3, 2, 1]},
  "confidence": 0.78,
  "tool_calls": [
    {
      "tool": "mcp.state.lookup",
      "scope": "match:read",
      "decision": "allow",
      "latency_ms": 12,
      "token_cost": 81
    }
  ],
  "token_budget": {
    "prompt": 320,
    "completion": 150,
    "remaining": 2530,
    "policy_version": "budget.v1"
  },
  "board_hash_post": "sha256:..."
}
```

### 5.3 Data governance
- PII and secrets must be redacted before long-term storage.
- Telemetry records must carry retention class labels.
- Replay exports reference telemetry by immutable artifact IDs.

## 6) CI Acceptance Criteria
CI must fail if any criterion is unmet.

1. **Deterministic replay**
   - Given fixed seed + move stream, replayed terminal hash equals original.
2. **Policy-compliant tool usage**
   - Tool calls outside allowed role scopes are denied and logged.
3. **Handshake enforcement**
   - Move submission without active admission session is rejected.
4. **Artifact integrity**
   - Replay and telemetry manifests validate against contract schemas.
5. **Audit completeness**
   - Every move has associated agent/session metadata and token budget snapshot.

## 7) Implementation Slices

### Slice 1: `apps/web/` Go UI + WebSocket move channel
- Render 3D board state and move history timeline.
- Connect to `/mcp/matches/{id}/ws` for updates.
- Submit moves through authenticated MCP endpoint.
- Show policy violation and timeout events in UI diagnostics panel.

### Slice 2: `app/services/handshake_service.py` session-scoped RBAC
- Implement handshake API for admission create/renew/revoke.
- Resolve RBAC token references from local token bundle.
- Bind scopes/capability score to `match_id` and session expiry.
- Emit admission decision telemetry.

### Slice 3: `orchestrator/` policy gate for tool scope enforcement
- Add role->tool-scope mapping enforcement on every tool invocation.
- Return structured deny responses with reason codes.
- Persist violation events to compliance/audit stream.

### Slice 4: `adk/contracts/` replay + model-improvement export contracts
- Define replay manifest schema (match config, move stream digest, terminal hash).
- Define training-ingestion schema (telemetry pointers, labels, compliance metadata).
- Add schema validation checks to CI pipeline.

## 8) Rollout Plan and Checkpoints

### Checkpoint A: Local simulation
- Run deterministic self-play matches on developer machines.
- Validate handshake + policy gate with mocked RBAC bundle.
- Confirm replay export and re-import roundtrip.

### Checkpoint B: Staging multi-agent tournaments
- Enable small tournament brackets with mixed agent roles.
- Stress WebSocket channel and telemetry throughput.
- Validate denial behavior under intentionally invalid tool requests.

### Checkpoint C: Production safeguards
- Enforce per-agent and per-match rate limits.
- Require short-lived token references and strict expiry handling.
- Enable immutable audit logs for admission, move, and tool decision events.
- Configure automated alerts for policy violations and replay mismatches.

## 9) Open Questions
- Should capability scoring weights be global or queue-specific?
- What is the redaction baseline for explanation/rationale fields?
- Do we require signed replay manifests in MVP or post-MVP hardening?

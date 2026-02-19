# PRIME_DIRECTIVE Refactor Audit + Implementation Plan (Non-Destructive)

## Scope
Repository audited: `A2A_MCP`.
Audit objective: move incrementally toward PRIME_DIRECTIVE architecture using adapters and preserving existing behavior.

## A) Repo inventory + gap analysis

### A1. `tree -L 4` equivalent inventory (focused)
```text
.
├── app/
│   ├── multi_client_api.py
│   └── vector_ingestion.py
├── orchestrator/
│   ├── main.py
│   ├── stateflow.py
│   ├── settlement.py
│   ├── webhook.py
│   ├── telemetry_service.py
│   └── verify_api.py
├── pipeline/
│   ├── ingest_api/main.py
│   ├── docling_worker/worker.py
│   └── embed_worker/
├── src/
│   ├── fastmcp.py
│   ├── multi_client_router.py
│   └── prime_directive/
│       ├── api/
│       ├── pipeline/
│       ├── validators/
│       ├── sovereignty/
│       ├── export/
│       └── util/
├── scripts/
│   ├── repo_audit.py
│   ├── smoke_ws.sh
│   └── automate_healing.py
├── docs/
│   └── architecture/
│       ├── ws_protocol.md
│       ├── sovereignty_log.md
│       └── prime_directive_refactor_audit.md
├── tests/
│   ├── test_stateflow.py
│   ├── test_verify_api.py
│   ├── test_sovereignty_chain.py
│   └── test_api_health_prime_directive.py
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── requirements.txt
```

### A2. Current entrypoints + core logic locations
- **FastAPI entrypoints**
  - `app/multi_client_api.py` (`/mcp/register`, `/mcp/{id}/baseline`, `/mcp/{id}/stream`).
  - `app/vector_ingestion.py` (ingestion API).
  - `orchestrator/webhook.py` (`/plans/ingress`, `/plans/{plan_id}/ingress`).
  - `pipeline/ingest_api/main.py` (`/health`, `/ingest`, `/status/{bundle_id}`).
- **State machine logic**
  - `orchestrator/stateflow.py` provides the current FSM and transitions.
- **Telemetry / event logging / chain verification**
  - `orchestrator/telemetry_service.py`, `orchestrator/telemetry_integration.py`.
  - `orchestrator/settlement.py` has deterministic payload canonicalization and hash chaining helpers.
- **Exporter-like behavior**
  - No dedicated PRIME_DIRECTIVE exporter package yet; export functionality is scattered and domain-specific.

### A3. Move map to target modules

| Current file | Proposed target | Action | Notes |
|---|---|---|---|
| `orchestrator/stateflow.py` | `src/prime_directive/pipeline/state_machine.py` | WRAP then MOVE | Preserve old FSM API; create adapter for legacy webhook paths.
| `orchestrator/settlement.py` | `src/prime_directive/sovereignty/chain.py` | WRAP then MOVE | Reuse canonical hash logic; split DB adapter from pure chain functions.
| `orchestrator/webhook.py` | `src/prime_directive/api/app.py` | WRAP with adapter | Keep ingress compatibility while adding `/health` + `/ws/pipeline`.
| `app/multi_client_api.py` | `src/prime_directive/api/app.py` (integrated router) | KEEP then WRAP | Reuse current tenant/stream handlers as compatibility endpoints.
| `orchestrator/verify_api.py` | `src/prime_directive/api/verify_adapter.py` | MOVE | Keep legacy route until clients migrate.
| `orchestrator/telemetry_*.py` | `src/prime_directive/sovereignty/export.py` + adapters | KEEP | Integrate gradually; avoid telemetry regression.
| `pipeline/ingest_api/main.py` | separate service (unchanged) | KEEP as-is | Out-of-scope ingestion microservice.

### A4. Missing target files/modules/docs/tests/scripts
Missing or partial prior to this patch:
- `src/prime_directive/*` full package tree.
- validators modules (`preflight`, `c5`, `rsm`, optional provenance).
- pipeline engine orchestrator + explicit hard-stop gate sequencing.
- WS protocol docs and sovereignty docs.
- smoke script for pass/fail + no-export assertion.
- architecture audit script validating repo against target.
- dedicated tests for new sovereignty package and API health.

## B) Implementation plan (merge-safe PR sequence)

### PR1 — Foundation skeleton + deterministic sovereignty core
- Add `src/prime_directive` package skeleton.
- Add pure deterministic hashing + sovereignty chain module.
- Add unit tests for chain integrity + tamper detection.
- Keep all existing entrypoints untouched.

### PR2 — Validators with hard-stop contracts
- Implement `preflight`, `c5_geometry`, `rsm_color` validators (pure functions + structured results).
- Add unit tests for pass/fail cases and deterministic behavior.
- Add optional provenance gate with explicit feature flag.

### PR3 — PipelineEngine + state machine
- Implement engine sequencing: Render → Preflight → C5 → RSM → Export → Commit.
- Enforce: no export/commit on gate failure.
- Emit sovereignty events for each transition and gate.
- Add tests for pass path, fail path, and no-export guarantee.

### PR4 — API + WS transport adapter
- Add `/health` and `/ws/pipeline` in `src/prime_directive/api/app.py`.
- WS remains transport-only and delegates to `PipelineEngine`.
- Add protocol tests for required message and event types.
- Maintain compatibility adapters for legacy ingress endpoints.

### PR5 — Export/bundle + packaging + CI smoke
- Implement exporter + bundle emission with allowed-root path enforcement.
- Add runbooks (`local_dev.md`, `deployment.md`).
- Add Docker assets for PRIME_DIRECTIVE service/compose profile.
- Add CI commands and smoke workflow using `scripts/smoke_ws.sh`.

## D) Code review output requirements

### D1. Current vs Target table

| Area | Current | Target | Delta |
|---|---|---|---|
| API surface | Multiple FastAPI apps with mixed concerns | Single PRIME_DIRECTIVE app w/ `/health` + `/ws/pipeline` | Consolidate via adapters.
| Gate logic ownership | Not centralized yet | PipelineEngine-owned ordered gates | Add engine orchestrator layer.
| Sovereignty log | Available in settlement verification path | Dedicated pure chain module | Split storage from pure deterministic core.
| Determinism | Partially deterministic | Fully deterministic seeds/hash canonicalization | Ban `hash()` usage in new modules.
| Export safety | Not globally enforced | No export unless all gates pass | Add hard-stop checks + tests.
| Path safety | Not centrally guarded | allowed-root enforcement (`staging/`, `exports/`) | Add util path guards.

### D2. Risks / unknowns + mitigation
- **Risk:** multiple existing APIs with production consumers.  
  **Mitigation:** keep compatibility routers during migration.
- **Risk:** state semantics mismatch between `stateflow` and new pipeline states.  
  **Mitigation:** transitional adapter mapping table + regression tests.
- **Risk:** mixed persistence backends.  
  **Mitigation:** isolate pure chain logic from storage adapters and test both.

### D3. Determinism compliance checklist
- [x] Canonical JSON for hash inputs.
- [x] `sha256`-based deterministic seed helper.
- [x] No use of Python `hash()` in new PRIME_DIRECTIVE modules.
- [ ] Remove/replace any legacy randomness in render/export path as PR3/PR5 follow-up.

### D4. Security constraints checklist (allowed-root enforcement)
- [x] Add `enforce_allowed_root` utility for `staging/` and `exports/` only.
- [x] Add `.gitignore` entries for `exports/`, `staging/`, `.db`, `.env.*`.
- [ ] Wire path checks into exporter and bundle writer in PR5.

### D5. CI/CD acceptance criteria + exact commands
- Unit tests: `pytest tests/test_sovereignty_chain.py tests/test_api_health_prime_directive.py`
- Static repo audit: `python scripts/repo_audit.py` (non-zero indicates findings to address)
- Smoke: `bash scripts/smoke_ws.sh` (requires running PRIME_DIRECTIVE service + ws_client harness)

### D6. PR-ready diff summary (this patch)
Added:
- `src/prime_directive/` skeleton modules
- `tests/test_sovereignty_chain.py`
- `tests/test_api_health_prime_directive.py`
- `scripts/repo_audit.py`
- `scripts/smoke_ws.sh`
- `docs/architecture/ws_protocol.md`
- `docs/architecture/sovereignty_log.md`
- `docs/architecture/prime_directive_refactor_audit.md`

Modified:
- `.gitignore` (artifact safety)

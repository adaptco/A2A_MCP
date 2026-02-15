# Developer Handoff: Workflow + Spec + Manifold Schema Package

## Recommended PR
- `Title`: `feat(release): add milestone autopublish, release gates, and XML->MEL manifold schema contract`
- `Why this exists`: consolidate release workflow automation, milestone gating metadata, and the XML normalization/manifold schema contract into one reviewable package.

## Scope

### Workflow and CI updates
- `.github/workflows/milestone_autopublish.yml`
  - Adds milestone bundle artifact publishing.
  - Adds draft-PR monitoring report artifact generation.
  - Updates/creates lifecycle monitoring comment on PRs.
- `.github/workflows/daily_ingress.yml`
  - Uses `POST /plans/ingress` and explicit `plan_id` payload.
- `.github/workflows/integration_test.yml`
  - Runs DB-backed persistence + MCP handshake test lanes.
- `.github/workflows/main.yml`
  - Maintains containerized integration pipeline execution.

### Release and contract specs
- `specs/release_milestones.yaml`
  - Defines milestone gates M0..M5 and phase-change seeds.
- `specs/supra_specs.yaml`
  - Updated specification payload (audit-driven corrections/additions).
- `specs/supra_specs_verified.yaml`
  - Verified/high-confidence spec variant.
- `SPECS_AUDIT.md`
  - Audit notes, verified fields, and corrective actions.

### Manifold engine language contract
- `specs/xml_normalization_map.yaml`
  - XML normalization map into canonical manifold input fields.
- `schemas/manifold_action_language.schema.json`
  - JSON schema for MEL-1 (`manifold_input`, decision axes, generated actions).

### Runtime/test touchpoints in this package
- `agents/tester.py`
- `orchestrator/main.py`
- `orchestrator/stateflow.py`
- `orchestrator/telemetry_service.py`
- `orchestrator/webhook.py`
- `schemas/__init__.py`
- `schemas/database.py`
- `tests/test_mcp_agents.py`
- `conftest.py`
- `requirements.txt`
- `mcp_server.py`

## Behavior Change Summary
- CI now emits milestone + draft-monitor artifacts and PR draft-state visibility.
- Ingress workflow now hits the canonical `/plans/ingress` endpoint with explicit `plan_id`.
- Release gating is codified in `specs/release_milestones.yaml`.
- XML payloads can be normalized to a canonical action manifold envelope and validated against MEL-1 schema.

## Validation (exact commands)

### Local
```powershell
# 1) Install deps
python -m pip install -r requirements.txt

# 2) Validate MCP/agent handshake path
python -m pytest -q tests/test_mcp_agents.py

# 3) Validate orchestrator/judge path
python -m pytest -q tests/test_avatar_integration.py tests/test_intent_engine.py

# 4) Validate XML map + MEL-1 schema parse
python -c "import json, pathlib, yaml; yaml.safe_load(pathlib.Path('specs/xml_normalization_map.yaml').read_text(encoding='utf-8')); json.loads(pathlib.Path('schemas/manifold_action_language.schema.json').read_text(encoding='utf-8')); print('ok')"
```

### CI/workflow trigger verification
1. Push PR branch and confirm these workflows run:
   - `A2A-MCP Integration Tests`
   - `A2A Pipeline CI`
   - `Milestone Autopublish and Draft Monitor`
2. In workflow artifacts, verify:
   - `milestone-bundle-*`
   - `draft-monitor-report-*`
3. On PR page, verify bot comment marker exists:
   - `<!-- a2a-draft-monitor -->`

## Risks and Known Gaps
- `specs/supra_specs.yaml` has broad edits; downstream consumers may require fixture updates.
- Workflow behavior depends on existing repo secrets (`MCP_ENDPOINT`, `MCP_TOKEN`).
- Current repo tree contains many unrelated local temp paths (`tmpclaude-*`), which should not be included in PR.
- `a2a_mcp.db` is locally modified and should remain excluded from PR diffs.

## Rollback Plan
```powershell
# Roll back this package by reverting the merge commit
git revert <merge_commit_sha>

# Or rollback individual files if needed
git checkout origin/main -- .github/workflows/milestone_autopublish.yml
git checkout origin/main -- .github/workflows/daily_ingress.yml
git checkout origin/main -- specs/release_milestones.yaml
git checkout origin/main -- specs/xml_normalization_map.yaml
git checkout origin/main -- schemas/manifold_action_language.schema.json
```

## PR Checklist
- [ ] Tests passed locally (`pytest` commands above).
- [ ] Workflow triggers verified in PR checks.
- [ ] Milestone artifacts generated in Actions.
- [ ] Draft monitor report artifact generated.
- [ ] Reviewer sign-off from platform/infra owner.
- [ ] Reviewer sign-off from orchestrator owner.
- [ ] Temp/local artifacts excluded from PR (`tmpclaude-*`, local DB).


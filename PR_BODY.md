## Title
`feat(release): add milestone autopublish, release gates, and XML->MEL manifold schema contract`

## Why this exists
This PR packages release automation and the manifold language contract in one place so developers can validate and merge safely with a single review path.

## What changed
- Added milestone autopublish + draft monitoring workflow:
  - `.github/workflows/milestone_autopublish.yml`
- Updated core workflow paths and integration lanes:
  - `.github/workflows/daily_ingress.yml`
  - `.github/workflows/integration_test.yml`
  - `.github/workflows/main.yml`
- Added release milestone gate spec:
  - `specs/release_milestones.yaml`
- Added XML normalization map + manifold language schema:
  - `specs/xml_normalization_map.yaml`
  - `schemas/manifold_action_language.schema.json`
- Included supporting runtime/spec/test updates (see `HANDOFF.md` for full list).

## What this enables
- Automatic release milestone bundle artifacts on push/PR/schedule.
- Automatic draft PR observability and status comment updates.
- A concrete, versioned XML-to-MEL normalization and validation contract for manifold action generation.

## What developers need to do next
1. Run local validation commands in `HANDOFF.md`.
2. Verify the three workflows complete successfully in PR checks.
3. Confirm milestone and draft monitor artifacts are present.
4. Confirm draft-monitor PR comment appears/updates correctly.

## What can wait
- Broad cleanup of local temp artifacts (`tmpclaude-*`) can be done in a follow-up hygiene PR.
- Optional extension of MEL-1 fields can be deferred until first production payloads are observed.

## Validation
```powershell
python -m pip install -r requirements.txt
python -m pytest -q tests/test_mcp_agents.py
python -m pytest -q tests/test_avatar_integration.py tests/test_intent_engine.py
python -c "import json, pathlib, yaml; yaml.safe_load(pathlib.Path('specs/xml_normalization_map.yaml').read_text(encoding='utf-8')); json.loads(pathlib.Path('schemas/manifold_action_language.schema.json').read_text(encoding='utf-8')); print('ok')"
```

## Checklist
- [ ] Tests passed
- [ ] Workflow triggers verified
- [ ] Milestone artifacts generated
- [ ] Reviewer sign-off


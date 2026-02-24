# Developer Handoff: Milestone Autopublish + Draft Monitoring

## Scope
This handoff packages the CI milestone autopublish and draft-monitoring foundation, plus release milestone metadata and operator notes.

### Included files
- `.github/workflows/milestone_autopublish.yml`
- `specs/release_milestones.yaml`
- `docs/release/FOUNDATION_MODEL_RELEASE_SPEC.md`
- `docs/release/AGENT_IDLE_STATE_RELEASE_NOTES.md`
- `bootstrap.py`
- `conftest.py`
- `.github/workflows/integration_test.yml`
- `.github/workflows/main.yml`
- `requirements.txt`

## What It Enables
1. Auto-publishes milestone bundle artifacts on `push`, `pull_request`, `schedule`, and manual dispatch.
2. Generates draft monitoring artifacts and updates PR monitoring comments.
3. Defines release milestone gates (M0..M5) and phase-change seed transitions.
4. Keeps MCP test path available via `fastmcp` dependency baseline.

## Validation Commands
Run from repo root:

```powershell
C:\Users\eqhsp\.venv-qe\Scripts\python -m pytest -q tests/test_stateflow.py tests/test_mcp_agents.py
```

Expected result:
- `4 passed`

## Workflow Triggers To Verify In PR
1. `Milestone Autopublish and Draft Monitor`
2. `A2A-MCP Integration Tests`
3. `A2A Pipeline CI`

## Artifact Outputs To Verify
1. `milestone-bundle-*`
2. `draft-monitor-report-*`

## Known Constraints
1. Existing local submodule `PhysicalAI-Autonomous-Vehicles` is dirty and intentionally excluded from this handoff.
2. Repo contains unrelated local/temp artifacts; do not include them in PR.

## Rollback
If needed, revert this package by commit:

```powershell
git revert <commit_sha>
```

## Recommended PR
- **Title**: `feat(ci): autopublish milestone bundle and start draft monitoring`
- **Summary**: Adds CI workflow + release milestone contract to auto-publish artifacts and monitor draft lifecycle for handoff readiness.

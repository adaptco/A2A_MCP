# Orchestrator Runtime Branch Checklist

Use this checklist when creating a stable branch for the `OrchestrationAgent` to
produce a runtime model contract.

## 1) Canonical Repo + Branch

- [ ] Work only in `C:\Users\eqhsp\Documents\GitHub\A2A_MCP`.
- [ ] Confirm branch and cleanliness:
  - `git branch --show-current`
  - `git status --short`
- [ ] Create branch from updated `main`:
  - `git checkout main`
  - `git pull`
  - `git checkout -b stabilize/orchestrator-runtime-model`

## 2) Local Drift Alignment (Current Workspace)

As of February 16, 2026, this workspace should be treated as unstable if
`PhysicalAI-Autonomous-Vehicles` is dirty.

- [ ] If `git status --short` shows `PhysicalAI-Autonomous-Vehicles`, isolate it:
  - move dataset-only edits to a separate branch/repo, or
  - clean/commit inside that directory before opening a PR from this repo.
- [ ] Ensure no merge conflict markers are present:
  - `rg -n \"^<<<<<<<|^=======|^>>>>>>>\" .`
- [ ] Ensure no secrets are committed:
  - `rg -n \"LLM_API_KEY=|TWILIO_AUTH_TOKEN=|OPENAI_API_KEY=\" .`

## 3) Runtime Model Contract Lock

Stabilize these files first and avoid opportunistic edits outside this scope:

- [ ] `schemas/project_plan.py`
- [ ] `schemas/model_artifact.py`
- [ ] `schemas/game_model.py`
- [ ] `schemas/world_model.py`
- [ ] `agents/orchestration_agent.py`
- [ ] `orchestrator/intent_engine.py`
- [ ] `orchestrator/stateflow.py`
- [ ] `orchestrator/judge_orchestrator.py`

Definition of done for contract lock:

- [ ] Typed schemas are backward-compatible or explicitly versioned.
- [ ] State transitions are deterministic and replayable.
- [ ] Runtime outputs map to one authoritative schema path.

## 4) Stability Test Gate

Run this minimum gate before PR:

```powershell
python -m pytest -q tests/test_intent_engine.py tests/test_full_pipeline.py tests/test_stateflow.py tests/test_cicd_pipeline.py
```

If notifications/runtime bridge are included in the branch:

```powershell
python -m pytest -q tests/test_notifier.py tests/test_notification_agent.py tests/test_notification_app.py
```

## 5) CI Gate

- [ ] Ensure `.github/workflows/agents-ci-cd.yml` is enabled on the branch.
- [ ] PR must require green status for:
  - `validate`
  - `contract-artifacts`

## 6) PR Cut Criteria

Open PR only when all are true:

- [ ] `git status --short` is clean.
- [ ] No unresolved conflict markers.
- [ ] Tests above pass locally.
- [ ] Runtime contract changes are documented in PR summary.
- [ ] Scope excludes unrelated directories and generated files.

## 7) Suggested PR Body (Copy/Paste)

```markdown
## Runtime Model Stabilization
- Locked contract surfaces (`schemas/*`, `orchestrator/*`, `agents/orchestration_agent.py`)
- Verified deterministic state transitions
- Verified orchestration runtime output compatibility

## Validation
- [x] test_intent_engine
- [x] test_full_pipeline
- [x] test_stateflow
- [x] test_cicd_pipeline
- [x] notification tests (if applicable)

## Drift Control
- [x] No unresolved merge markers
- [x] No secret material in tracked files
- [x] Branch cleaned before PR
```

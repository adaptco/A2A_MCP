## Title
`feat(cicd): wire production CI monitor with signed webhooks and GKE release deployment`

## Summary
This PR introduces a production CI/CD monitoring path from GitHub Actions into MCP, then uses those signals to compute release readiness by commit SHA.

## Why
- CI and release readiness were spread across separate workflows with no unified runtime status endpoint.
- Existing workflow ingestion had route drift (`/ingress` vs `/plans/ingress`) and one broken workflow YAML.
- Production webhooks needed stronger integrity checks.

## What Changed
- Added CI monitor agent:
  - `agents/cicd_monitor_agent.py`
  - `agents/__init__.py`
- Extended webhook API for CI/CD status ingestion and queries:
  - `orchestrator/webhook.py`
  - New endpoints:
    - `POST /webhooks/github/actions`
    - `GET /cicd/status/{head_sha}`
    - `GET /cicd/run/{run_id}`
    - Backward-compatible `POST /ingress`
- Refactored workflows for end-to-end wiring:
  - `.github/workflows/cicd-monitor.yml` (new `workflow_run` hook)
  - `.github/workflows/agents-ci-cd.yml` (monitor notification job)
  - `.github/workflows/main.yml` (corrected ingress path)
  - `.github/workflows/integration_test.yml` (rebuilt valid workflow)
  - `.github/workflows/release-gke-deploy.yml` (manual/tag release deploy with MCP readiness gate and post-deploy webhook)
- Added tests and workflow assertions:
  - `tests/test_webhook_cicd_monitor.py`
  - `tests/test_workflow_actions.py`

## Security
- Added strict GitHub signature validation in webhook ingestion when `GITHUB_WEBHOOK_SECRET` is configured.
- Workflow hooks emit `X-Hub-Signature-256` when `MCP_WEBHOOK_SECRET` is configured.
- Token fallback remains supported via `Authorization: Bearer`/`X-Webhook-Token` for non-signature environments.

## Suggested Tags
- `release`
- `ci/cd`
- `orchestrator`
- `security`
- `onboarding`
- `production-ready`

## Release Notes
See:
- `docs/release/CI_CD_MONITOR_RELEASE_NOTES.md`
- `docs/release/AGENT_WORKFLOW_TASKS.md`
- `docs/PHASE_RELEASE_FINAL.md`

## GKE Release Onboarding
- Configure `GCP_PROJECT_ID`, `GCP_WORKLOAD_IDENTITY_PROVIDER`, `GCP_SERVICE_ACCOUNT`, `GKE_CLUSTER_NAME`, `GKE_CLUSTER_LOCATION`, and `GKE_IMAGE_REPOSITORY`.
- Set `MCP_ENDPOINT`, `MCP_TOKEN`, and optionally `MCP_WEBHOOK_SECRET` for deployment notifications.
- Run `Release GKE Deploy` via `workflow_dispatch` (with `image_tag`) or push a `v*` tag.
- The preflight gate checks MCP readiness at `/cicd/status/{sha}` before deployment.

## Validation Run
```powershell
python -m py_compile agents\cicd_monitor_agent.py orchestrator\webhook.py
python -m pytest -q -o addopts="" tests/test_webhook_cicd_monitor.py
python -m pytest -q -o addopts="" tests/test_workflow_actions.py
```

## Reviewer Checklist
- [ ] `MCP_ENDPOINT` and `MCP_TOKEN` secrets are set for workflow hooks
- [ ] If signature mode is required, set `MCP_WEBHOOK_SECRET` in GitHub and `GITHUB_WEBHOOK_SECRET` in MCP runtime
- [ ] `cicd-monitor.yml` is enabled and receives workflow_run events
- [ ] `/cicd/status/{sha}` returns expected readiness for a recent commit


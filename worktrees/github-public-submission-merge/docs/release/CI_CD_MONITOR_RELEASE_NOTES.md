# CI/CD Monitor Release Notes

## Release
- Name: CI Monitor Agent + Signed Webhook Ingestion
- Date: 2026-02-19
- Scope: production CI/CD signal routing, workflow hardening, release readiness status APIs

## Included
1. New monitor agent:
   - `agents/cicd_monitor_agent.py`
2. New CI/CD runtime APIs:
   - `POST /webhooks/github/actions`
   - `GET /cicd/status/{head_sha}`
   - `GET /cicd/run/{run_id}`
3. Workflow wiring:
   - `.github/workflows/cicd-monitor.yml`
   - `.github/workflows/agents-ci-cd.yml` (`notify-cicd-monitor` job)
4. Workflow correctness fixes:
   - `.github/workflows/main.yml` now calls `/plans/ingress`
   - `.github/workflows/integration_test.yml` rebuilt and validated
5. Security:
   - GitHub HMAC signature validation (`X-Hub-Signature-256`) when `GITHUB_WEBHOOK_SECRET` is set

## Onboarding Quickstart
1. Configure repository secrets:
   - `MCP_ENDPOINT`
   - `MCP_TOKEN`
   - `MCP_WEBHOOK_SECRET` (recommended for signature mode)
2. Configure orchestrator runtime env:
   - `WEBHOOK_SHARED_SECRET` (token mode)
   - `GITHUB_WEBHOOK_SECRET` (signature mode)
3. Trigger any monitored workflow:
   - `Agents CI/CD`
   - `Python application`
   - `A2A-MCP Integration Tests`
4. Verify status:
   - `GET /cicd/status/{head_sha}`

## Compatibility Notes
- Legacy `POST /ingress` remains available and internally routes to `/plans/ingress`.
- Signature mode is opt-in. If `GITHUB_WEBHOOK_SECRET` is not set, token mode remains active.

## Operator Runbook
1. If monitor endpoint returns `401`:
   - Check token or signature secret configuration mismatch.
2. If `ready_for_release` is `false`:
   - Inspect `missing_workflows`, `incomplete_workflows`, `failed_workflows`.
3. If status data is missing:
   - Verify workflow hook job executed and can reach `MCP_ENDPOINT`.

## Validation Commands
```powershell
python -m py_compile agents\cicd_monitor_agent.py orchestrator\webhook.py
python -m pytest -q -o addopts="" tests/test_webhook_cicd_monitor.py
python -m pytest -q -o addopts="" tests/test_workflow_actions.py
```

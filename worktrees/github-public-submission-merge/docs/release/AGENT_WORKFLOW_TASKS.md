# Agent Workflow Tasks

## Objective
Define explicit agent responsibilities as workflow tasks for production CI/CD operation.

## Task Matrix

### ManagingAgent
- Task: Gate release progression based on workflow readiness.
- Input:
  - `GET /cicd/status/{head_sha}`
- Output:
  - Release gate decision: `ready_for_release` and `production_ready`
- Workflow touchpoints:
  - `.github/workflows/agents-ci-cd.yml`
  - `.github/workflows/cicd-monitor.yml`

### OrchestrationAgent
- Task: Route workflow lifecycle signals into MCP webhook ingestion.
- Input:
  - GitHub `workflow_run` completion events
- Output:
  - `POST /webhooks/github/actions` payload dispatch
- Workflow touchpoints:
  - `.github/workflows/cicd-monitor.yml`
  - `.github/workflows/agents-ci-cd.yml` (`notify-cicd-monitor`)

### CoderAgent
- Task: Maintain compatibility and endpoint correctness for ingress paths.
- Input:
  - Workflow trigger path requirements
- Output:
  - Stable ingress APIs (`/plans/ingress` and compatibility `/ingress`)
- Code touchpoints:
  - `orchestrator/webhook.py`
  - `.github/workflows/main.yml`

### TesterAgent
- Task: Validate workflow and webhook wiring on each change.
- Input:
  - YAML workflow files
  - webhook behavior
- Output:
  - Passing checks:
    - `tests/test_workflow_actions.py`
    - `tests/test_webhook_cicd_monitor.py`
- Workflow touchpoints:
  - `Agents CI/CD` unit-test lane

### CICDMonitorAgent
- Task: Normalize workflow runs and compute release readiness by commit.
- Input:
  - `workflow_run` payloads
- Output:
  - Commit-level readiness status
  - Workflow run snapshots
- Code touchpoint:
  - `agents/cicd_monitor_agent.py`

## Security Tasks
1. Enforce signature verification in production:
   - Set `GITHUB_WEBHOOK_SECRET` in MCP runtime.
   - Set `MCP_WEBHOOK_SECRET` in GitHub Actions secrets.
2. Keep token fallback only for non-production/local environments.

## Workflow Tasks
1. Run `Agents CI/CD` to produce schema/contracts and unit pass signal.
2. Run `Python application` and `A2A-MCP Integration Tests`.
3. Run `CI/CD Monitor Hook` (`workflow_run`) to emit terminal signal to MCP.
4. Query `/cicd/status/{head_sha}` before release tagging.

## Release Handoff Checklist
- [ ] Required secrets configured
- [ ] CI monitor endpoint reachable from GitHub runners
- [ ] Signature verification enabled (recommended)
- [ ] Status endpoint reflects all required workflows
- [ ] Release gate decision recorded in PR

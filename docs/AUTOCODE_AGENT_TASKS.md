# A2A_MCP Autocode Agent Task Backlog

Root repository for all coding-agent commits and PRs:

- `/mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP`

Branch convention:

- `agent/<task-id>-<short-name>`

Commit convention:

- `agent(<task-id>): <summary>`

## Task Board

| Task ID | Title | Primary Agent | Depends On | Output |
|---|---|---|---|---|
| `AAT-001` | Regenerate env map and templates | `orchestration` | None | Updated `build/env_map/*` and `build/actions_templates/*` |
| `AAT-002` | Refresh per-agent env contracts | `architecture` | `AAT-001` | Updated `.env.*.example` contracts |
| `AAT-003` | Wire reusable CI runtime workflows | `coder` | `AAT-001` | `.github/workflows/reusable-agent-ci.yml`, `.github/workflows/reusable-mcp-runtime.yml` |
| `AAT-004` | Add onboarding orchestration workflow | `coder` | `AAT-003` | `.github/workflows/onboard-agents.yml` |
| `AAT-005` | Configure GitHub environment secrets | `managing` | `AAT-004` | `dev`, `staging`, `prod` environments + secret keys |
| `AAT-006` | Execute first agent PR cycle | `tester` | `AAT-005` | Green PR checks with reusable workflows |
| `AAT-007` | Promote deployment lanes | `managing` | `AAT-006` | Verified `dev -> staging -> prod` promotions |

## Execution Tasks

### AAT-001 — Regenerate env map and templates

```bash
python3 /home/eqhspam/.codex/skills/a2a-mcp-agent-env-map/scripts/build_agent_env_map.py \
  --repo-root /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP --format both
python3 /home/eqhspam/.codex/skills/a2a-mcp-agent-env-map/scripts/generate_actions_templates.py \
  --repo-root /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP --template-scope account
```

Definition of done:
- `build/env_map/agent_env_map.json` exists and is valid JSON.
- `build/actions_templates/secrets-matrix.template.json` exists.

### AAT-002 — Refresh per-agent env contracts

```bash
python3 /home/eqhspam/.codex/skills/a2a-mcp-agent-env-map/scripts/generate_env_contracts.py \
  --repo-root /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP
```

Definition of done:
- `.env.agent.*.example`, `.env.runtime.*.example`, `.env.shared.global.example` are present.
- No secret values are committed in env files.

### AAT-003 — Wire reusable CI/runtime workflows

Definition of done:
- Reusable workflow files exist under `.github/workflows/`.
- Workflows are configured with `on.workflow_call`.
- `agent-ci` and `runtime` contracts consume env/secrets placeholders only.

### AAT-004 — Add onboarding orchestration workflow

Definition of done:
- `.github/workflows/onboard-agents.yml` exists.
- Workflow calls reusable CI and runtime workflows.
- Workflow runs in PR context of `A2A_MCP`.

### AAT-005 — Configure GitHub environments and secrets

Required environments:
- `dev`
- `staging`
- `prod`

Minimum secret keys:
- `MCP_ENDPOINT`
- `MCP_TOKEN`
- `WIF_PROVIDER`
- `WIF_SERVICE_ACCOUNT`
- `MCP_SERVER_AUDIENCE`
- `MCP_INGEST_ENDPOINT`
- `GITHUB_MCP_API_URL` (optional)

Definition of done:
- Keys are present in each required GitHub Environment.
- Production environment has required reviewers enabled.

### AAT-006 — Execute first agent PR cycle

```bash
cd /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP
git checkout -b agent/AAT-006-first-autocode-pr
git add -A
git commit -m "agent(AAT-006): run first autocode PR cycle"
git push -u origin agent/AAT-006-first-autocode-pr
```

Definition of done:
- PR opened against `main`.
- Reusable `agent-ci` and `runtime` jobs pass.

### AAT-007 — Promote deployment lanes

Definition of done:
- Promotion is executed in order `dev -> staging -> prod`.
- Deployment evidence is attached to PR/Release notes.

## Operating Rules for Coding Agents

1. Always commit to the root repo (`A2A_MCP`), never to `vh2-docker`.
2. Each task maps to one branch and one PR whenever possible.
3. MCP runtime assignments must reference the same branch under review.
4. Never commit `.env`; only commit `.env.*.example` files.

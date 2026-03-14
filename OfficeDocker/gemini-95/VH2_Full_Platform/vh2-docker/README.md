# VH2 · Sovereign Suspension Rig — Docker Deploy

**Advan GT Beyond C5 · 5-spoke · KPI 12.5° · Ackermann Steering · SHA-256 Witnessed**

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                     BROWSER / MOBILE                │
└────────────────────────┬────────────────────────────┘
                         │ :80
              ┌──────────▼──────────┐
              │    NGINX PROXY      │  (vh2-public network)
              │  reverse proxy +    │
              │  gzip + cache hdrs  │
              └─────┬─────────┬─────┘
                    │         │         (vh2-internal network)
         /api/*     │         │  /*
     ┌──────────────▼─┐   ┌───▼──────────────────┐
     │ BACKEND SOCKET  │   │  FRONTEND SOCKET     │
     │  Express :3001  │   │   Express :3000      │
     │                 │   │                      │
     │  POST /validate │   │  GET /               │
     │  GET  /spec     │   │  GET /vehicle.html   │  ← VH2 Sim artifact
     │  GET  /kpi      │   │  GET /tests.html     │  ← Unit test artifact
     │  GET  /ackermann│   │  GET /vh2-plugin.js  │  ← Web Component
     │  GET  /health   │   │                      │
     └─────────────────┘   └──────────────────────┘
```

## Quick Start

```bash
# Clone / unzip this folder, then:
chmod +x scripts/deploy.sh

# Full pipeline (test → build → deploy → validate)
./scripts/deploy.sh

# Then open:
#   http://localhost              ← plugin demo
#   http://localhost/vehicle.html ← raw simulation
#   http://localhost/tests.html   ← unit test runner
#   http://localhost/api/spec     ← canonical spec + witness hash
```

## Commands

| Command | Action |
|---|---|
| `./scripts/deploy.sh` | Full pipeline: test → build → up → validate |
| `./scripts/deploy.sh test` | Server-side unit tests only (fail-closed) |
| `./scripts/deploy.sh build` | Build Docker images |
| `./scripts/deploy.sh up` | Start stack |
| `./scripts/deploy.sh down` | Stop stack |
| `./scripts/deploy.sh validate` | Hit live API with canonical spec |
| `./scripts/deploy.sh logs` | Tail all service logs |
| `./scripts/deploy.sh status` | Show health + endpoints |
| `./scripts/deploy.sh clean` | Remove all containers + images |

## Agent Env Mapping (A2A_MCP)

Use the installed Codex skill `a2a-mcp-agent-env-map` to generate per-agent env contracts and reusable GitHub Actions templates from the A2A_MCP repo.

```bash
# Build env map (json + markdown)
python3 /home/eqhspam/.codex/skills/a2a-mcp-agent-env-map/scripts/build_agent_env_map.py \
  --repo-root /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP \
  --format both

# Generate per-agent and runtime env contract examples
python3 /home/eqhspam/.codex/skills/a2a-mcp-agent-env-map/scripts/generate_env_contracts.py \
  --repo-root /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP

# Generate reusable account-wide Actions templates + secrets matrix
python3 /home/eqhspam/.codex/skills/a2a-mcp-agent-env-map/scripts/generate_actions_templates.py \
  --repo-root /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP \
  --template-scope account
```

Generated outputs:
- `build/env_map/agent_env_map.json`
- `build/env_map/agent_env_map.md`
- `build/actions_templates/agent-ci-template.yml`
- `build/actions_templates/mcp-runtime-template.yml`
- `build/actions_templates/secrets-matrix.template.json`

## Autocode Agent Onboarding (Deployment)

Use this checklist to onboard coding agents so they can generate code and auto-run deployment workflows with per-agent env boundaries.

1. Generate contracts and templates from source-of-truth repo.

```bash
python3 /home/eqhspam/.codex/skills/a2a-mcp-agent-env-map/scripts/build_agent_env_map.py \
  --repo-root /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP --format both
python3 /home/eqhspam/.codex/skills/a2a-mcp-agent-env-map/scripts/generate_env_contracts.py \
  --repo-root /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP
python3 /home/eqhspam/.codex/skills/a2a-mcp-agent-env-map/scripts/generate_actions_templates.py \
  --repo-root /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP --template-scope account
```

2. Assign env contracts by agent role.
- Core coding agents (`managing`, `orchestration`, `architecture`, `coder`, `tester`) use global shared keys:
  - `DATABASE_URL`, `LLM_ENDPOINT`, `LLM_MODEL`, `A2A_ORCHESTRATION_MODEL`, `A2A_ORCHESTRATION_EMBEDDING_LANGUAGE`
- Notification agent additionally uses:
  - `WHATSAPP_NOTIFICATIONS_ENABLED`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `WHATSAPP_FROM`, `WHATSAPP_TO`, `WHATSAPP_CHANNEL_BRIDGE_TO`
- Runtime bridge and MCP routing use:
  - `A2A_MCP_PROVIDER`, `A2A_MCP_TOOL_NAME`, `A2A_MCP_ENDPOINT`, `A2A_MCP_API_TOKEN`
- RBAC runtime uses:
  - `RBAC_SECRET`, `DATABASE_URL`

3. Configure GitHub Environments for deployment lanes.
- Create `dev`, `staging`, `prod` environments in repository settings.
- Load secret names from `build/actions_templates/secrets-matrix.template.json`.
- Add required environment secrets (examples):
  - `MCP_ENDPOINT`, `MCP_TOKEN`, `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`, `MCP_SERVER_AUDIENCE`, `MCP_INGEST_ENDPOINT`
  - optional `GITHUB_MCP_API_URL`

4. Wire reusable workflows into target repositories.
- Copy:
  - `build/actions_templates/agent-ci-template.yml`
  - `build/actions_templates/mcp-runtime-template.yml`
- Reference them from project workflows using `workflow_call` so coding agents invoke standardized CI/runtime jobs.

### Root Repo + Commit Routing (Required)

For this agentic deployment flow, treat this repository as the root GitHub source of truth:

- Root repo path: `/mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP`
- All coding-agent branches, commits, and PRs should be created from `A2A_MCP` (not from `vh2-docker`).

Local task workflow for coding agents:

```bash
cd /mnt/c/Users/eqhsp/Documents/GitHub/A2A_MCP
git checkout -b agent/<task-id>-<short-name>
# implement task changes
git add -A
git commit -m "agent(<task-id>): <summary>"
git push -u origin agent/<task-id>-<short-name>
```

MCP to Actions routing rule:
- MCP-generated runtime assignments and env contracts must point Actions to the same root repo branch that contains the code change.
- Workflow templates must run in the PR repository context (`A2A_MCP`) so checks, secrets, and deployment promotions attach to the correct PR and branch.
- If an agent works from another local folder, it must still open PRs against `A2A_MCP` as upstream.

5. Run first autocode deployment cycle.
- Agent creates/updates code in feature branch.
- CI template validates tests and contracts.
- Runtime template validates MCP/runtime env contract before merge/deploy.
- Promote from `dev` -> `staging` -> `prod` using environment protections.

6. Safety gates (required).
- Never commit `.env` with values.
- Keep `.env.*.example` contracts in git.
- Restrict production deploy to protected branches + required reviewers.
- Re-run env map scripts when agent roles, workflows, or MCP tools change.

## Plugin Embed

Drop into **any website** with two lines:

```html
<script src="https://yourdomain.com/vh2-plugin.js" defer></script>
<vh2-simulator mode="sim" api-base="https://yourdomain.com/api" height="600px"></vh2-simulator>
```

### Attributes

| Attribute | Values | Default |
|---|---|---|
| `mode` | `sim` \| `test` \| `split` | `sim` |
| `api-base` | URL to backend API | `/api` |
| `height` | Any CSS height | `600px` (auto on mobile) |

### Events

```js
document.querySelector('vh2-simulator').addEventListener('vh2:validated', e => {
  console.log(e.detail.witness.tag)   // 0xVH2_ET29_ET22_C5_SOV_XXXXXX
  console.log(e.detail.pass)          // true | false
})
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe |
| `GET` | `/api/spec` | Canonical spec + witness hash |
| `POST` | `/api/validate` | Fail-closed constraint validator |
| `POST` | `/api/witness` | SHA-256 hash any object |
| `GET` | `/api/ackermann/:deg` | Ackermann angles at steer angle |
| `GET` | `/api/kpi` | KPI kinematics constants |

### Validate Example

```bash
curl -X POST http://localhost/api/validate \
  -H 'Content-Type: application/json' \
  -d '{"spoke_count":5,"rim_diameter_in":19,"front_et_mm":29,
       "rear_et_mm":22,"kpi_deg":12.5,"scrub_radius_mm":45,"c5_sector_deg":72}'

# → {"pass":true,"status":"SOVEREIGN_PASS","witness":{"tag":"0xVH2_ET29_ET22_C5_SOV_..."}}
# Tampered field → {"pass":false,"status":"SYSTEM_HALT","violations":[...]}
```

## Physical Invariants

| Constraint | Value |
|---|---|
| Spoke count | 5 (C5 symmetry, 72° pitch) |
| Rim diameter | 19" |
| Front offset | ET+29mm · concavity 0.150 |
| Rear offset | ET+22mm · concavity 0.185 |
| KPI angle | 12.5° |
| Scrub radius | 45mm (positive) |
| Han eigenvalue | 0.82mm |
| Hausdorff limit | < 0.20mm |
| Ising universality | 0.9982 |

## Production Deploy

```bash
ALLOWED_ORIGIN=https://yourdomain.com \
  docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

*SHA-256 Witnessed · Saintly Honesty Enforced · Three.js r128 · Node 20 LTS*

# ChatGPT App MCP Embeddings Integration

This document defines the canonical ChatGPT App workflow for MCP embeddings and orchestration in `A2A_MCP`.

## Components

- Backend MCP gateway: `app.mcp_gateway:app` (`/mcp`, `/tools/call`)
- Tool implementation: `app.mcp_tooling`
- ChatGPT App package: `chatgpt-app/`
- Mirror target: `C:\Users\eqhsp\.codex\worktrees\47cf\projects\chatgpt-app`
- Mirror sync command: `python scripts/sync_chatgpt_app_mirror.py`

## Env Contract

Backend (`.env.example`):

- `CHATGPT_APP_DOMAIN`
- `CHATGPT_APP_BACKEND_URL`
- `GITHUB_OAUTH_CLIENT_ID`
- `GITHUB_OAUTH_CLIENT_SECRET`
- `GITHUB_OAUTH_REDIRECT_URI`
- `CHATGPT_APP_PRIVACY_URL`
- `CHATGPT_APP_SUPPORT_URL`
- `GITHUB_OAUTH_REQUIRED_SCOPES_READ`
- `GITHUB_OAUTH_REQUIRED_SCOPES_WRITE`

ChatGPT app package (`chatgpt-app/.env.example`) mirrors these values plus:

- `CHATGPT_APP_BACKEND_BEARER` (optional service token for local integration)
- `CHATGPT_APP_TIMEOUT_MS`

## Local Smoke

1. Install Python deps:
   - `pip install -e .[dev,integrations]`
2. Start backend gateway:
   - `uvicorn app.mcp_gateway:app --host 0.0.0.0 --port 8080`
3. Start orchestrator:
   - `uvicorn orchestrator.api:app --host 0.0.0.0 --port 8000`
4. Start ChatGPT app server:
   - `npm install --prefix chatgpt-app`
   - `npm run dev --prefix chatgpt-app`
5. Tunnel app endpoint and attach in ChatGPT Developer Mode:
   - `https://<tunnel>/mcp`

## Submission Checklist

- Stable HTTPS app endpoint and production MCP path.
- OAuth client configured and secret-managed (`GITHUB_OAUTH_*`).
- Privacy/support URLs populated.
- CSP domains set to exact backend/resource origins.
- Hybrid tool surface validated:
  - `embedding_search`
  - `embedding_upsert`
  - `embedding_workspace_data`
  - `orchestrate_command`
  - `render_embedding_workspace`

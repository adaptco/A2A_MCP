---
description: Deploy the sovereign orchestrator pipeline to a GitHub repository
---

# Deploy Pipeline

## Steps

1. Ensure all GitHub Secrets are configured in your repo settings:
   - `ANTHROPIC_API_KEY` — for Claude agents
   - `OPENAI_API_KEY` — for GPT agents
   - `GEMINI_API_KEY` — for Gemini agents
   - `ECHO_MCP_TOKEN` — for Echo relay broker
   - `GLOH_MCP_TOKEN` — for Gloh RAG vector store

// turbo
2. Stage all sovereign-orchestrator files:

```bash
git add sovereign-orchestrator/
```

// turbo
3. Commit the framework:

```bash
git commit -m "feat: add sovereign-orchestrator coding agent pipeline framework"
```

// turbo
4. Push to GitHub:

```bash
git push origin HEAD
```

1. Verify the `Sovereign Orchestrator` workflow appears in the Actions tab.

2. Trigger a test run via `workflow_dispatch` with a sample prompt.

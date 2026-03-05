---
description: Execute a single agent task locally or via GitHub Actions
---

# Run Agent Task

## Local Execution

// turbo

1. Set environment variables:

```bash
export LLM_TARGET=gemini
export GEMINI_API_KEY=your-key
export TASK_ID=T-001
export AGENT_CARD=agents/Celine/planner.py
export USER_PROMPT="Build a REST API for user management"
```

// turbo
2. Run the agent:

```bash
cd sovereign-orchestrator
python agents/runner.py
```

1. Check the output:

```bash
cat artifacts/T-001/output.txt
cat receipts/T-001.json
```

## Via GitHub Actions

1. Go to the repository Actions tab
2. Select "Sovereign Orchestrator"
3. Click "Run workflow"
4. Enter your prompt and click "Run"

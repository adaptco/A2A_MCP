---
name: mcp-entropy-template-router
description: Generate deterministic MCP routing controls that combine API skill tokens, enthalpy/entropy style temperature tuning, and uniform dotproduct template selection for frontend/backend/fullstack actions. Use when orchestrator payloads need stable template-triggered implementation actions and avatar runtime token bindings.
---

# MCP Entropy Template Router

Produce deterministic routing metadata for coding-agent execution.

## Do This

1. Run `scripts/route_actions.py` with prompt, risk profile, and changed-path count.
2. Attach output fields to orchestration artifacts (`api_skill_tokens`, `style_temperature_profile`, `template_route`).
3. Use `selected_actions` to trigger implementation templates for frontend, backend, or fullstack flows.

## Command

```bash
python skills/mcp-entropy-template-router/scripts/route_actions.py \
  --prompt "Resolve merge conflict and patch API runtime" \
  --risk-profile high \
  --changed-path-count 14
```

## Outputs

- `temperature` (style control)
- `selected_template` and `selected_actions` (execution trigger)
- `api_skill_tokens` (avatar/runtime shell API bindings)

## Read When Needed

- Runtime field contract: `references/runtime_contract.md`

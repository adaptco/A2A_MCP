---
name: mcp-entropy-template-router
<<<<<<< HEAD
description: Generate deterministic MCP bridge routing and embedding-aware template controls for A2A_MCP Node.js or TypeScript implementations. Use when building or updating the A2A_MCP `/mcp` bridge, ChatGPT app MCP server, embedding search/upsert/workspace tools, or runtime bridge payloads that need stable `api_skill_tokens`, `style_temperature_profile`, and `template_route` values for frontend/backend/fullstack actions.
=======
description: Generate deterministic MCP routing controls that combine API skill tokens, enthalpy/entropy style temperature tuning, and uniform dotproduct template selection for frontend/backend/fullstack actions. Use when orchestrator payloads need stable template-triggered implementation actions and avatar runtime token bindings.
>>>>>>> origin/main
---

# MCP Entropy Template Router

<<<<<<< HEAD
Produce deterministic routing metadata for A2A_MCP MCP bridge execution.

## Do This

1. For A2A_MCP `/mcp` bridge work, treat `chatgpt-app/src/server.ts` as the primary Node.js template and `src/mcp_adk/templates/ts_agent/` as the minimal TypeScript agent package shape.
2. Run `scripts/route_actions.py` with prompt, risk profile, and changed-path count.
3. Attach output fields to orchestration artifacts or `RuntimeAssignmentV1` payloads (`api_skill_tokens`, `style_temperature_profile`, `template_route`).
4. Map `selected_template` into bridge scope:
   - `frontend`: widget/resource surface
   - `backend`: MCP server/tool handler surface
   - `fullstack`: `/mcp` route plus widget/tool surfaces
5. Keep bridge tools aligned with the embedding vocabulary already used in `chatgpt-app/src/server.ts`: `embedding_search`, `embedding_upsert`, `embedding_workspace_data`, `render_embedding_workspace`, and `orchestrate_command`.
=======
Produce deterministic routing metadata for coding-agent execution.

## Do This

1. Run `scripts/route_actions.py` with prompt, risk profile, and changed-path count.
2. Attach output fields to orchestration artifacts (`api_skill_tokens`, `style_temperature_profile`, `template_route`).
3. Use `selected_actions` to trigger implementation templates for frontend, backend, or fullstack flows.
>>>>>>> origin/main

## Command

```bash
python skills/mcp-entropy-template-router/scripts/route_actions.py \
<<<<<<< HEAD
  --prompt "Scaffold the A2A_MCP /mcp bridge as a Node.js template" \
  --risk-profile medium \
  --changed-path-count 6
=======
  --prompt "Resolve merge conflict and patch API runtime" \
  --risk-profile high \
  --changed-path-count 14
>>>>>>> origin/main
```

## Outputs

- `temperature` (style control)
<<<<<<< HEAD
- `style_temperature_profile` (`enthalpy`, `entropy`, `temperature`, `model_style_preferences`)
- `template_route` (`template_scores`, `selected_template`, `selected_actions`)
- `api_skill_tokens` (avatar/runtime shell API bindings)
- deterministic template selection that can be serialized into `schemas/runtime_bridge.RuntimeAssignmentV1`
=======
- `selected_template` and `selected_actions` (execution trigger)
- `api_skill_tokens` (avatar/runtime shell API bindings)
>>>>>>> origin/main

## Read When Needed

- Runtime field contract: `references/runtime_contract.md`
<<<<<<< HEAD
- Node.js MCP bridge template: `chatgpt-app/src/server.ts`
- Runtime handoff builder: `orchestrator/runtime_bridge.py`
- Worldline embedding producer: `world_foundation_model.py`
- Minimal TypeScript agent template: `src/mcp_adk/templates/ts_agent/package.json`
=======
>>>>>>> origin/main

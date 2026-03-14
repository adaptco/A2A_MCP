---
name: avatar-mcp-root-context
description: Build zero-shot root-repo launch context for Codex avatar flows in the A2A_MCP repository by combining AGENTS.md, avatar bindings, frontier agent cards, and MCP tool surfaces into a compact packet. Use when API-triggered avatar tokens must launch from the MCP node, when a chat model needs root GitHub codebase context before tool use, or when preparing payloads for ingest_repository_data, ingest_avatar_token_stream, build_local_world_foundation_model, get_coding_agent_avatar_cast, or route_a2a_intent.
---

# Avatar MCP Root Context

## Overview

Build the smallest repo-grounded context packet for avatar-triggered MCP launches in `A2A_MCP`.
Prefer the root artifacts and MCP entrypoints that already exist in the repo instead of reconstructing the launch surface ad hoc.

## Quick Start

1. Run the snapshot script to produce a zero-shot launch packet from the repo root.
2. Use that packet as the briefing for the downstream Codex instance or API-triggered MCP run.
3. Read `references/root-artifact-map.md` only when you need the payload rules or the file-selection rationale.

```bash
python skills/avatar-mcp-root-context/scripts/build_zero_shot_avatar_context.py \
  --prompt "Investigate the API-triggered avatar launch path from the MCP node"
```

## Workflow

1. Treat the repo root as the source of truth.
   Read `AGENTS.md`, `AVATAR_SYSTEM.md`, `avatar_bindings.v1.json`, `registry/agents/frontier_agent_index.v1.json`, `registry/agents/frontier_agent_cards.v1.json`, `app/mcp_tooling.py`, `runtime_mcp_server.py`, and `embed_control_plane.py` before inventing new launch rules.
2. Build a compact zero-shot packet first.
   Run `scripts/build_zero_shot_avatar_context.py` with the current prompt and commit so the next model gets a concise, hashable summary instead of a raw file dump.
3. Choose the launch surface deliberately.
   Use `runtime_mcp_server.py` for API-driven runtime launches and `route_a2a_intent` flows.
   Use `mcp_server.py` only when the client explicitly needs the stdio compatibility server.
4. Use the protected tool path for repo and token ingestion.
   `ingest_repository_data` and `ingest_avatar_token_stream` require bearer authorization and should be treated as verified ingress surfaces, not casual helper calls.
5. Keep the model-visible state small.
   Pass repository slug, commit SHA, prompt, actor, risk profile, avatar namespace, and artifact references or hashes.
   Do not dump large code blobs into the packet unless the downstream task truly needs them.

## Tool Order

Use this order unless the user explicitly asks for a different one:

- `get_coding_agent_avatar_cast`
  Use when the launch needs the embodied avatar mapping for coding agents.
- `build_local_world_foundation_model`
  Use when the chat model needs a root-repo context block before the protected ingestion calls.
- `ingest_repository_data`
  Use to verify and ingest the repository snapshot with a bearer token tied to the repository claim.
- `ingest_avatar_token_stream`
  Use to namespace and shape the API-triggered avatar tokens before model execution.
- `route_a2a_intent`
  Use to hand the prepared intent into the runtime MCP surface.

## Packet Rules

- Prefer artifact references and hashes over long file excerpts.
- Keep the repository snapshot rooted at the repo root, not a nested package copy.
- Treat `frontier_agent_index.v1.json` and `frontier_agent_cards.v1.json` as the authoritative frontier-agent capability map.
- Regenerate the frontier index with `make frontier-index` or `python scripts/build_frontier_agent_index.py` if those artifacts are stale or missing.
- Keep bearer tokens and RBAC token bundles out of committed files and out of the skill output.

## Read When Needed

- `references/root-artifact-map.md`
  Read for the repo artifact map, payload shape reminders, and launch-surface selection guidance.

## Script

- `scripts/build_zero_shot_avatar_context.py`
  Build a compact JSON packet that summarizes the root repo, avatar cast, frontier agent cards, protected MCP tools, and suggested payloads for token-triggered launches.

```bash
python skills/avatar-mcp-root-context/scripts/build_zero_shot_avatar_context.py \
  --prompt "Prepare a zero-shot avatar launch packet for the repo root" \
  --risk-profile medium \
  --output out/avatar-context.json
```

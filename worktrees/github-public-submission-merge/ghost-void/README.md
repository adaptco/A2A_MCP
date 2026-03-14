# world-os-codex

[![.github/workflows/ci.yml](https://github.com/Q-Enterprises/core-orchestrator/actions/workflows/ci.yml/badge.svg)](https://github.com/Q-Enterprises/core-orchestrator/actions/workflows/ci.yml)

Monorepo delivering the Synapse digital twin, Chrono-Sync protocol, Asset Forge, and World OS kernel. Everything runs with one Docker compose stack.

## Commands
- `pnpm i`
- `docker compose up --build`
- `pnpm test`
- `pnpm dev`
- `pnpm chain:up`
- `pnpm contracts:deploy`

## Structure
- `packages/kernel`: deterministic SSOT, schemas, reducer, replay helpers.
- `packages/contracts`: TimekeepersTFT ERC-721 + tests + deploy script.
- `packages/sdk`: shared types and API client.
- `apps/api`: Fastify API serving game/chrono/forge endpoints.
- `apps/web`: React + Vite SPA with game, sync, and case views.
- `apps/worker`: BullMQ Forge processor.

## Local stack
- Web: http://localhost:5173
- API: http://localhost:3001
- Anvil: http://localhost:8545

### Data flow
- Game actions are validated against JSON Schemas and reduced through the kernel.
- Chrono-Sync issues signed challenges before minting TFTs on the local chain.
- Asset Forge requests enqueue jobs persisted to Postgres with Redis cache via BullMQ.
- Kernel reductions are CI-gated for determinism and schema compliance.

### Setup
1. Copy `.env.example` to `.env` if you need overrides.
2. Install: `pnpm i`
3. Bring up services: `docker compose up --build`
4. Run tests: `pnpm test`
5. Seed the initial state: `pnpm --filter @world-os/api seed`
6. Deploy contracts to anvil: `pnpm chain:up` (in another terminal) then `pnpm contracts:deploy`

### Notes
- Reducer is pure/deterministic; state hashes use stable JSON stringification.
- Chat text never mutates state; only canonical JSON actions do.
- Chrono-Key registry is hashed in-memory to avoid leaking secrets in logs.

## Runtime memory strategy

| Strategy | Optimizes for | Best for |
| --- | --- | --- |
| Direct visual recall | Visual similarity and continuity | Cinematic composition and art direction |
| Semantic state mapping | Physics and constraint invariants | Deterministic gameplay and agent control loops |

Recommended layering:
1. Use semantic state mapping as the kernel to drive deterministic behavior.
2. Use direct visual recall as a rendering overlay for visual continuity.

Kernel-first sequencing:
1. Define a physics and affordance tagging rubric to anchor retrieval and policy.
2. Specify LoRA routing logic that depends on the rubric’s tags.
3. Formalize the vector schema that serializes embeddings, tags, and outcomes.

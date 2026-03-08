<!-- adaptco-ssot/README.md -->
# Adaptco Single Source of Truth (SSoT)

Adaptco SSoT is a Node.js 20 REST API that centralizes asset metadata, exposing CRUD operations backed by a JSON catalog.

## Features

- Health endpoint for uptime monitoring.
- JSON Schema validation for asset CRUD operations.
- In-memory store backed by a persisted catalog file.
- Structured logging with Pino.

## Prerequisites

- Node.js >= 20
- npm >= 9

## Setup

```bash
npm install
```

## Running Locally

```bash
npm start
```

The service listens on port 3000 by default.

### Example Requests

List assets:

```bash
curl http://localhost:3000/assets
```

Create an asset:

```bash
curl -X POST http://localhost:3000/assets \
  -H "Content-Type: application/json" \
  -d '{
    "id": "asset-200",
    "name": "Storyboard",
    "kind": "document",
    "uri": "s3://bucket/storyboard.pdf",
    "tags": ["storyboard"],
    "meta": {"owner": "creative@adaptco.io"}
  }'
```

## Scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Start with nodemon for live reload. |
| `npm run start` | Start the API in production mode. |
| `npm run build` | Placeholder build step. |
| `npm run test` | Run Jest and Supertest suite. |
| `npm run lint` | Run ESLint across the project. |
| `npm run format` | Format files via Prettier. |

## Testing

```bash
npm test
```

## Docker

```bash
docker build -t adaptco-ssot .
docker run --rm -p 3000:3000 adaptco-ssot
```

## Data Model

The API enforces [`schemas/asset.schema.json`](schemas/asset.schema.json) for all mutations. Assets must include a `registry` packet that mirrors the `ssot.registry.v1` capsule structure:

- `capsule_id` — fixed to `ssot.registry.v1` for archive alignment.
- `registry` — sovereign archive metadata (`name`, `version`, `maintainer`).
- `entry` — canonical artifact facts (author, created_at, `canonical_sha256`, `merkle_root`, and council attestation signatures).
- `lineage` — immutable parent/fork references with maker–checker provenance.
- `replay` — authorization envelope describing integrity gates and override protocol.

Initial catalog entries live in [`data/catalog.json`](data/catalog.json) and demonstrate the required structure.

## Project Structure

```
src/
  index.js
  server.js
  log.js
  validator.js
  store.js
schemas/
  asset.schema.json
data/
  catalog.json
```

## License

MIT

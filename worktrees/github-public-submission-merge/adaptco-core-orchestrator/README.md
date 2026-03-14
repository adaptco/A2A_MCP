<!-- adaptco-core-orchestrator/README.md -->
# Adaptco Core Orchestrator

Adaptco Core Orchestrator is a Node.js 20 microservice that receives capsule registration requests, validates them against a JSON Schema, and appends the request to a ledger for downstream coordination.

## Features

- Health endpoint for uptime monitoring.
- Capsule registration endpoint with JSON Schema validation using Ajv.
- Optional preview + SSOT coordination pipeline driven by the Sentinel agent.
- Append-only ledger that records registration events to JSON Lines for auditing.
- Structured logging via Pino.

## Prerequisites

- Node.js >= 20
- npm >= 9

## Setup

```bash
npm install
```

## Development Scripts

| Script | Description |
| --- | --- |
| `npm run dev` | Starts the service with nodemon on port 3000. |
| `npm run start` | Starts the service in production mode. |
| `npm run build` | Placeholder build step. |
| `npm run test` | Runs Jest unit tests. |
| `npm run lint` | Lints the codebase with ESLint. |
| `npm run format` | Formats files with Prettier. |
| `npm run audit` | Runs a wrapper/registry integrity check. |
| `npm run rehearsal` | Performs a rehearsal-only anchor binding check. |

## Usage

Start the service:

```bash
npm start
```

Register a capsule:

```bash
curl -X POST http://localhost:3000/capsule/register \
  -H "Content-Type: application/json" \
  -d '{
    "capsule_id": "caps-001",
    "version": "1.0.0",
    "issued_at": "2024-01-01T00:00:00Z",
    "author": "example@adaptco.io",
    "payload": {"type": "demo"},
    "provenance": {"source": "unit-test"}
  }'
```

Example response:

```json
{
  "status": "ok",
  "id": "capsule-caps-001-1.0.0",
  "received": {
    "capsule_id": "caps-001",
    "version": "1.0.0"
  }
}
```

### Auditing and rehearsal checks

Run an integrity audit of the wrapper and runtime registry (fails on missing registry, ledger, or unbound anchors):

```bash
npm run audit -- --wrapper capsules/doctrine/capsule.wrapper.adaptco_os.v1.json --registry runtime/capsule.registry.runtime.v1.json
```

Validate that rehearsal anchors are present and marked with `status: "REHEARSAL"`:

```bash
npm run rehearsal -- --wrapper capsules/doctrine/capsule.wrapper.adaptco_os.v1.json --registry runtime/capsule.registry.runtime.v1.json
```

### Optional Operations

Augment the payload with an `operations` object to wire the request into the
Previz renderer, SSOT asset registry, and the `hash_gen_scroll.py` manifest
workflow:

```json
{
  "capsule_id": "caps-001",
  "version": "1.0.0",
  "issued_at": "2024-01-01T00:00:00Z",
  "author": "example@adaptco.io",
  "payload": { "type": "demo" },
  "provenance": { "source": "unit-test" },
  "operations": {
    "preview": {
      "descriptor": {
        "id": "asset-001",
        "name": "Hero Render",
        "type": "image",
        "sourcePath": "assets/hero.glb"
      },
      "out_dir": "/tmp/previews"
    },
    "asset": {
      "payload": {
        "id": "asset-001",
        "name": "Hero Render",
        "kind": "image",
        "uri": "https://cdn.adaptco.io/assets/hero.png",
        "tags": ["marketing"],
        "meta": { "owner": "creative@adaptco.io" }
      },
      "path": "/assets"
    },
    "hash": {
      "out_dir": "data/capsules",
      "events_path": "events.ndjson",
      "capsule_id": "capsule.validation.v1"
    }
  }
}
```

When present, the orchestrator will:

1. Invoke the Previz CLI via `SentinelAgent.renderPreview()`.
2. Register the asset with the SSOT API using `SentinelAgent.registerAsset()`.
3. Execute `hash_gen_scroll.py` to emit a Merkle-rooted manifest capturing the
   generated artifacts.

## Testing

```bash
npm test
```

## Docker

```bash
# Build image
docker build -t adaptco-core-orchestrator .

# Run container
docker run --rm -p 3000:3000 adaptco-core-orchestrator
```

## JSON Schema

The capsule registration payload is validated against [`schemas/capsule.schema.json`](schemas/capsule.schema.json), which ensures a consistent format for orchestrator integrations.

## Project Structure

```
src/
  index.js
  server.js
  routes/
    capsules.js
  ledger.js
  log.js
  validator.js
schemas/
  capsule.schema.json
storage/
  ledger.jsonl (generated)
```

## License

MIT

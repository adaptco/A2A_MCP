# Sentinel single source of truth

The SSOT tier guarantees that cockpit manifests and capsules originate from validated catalog data.

## Services and schemas
- `adaptco-ssot/` – Node.js service that persists the asset catalog, enforces the JSON schema in `adaptco-ssot/schemas/asset.schema.json`,
  and exposes CRUD APIs consumed during freeze operations.
- `public/data/avatar_bindings.v1.json` – materialized manifest served to the cockpit; it should be regenerated from SSOT data
  whenever bindings change.
- `specs/avatar_bindings.v1.schema.json` – repository-wide contract describing the avatar bindings manifest used by validation jobs.

## Operational notes
Run the SSOT service locally while authoring new bindings:

```bash
cd adaptco-ssot
npm install
npm start
```

Authoritative updates must pass through the SSOT API before freeze scripts are executed to keep the Sentinel in sync with the
canonical catalog.

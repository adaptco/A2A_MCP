# Federation Ownership Contract

This contract defines strict boundaries between:

- `SSOT` (truth and schema authority)
- `core-orchestrator` (runtime authority)
- `ground` (bridge authority)

## Canonical ownership

- `SSOT` owns canonical schema contracts and proof-plane artifacts.
- `core-orchestrator` owns runtime execution, webhook ingestion, and gate logic.
- `ground` owns bridge/client adapters used to emit integration events.

Machine-readable source:

- `core-orchestrator/manifests/federation_ownership.v1.yaml`

## Typed integration contract

Canonical schema:

- `SSOT/schemas/ssot.integration.contract.v1.schema.json`

Mirrors (must remain byte-identical):

- `core-orchestrator/schemas/ssot.integration.contract.v1.schema.json`
- `ground/public/schemas/ssot.integration.contract.v1.schema.json`

## Legacy subtree policy

The following subtrees are explicitly legacy/read-only mirrors inside `core-orchestrator`:

- `core-orchestrator/adaptco-core-orchestrator`
- `core-orchestrator/adaptco-ssot`
- `core-orchestrator/adaptco-previz`

Runtime code paths must not add new dependencies on these directories.

## Drift check

Run from `core-orchestrator`:

```bash
python scripts/verify_federation_contract.py --repo-root ..
```

This verifies:

- Schema contract parity across all three repositories.
- Presence and policy continuity for declared legacy subtrees.

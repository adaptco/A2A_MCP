# Sentinel

The Sentinel packages the workflow observability and governance mesh that wraps the core orchestrator assets. It groups the
operator cockpit, automated governance jobs, ledger attestation surface, and the single-source-of-truth validation rails into a
cohesive topology for delivery and audit.

## Directory layout
- `docs/` – architectural references and runbooks for stitching the components together.
- `cockpit/` – Live Ops HUD documentation that maps to the public assets served from `public/hud`.
- `governance/` – protocol governance controls, including freeze scripts and GitHub workflows.
- `ledger/` – immutable ledger staging areas for scroll batches, proofs, and events.
- `ssot/` – single-source-of-truth interfaces and validation guardrails.
- `capsules/` – capsule catalog documentation that ties protocol contracts to cockpit surfaces.

Each leaf links back to concrete assets in the repository so operators have a canonical place to reason about the Sentinel mesh.

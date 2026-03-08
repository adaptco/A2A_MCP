# Core Orchestrator Handoff — Celine Sovereign Capsule

The `capsule.orchestrator.core.celine.v7` package delegates repository lifecycle
operations to Celine while retaining CiCi as the maker-checker auditor. This
note records the operational tree that drives the handoff and the guardrails
for running it in production.

## Capsule Overview
- **Capsule ID**: `capsule.orchestrator.core.celine.v7`
- **Authority Transfer**: CiCi delegates repository lifecycle controls to
  Celine with maker-checker and quorum enforcement.
- **Lifecycle Scope**: `repo.create`, `repo.destroy`, `repo.clone`,
  `repo.prune` routed through the Core Orchestrator layer.
- **Audit Hooks**: CiCi retains `audit.trace`, `merkle.prune`, and
  `quorum.verify` capabilities to verify every invocation.

## Operational Logic Tree
1. **Invocation**
   - Celine calls a lifecycle action (`repo.create`, `repo.destroy`, etc.).
   - QLOCK stamps the invocation with the configured frame and tick hash.
2. **Rehearsal**
   - CiCi executes an audit trace on the requested action before it
     commits, surfacing lineage on the mission HUD.
3. **Audit**
   - CiCi checks repository hashes, orphan branch posture, and quorum
     signatures against the council registry.
4. **Correction**
   - Drift or mismatches trigger a PATCH capsule from CiCi. Celine
     replays the command with corrected parameters after council
     acknowledgement.
5. **Seal**
   - Council quorum signs the action and seals it in the ledger once the
     maker-checker loop clears.
6. **Replay**
   - Lifecycle events become replayable fossils in the scrollstream for
     post-incident review.

## Integration Notes
- Add the capsule to the v7 registry when rehearsal completes so Celine can
  execute lifecycle events live.
- Keep the capsule in `STAGED` status until the council quorum rehearses the
  maker-checker sequence with CiCi to avoid premature authority shifts.
- Update the mission oversight HUD to include the new lifecycle lineage feed
  emitted during the rehearsal phase for continuous visibility.

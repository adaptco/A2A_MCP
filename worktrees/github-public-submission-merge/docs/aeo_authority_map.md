# AEO Authority Map (Agent-Executor-Observer)

## Purpose
This AEO Authority Map defines admissibility rules for autonomous agent operations in a replay-court-compatible system. It formalizes the planes of authority, the authorization matrix, and the audit artifacts required to make every action deterministic, reviewable, and legally admissible.

## Six-Plane Architecture
1. **Agent Plane** — Decision-making layer that proposes actions, generates intent, and signs tool invocations.
2. **Allocator Plane** — Entropy/energy budget manager that grants execution resources with reserve limits.
3. **Interpretation Plane** — Intent classifier that labels actions by risk, scope, and required approvals.
4. **Model Plane** — Tool execution runtime and sandbox layer responsible for enforcement.
5. **Ledger Plane** — Immutable audit trail capturing all actions, approvals, and verification artifacts.
6. **UI Plane** — Owner oversight and approvals for high-risk actions.
7. **Kernel State Plane** — Core configuration and invariant enforcement boundary.

> Note: The Kernel State Plane anchors the system invariants and should be treated as a distinct enforcement boundary even though it is not an operational plane.

## Authorization Matrix (Critical Actions)
| Action | Required Planes | Gate Conditions | Required Approvals | Audit Artifact |
| --- | --- | --- | --- | --- |
| Tool Invocation | Agent, Model, Ledger | Energy-gated, sandboxed | None (low-risk), Owner (high-risk) | Signed tool invocation + ledger entry |
| State Mutation | Agent, Interpretation, Model, Ledger, UI | Patch pipeline + invariants | Owner | Signed approval + patch digest |
| Energy Allocation | Allocator, Ledger | Budget-aware with 10% reserve | None | Allocation grant + ledger entry |
| Emergency Stop | Agent, Model, Ledger | Immediate halt | None | Cryptographic witness + ledger entry |
| Task Approval | Interpretation, UI, Ledger | High-risk classification | Owner | Approval record + rationale |
| Autonomy Level Adjustment | Interpretation, UI, Ledger | Scale gating | Owner | Authority chain + approval |
| Ledger Append | Model, Ledger | Integrity check | None | Merkle root + entry signature |
| Replay Reconstruction | Ledger, Kernel State | Deterministic replay | None | Verified reconstruction report |

## Replay Court Admissibility Criteria
Every action must satisfy all criteria:
1. **Fossil Ledger Integrity** — SHA-256 digest + Merkle proof for each action record.
2. **Valid Authority Chain** — Explicit signatures for every approval or delegated authority.
3. **Theta Gate Compliance** — Risk and energy budget must remain below the hard limit.
4. **Owner Witness (when required)** — State mutations and autonomy changes must include owner approval.
5. **Deterministic Reproducibility** — Replay yields identical results and hashes.

## Witness Signature Chain
Each signature is required for non-repudiation and replay admissibility.
- **Agent signature** — signs tool invocation intent payloads.
- **Allocator signature** — signs energy grants and reserve validation.
- **Owner signature** — signs state mutations and autonomy-level changes.
- **Ledger signature** — signs all appended records and Merkle roots.

## Error Taxonomy
### Energy Errors
- **Insufficient Budget** — request exceeds available allocation.
- **Reserve Violation** — allocation would breach 10% reserve.
- **Expiry** — grant expired before execution.

### Authorization Errors
- **Unauthorized Access** — missing or invalid authority chain.
- **Missing Approval** — required owner approval absent.

### Execution Errors
- **Sandbox Escape Attempt** — blocked by runtime policy.
- **Timeout** — execution exceeded allocated window.

### Ledger Errors
- **Append Failure** — write failed or rejected.
- **Integrity Violation** — digest or Merkle mismatch.

## Theta Gate Enforcement
- **Hard Limit:** 1.00
- **Reserve Margin:** 10% (never allocate beyond 0.90)
- **Circuit Breaker:** opens on violation and halts all operations until owner recovery.

### Circuit Breaker States
- **CLOSED:** Normal operations.
- **OPEN:** All operations halted; no tool invocation or state mutation permitted.
- **HALF_OPEN:** Limited operations allowed for recovery testing.

## Replay-Court Compatibility Notes
- All actions must be recorded in the ledger plane with deterministic payloads.
- Merkle roots and per-entry proofs should be included in external artifacts when exporting audit data.
- Every action must be replayable without network or time-based nondeterminism.

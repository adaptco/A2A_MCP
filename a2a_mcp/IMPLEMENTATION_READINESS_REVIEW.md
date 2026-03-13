# Implementation Readiness Review

This document reviews whether the current plan is implementable and what must
be resolved before execution begins.

## Executive verdict
- **Status:** Conditionally ready.
- **Reason:** The sequencing is strong, but execution is blocked by repository
  access/auth and by unresolved ownership/acceptance criteria.

## What is already solid in the plan
1. Correct migration order (interfaces before assets, then gates).
2. Clear AGENTS vs MODELS boundary intent.
3. Lightweight attestation model (`sha256` commitments) without heavy crypto.
4. CI enforcement concepts for contamination prevention.

## Blocking gaps to resolve before implementation

### 1) Access and authority (P0 blocker)
- Missing read/write access to both target repos in this environment.
- No configured git remote in local checkout for push/PR workflows.
- Owner/reviewer assignment not defined for cross-repo cutover.

**Action:** Complete `scripts/pr_preflight_check.sh` with PASS in both repos and
record command output in `SCAN_EVIDENCE.md`.

### 2) Contract specification depth (P0 blocker)
- Schemas are named but not versioned.
- Canonicalization rules for manifest hashing are not fully specified.
- Error and fallback behaviors for MCP tools are not defined.

**Action:** Add interface spec v1 with:
- canonical JSON rules (key sort, UTF-8, normalized whitespace policy),
- required/optional fields,
- backward compatibility policy,
- deterministic error codes.

### 3) CI gate thresholds and allowlists (P0 blocker)
- "Oversized ONNX" and large-file policy exist conceptually but lack numeric
  thresholds and explicit exceptions.
- Static import scan scope and false-positive handling are not defined.

**Action:** Define hard values in policy:
- max file size threshold,
- explicit allowlist paths,
- import scan include/exclude rules,
- fail/warn behavior.

### 4) Ledger/storage operational model (P1 blocker)
- Append-only semantics are stated but retention, backup, and replay are not.
- Trust boundary between ledger and artifact store is not explicit.

**Action:** Specify minimal operational model:
- immutable bucket/object policy,
- append-only record format,
- replay verification procedure,
- incident response for mismatch between artifact and commitment.

### 5) Cutover safety criteria (P1 blocker)
- No explicit go/no-go gates for each phase.
- No rollback criteria per phase.

**Action:** Add release checklist for each phase with measurable exit criteria.

## Implementation-ready checklist (must be true before PR1 coding)
- [ ] Access to both repos confirmed (clone + fetch + push dry-run).
- [ ] Branch protection and reviewer ownership defined.
- [ ] Interface spec v1 approved.
- [ ] CI thresholds/allowlists approved.
- [ ] Ledger operational model approved.
- [ ] Rollback plan approved.

## Suggested execution plan refinement

### PR1 (boundary + interfaces) readiness conditions
- Include concrete schema files and MCP tool contracts.
- Include CI gate scripts with numeric thresholds.
- Include policy docs that define false-positive handling.

### PR2 (assets + attestation) readiness conditions
- Include migration map with source/destination and ownership.
- Include ledger writer/verifier and replay checks.
- Include end-to-end verification test that proves agent runtime consumes IDs,
  commits, and URIs only.

## First implementation sprint (recommended)
1. Author `interface-spec-v1.md` with canonicalization + errors.
2. Implement CI scanners in dry-run mode first.
3. Produce baseline contamination report in both repos.
4. Turn CI gates from warn to fail after baseline exceptions are approved.

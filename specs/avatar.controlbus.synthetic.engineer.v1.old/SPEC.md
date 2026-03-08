# avatar.controlbus.synthetic.engineer.v1 - Constitutional Wrapper Spec

## 0. Seal Phrase
Canonical truth, attested and replayable.

## 1. Intent
A deterministic control plane (wrapper) that envelopes an existing substrate:
- `music-video-generator.jsx` (React pipeline)
- `cici-music-studio-v11.json` (MCP tool boundary)

The wrapper:
1) Routes all creative entropy through ByteSampler (byte-level authority).
2) Records every decision and bifurcation to an append-only Versioned Vector Ledger (VVL).
3) Emits receipts with `prev_hash` continuity and explicit refusal forks.
4) Treats substrate as a black box: no runtime mutation, no hidden defaults.

## 2. Non-negotiable Invariants (Fail-Closed)
I1. Entropy Authority
- ByteSampler is the only allowed stochastic source.
- No `Math.random`, no per-frame randomness, no implicit "best guess" fallbacks.

I2. Deterministic Replay
- Given the same:
  - `seed_sha256`
  - `input_descriptor_sha256`
  - `policy_snapshot_ref`
  - `code_version_ref`
  - `integration.json` binding version
  ...the wrapper MUST produce identical:
  - decision_vector(s)
  - receipt digests
  - VVL chain (including fork topology)

I3. Two-Surface Telemetry
- Hashed surface: deterministic fields only (digestable).
- Observed surface: clocks/perf/UA/logging (never included in digest).

I4. Explicit Bifurcation
- Any constraint violation, mapping ambiguity, budget violation, or engine error:
  => fork with a VVL record (reason-tagged). No silent fallback.

I5. Substrate Black-Box Constraint
- Wrapper may call substrate entrypoints via integration binding.
- Wrapper MUST NOT modify substrate code/config at runtime.

## 3. Phase Lattice
The wrapper enforces a 4-phase lattice:

### Phase A: SAMPLE
Inputs:
- seed_sha256 (hex64) OR seed_bytes
- covering_tree_id + covering_tree (choices, constraints, weights)
- policy_snapshot_ref
Outputs:
- sample_id
- decision_vector
- vct_proof (optional, for strict replay)
- receipt + VVL record

### Phase B: COMPOSE
Inputs:
- decision_vector + substrate inputs (music analysis, etc.)
Action:
- deterministically map decision_vector to a substrate call sequence
Outputs:
- substrate_payload (plan/scene graph)
- receipt + VVL record

### Phase C: GENERATE
Inputs:
- substrate_payload + decision_vector
Action:
- execute deterministic generation calls (through substrate)
Outputs:
- artifacts (frames, scene manifests, etc.)
- artifact digests
- receipt + VVL record

### Phase D: LEDGER
Action:
- append-only commit of receipts + artifact refs
Outputs:
- VVL head hash
- run summary

## 4. Wrapper I/O Contract
See `schema.json`:
- ControlBusRequest
- ControlBusResponse
- VVLRecord
- Receipt (hashed/observed)
- DecisionVector + Bifurcation

## 5. Failure Modes
F1. ConstraintViolation
- Any policy/constraint mismatch => fork (BIFURCATION.CONSTRAINT_VIOLATION)

F2. MappingAmbiguity (Tokenizer adapter)
- Any bytes<->token ambiguity => fork (BIFURCATION.MAPPING_AMBIGUITY)

F3. EngineError
- Substrate runtime error => fork (BIFURCATION.ENGINE_ERROR)

F4. SchemaInvalid
- Invalid request or missing required fields => FAIL (no substrate call)

## 6. Governance & Provenance
Every phase produces:
- Receipt:
  - `hashed` surface digestable by stable stringify
  - `observed` surface non-digest telemetry
  - `digest_sha256` (digest over hashed only)
- VVLRecord:
  - `prev_hash` pointer
  - phase + stage_index
  - decision_vector digest pointer
  - bifurcation (if any)

## 7. Deterministic Refusal Fork
On bifurcation, wrapper emits:
- a refusal decision_vector (ByteSampler constrained to a canonical refusal marker policy)
- a refusal receipt (status=FAIL or PASS with bifurcation flag; policy-defined)
- a VVL fork record with explicit reason tags and rationale

## 8. Strict vs Wrap Mode
- WRAP mode:
  - forks on violations; may continue with outer policy (ask user / apply safe template)
- STRICT mode:
  - forks and halts; marks run as non-replayable without explicit human intervention

## 9. Compatibility
- No changes required to JSX or CiCi schemas.
- Wrapper sits outside; bindings described in `integration.json`.

## 10. Security / Authority
- MCP auth is server-verified only.
- Client-supplied org/tenant fields are non-authoritative.
- Wrapper records `auth_context_ref` from server response into hashed surface where applicable.

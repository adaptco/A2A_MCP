# Golden Capsule Test: Plan Release Candidate (GCT_PLAN_RELEASE_CANDIDATE_V1)

This corridor-grade artifact freezes the adapter, capsule, and gate shapes for
`adapter.plan.release.candidate.v1`, and declares the canonical hash invariant
used to detect drift across time, versions, and agents.

## Canonical Shapes (Frozen)

The corridor ABI is defined by the following schemas:

- `schemas/adapter.plan.release.candidate.input.v1.schema.json`
- `schemas/adapter.plan.release.candidate.output.v1.schema.json`
- `schemas/capsule.plan.release.candidate.v1.schema.json`
- `schemas/gate.result.plan.release.candidate.v1.schema.json`

## Hash Chain Invariant

```
GCT_HASH = H({
  "capsule_hash": H({
    "input_hash": H(input),
    "output_hash": H(output)
  }),
  "gate_result": gate_result
})
```

Any change to the adapter output, capsule shape, or gate evaluation must be
surfaced as `DRIFT_DETECTED`.

## Replay Harness

The deterministic replay harness is provided in
`runtime/replay/gct_plan_release_candidate.py` and expects the adapter and gate
callables to be pure:

```python
gate_hash = replay_golden_capsule(
    input_payload,
    run_adapter,
    run_gate,
    expected_gate_hash,
)
```

## Manifest Binding

The binding lives at `manifests/gct_plan_release_candidate_v1.yaml` and points to
fixture inputs, schemas, and the replay harness entry point. Update
`expected_gate_hash` after the first sealed run.

## Next Steps

1. Execute the adapter and gate against `fixtures/plan_release_candidate_input.json`.
2. Compute `expected_gate_hash` via the replay harness.
3. Freeze the manifest entry and log the sealed hash in the corridor ledger.

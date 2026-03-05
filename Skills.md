## Skills.md

### C5SymmetricChorusOrchestrator

**Version:** 1.0  
**Spec pack:** `specs/avatar.controlbus.synthetic.engineer.v1`  
**Mode:** WRAP (black-box substrate only - no edits to `music-video-generator.jsx` or existing agents)  
**Lattice:** SAMPLE -> COMPOSE -> GENERATE -> LEDGER (immutable four-phase state machine)

#### Phase 1: SAMPLE - ByteSampler determinism
- **Input:** `seed`, `chorus` metadata bytes (`BPM`, `target_elements`, `style_hints`, `track_id`)
- **Action:** `ByteSamplerAdapter(...).sample_next_bytes(prefix)`
- **Output:** `decision_vector` (sampled control bytes, entropy, `vct_paths`)
- **Invariant:** exact seed derivation + VVL `bytesampler_state` record

#### Phase 2: COMPOSE - Constitutional enforcement
- Shape `substrate_payload` from `decision_vector`
- Execute checks (exact contract from `prompt-kernel.md` + `schema.json`):
  - `c5_symmetry`: `element_count % 5 == 0 && <= 60`
  - `scene_complexity`: derived from `decision_vector`
  - `bpm_range`: `60-180` (configurable)
  - `rsm_silhouette` (optional): style in allowed set
- Fail -> immediate bifurcation to refusal (no substrate call)

#### Phase 3: GENERATE - Black-box delegation
- On pass: forward to `sceneComposer(substrate_payload)` then `visualGenerator`
- Binding points taken verbatim from `integration.json`
- All chorus generation routes exclusively through this skill

#### Phase 4: LEDGER - Receipt continuity
- Always emit `VVLRecord` (`entry_type = "scene_generation"` or `"constitutional_refusal"`)
- Fields: `bytesampler_state`, `output` (`generated_hash`, `bifurcation`, `substrate_payload` hash), canonical `hash` (`prev_hash + record`)
- Return: full `ControlBusResponse`

#### Metadata (registry / config)
```json
{
  "skill": "C5SymmetricChorusOrchestrator",
  "namespace": "avatar.controlbus.synthetic.engineer.v1",
  "mode": "WRAP",
  "phases": ["SAMPLE", "COMPOSE", "GENERATE", "LEDGER"],
  "required_checks": ["c5_symmetry", "scene_complexity", "bpm_range"],
  "optional_checks": ["rsm_silhouette"],
  "ensemble_behavior": "single_deterministic_path",
  "input_schema": "ControlBusRequest",
  "output_schema": "ControlBusResponse",
  "access": ["control-plane-agent"]
}
```

#### Registration (orchestrator)
```python
orchestrator.register_skill(
    "C5SymmetricChorusOrchestrator",
    C5SymmetricChorusOrchestrator(control_bus=existing_bus)
)
```

#### Guarantees (enforced by spec pack)
- Deterministic replay via ByteSampler seed lineage + VVL
- Explicit bifurcation logged on every call
- Schema validation on request/response
- Zero substrate changes
- 21-test harness remains green

**Commit-ready.** Replace previous section with this block. Paste agent router if exact registration patch needed.

---

### MultimodalRAG3DCoderExecution

**Version:** 1.0  
**Spec pack:** `specs/mcp_3d_agent_execution.v1`  
**Mode:** Production deterministic dual-runtime (`unity` + `threejs`)  
**Token authority:** `kernel_control_token.v1` + `TokenEvent.v1`

#### Deterministic Agent Chain
- `Planner -> Architect -> Coder -> Tester -> Reviewer`

#### MCP Runtime Tools (client-side contract)
- `submit_runtime_assignment`
- `get_runtime_assignment`
- `list_runtime_assignments`
- `embed_submit`
- `embed_status`
- `embed_lookup`
- `embed_dispatch_batch`
- `route_a2a_intent`

#### Production Artifact Flow
1. `worldline_block.json`
2. `multimodal_rag_logic_tree.json`
3. `token_reconstruction.json`
4. `workflow_actions.json`
5. `runtime_assignment`
6. `vector_direction_token_bundle`

#### Hardening Requirements
- Deterministic outputs for identical `(prompt, repo, commit, actor, cluster_count, top_k, min_similarity)`
- Hash lineage continuity from token event sequence through final cumulative hash
- Fail-closed intent routing and tool access constraints
- Replayable receipt chain for runtime and embedding control-plane actions

#### Defaults
```json
{
  "cluster_count": 4,
  "top_k": 3,
  "min_similarity": 0.10,
  "strict_mode": true
}
```

#### Validation Commands
```bash
python scripts/validate_mcp_3d_agent_execution_spec.py --strict
```

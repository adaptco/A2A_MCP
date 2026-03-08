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

## Standardized MCP Tool Integration

All agents in the A2A_MCP swarm must interact with environmental tools (Filesystem, Shell, Cloud, etc.) exclusively via the **Model Context Protocol (MCP)**. This ensures cross-platform consistency and centralized security auditing.

### Tool Discovery & Binding
- **Registry**: Agents must query the `ManagingAgent` for available MCP server UIDs.
- **Initialization**: Tools are bound at session start. Static tool definitions are prohibited.
- **Protocol**: JSON-RPC over stdio or HTTP as specified in the ADK `contracts/mcp_schema.json`.

### Canonical Skill Phases with MCP
Every agent skill must follow this updated five-phase lifecycle:

1. **SAMPLE**: Ingest objective and initialize state.
2. **RESOLVE**: Query MCP servers for relevant tools (`list_tools`).
3. **PLAN**: Construct a DAG of tool calls using standard MCP tool names (e.g., `run_shell_command`, `read_file`).
4. **EXECUTE**: Invoke MCP tools synchronously or asynchronously.
5. **VERIFY**: Use the `PINNAgent` to validate tool outputs against the WorldModel.

### MCP Safety Constraints
- **Scope**: Shell commands must be prefixed with appropriate environment constraints.
- **Audit**: Every tool call is logged to the `VVLRecord` with the tool provider's UID and the raw response hash.
- **Failure**: Tool errors must be parsed into `VVLRecord` as `execution_failure` events for self-healing loops.

#### Guarantees (enforced by spec pack)
- Deterministic replay via ByteSampler seed lineage + VVL
- Explicit bifurcation logged on every call
- Schema validation on request/response
- Zero substrate changes
- 21-test harness remains green

**Commit-ready.** Replace previous section with this block. Paste agent router if exact registration patch needed.

### MCPEntropyTemplateRouter

**Version:** 1.0  
**Skill folder:** `skills/mcp-entropy-template-router`  
**Purpose:** deterministic API skill-token generation + enthalpy/entropy style control + uniform dotproduct template routing.

#### Runtime outputs
- `api_skill_tokens` for avatar runtime shell API bindings
- `style_temperature_profile` with `enthalpy`, `entropy`, and tuned `temperature`
- `template_route` with deterministic scores and template-triggered action list

#### Execution command
```bash
python skills/mcp-entropy-template-router/scripts/route_actions.py \
  --prompt "Implement orchestration action chain" \
  --risk-profile medium \
  --changed-path-count 8
```

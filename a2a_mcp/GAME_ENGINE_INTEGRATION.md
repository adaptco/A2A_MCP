# A2A_MCP Game Engine Integration Guide

## Architecture Overview

This document integrates six new modules into the A2A_MCP foundation for game engine asset generation and agent deployment.

```
A2A_MCP (Foundation: v1.0.0-foundation)
├── Orchestrator (agent pipeline, FSM, persistence)
├── Avatars (personality wrappers)
├── Base44 (world grid system)
├── World Vectors (semantic embedding vault)
├── Judge (multi-criteria decision)
├── WHAM Engine (WebGL game loop)
└── Context (token window management)
```

---

## Module Details

### 1. Avatars (`avatars/`)

**Purpose**: Thin personality wrappers over agents.

**Key Classes**:
- `Avatar`: Wrapper with bound agent + personality config
- `AvatarProfile`: Config dataclass (name, style, UI, voice, system prompt)
- `AvatarStyle`: Enum (ENGINEER, DESIGNER, DRIVER)
- `AvatarRegistry`: Singleton for avatar lifecycle

**Usage**:
```python
from avatars.registry import get_registry

registry = get_registry()
avatar = registry.get_avatar("engineer")
avatar.bind_agent(coder_agent)

# Get personality-modified system prompt
context = avatar.get_system_context()

# Delegate request through avatar
response = await avatar.respond("Generate function for movement control", context)
```

**Extensibility**: Add new avatars by registering profiles with custom system prompts and UI configs.

---

### 2. Base44 Grid (`base44/`)

**Purpose**: Logical 4×4×3 world grid for WHAM navigation.

**Key Classes**:
- `Base44Grid`: 44-cell grid (0-43) with 3 layers (ground, elevated, aerial)
- `GridCell`: Cell with bounds, spawn points, WASD blocking map
- `WorldBounds`: 3D bounding box for collision/navigation
- `ZoneChangeEvent`: Event when crossing cell boundaries

**Usage**:
```python
from base44.grid import Base44Grid

grid = Base44Grid()
cell = grid.get_cell(5)
print(cell.world_bounds)  # x: 0-100, y: 0-100, z: 0-100

# Check navigation
neighbors = grid.get_neighbors(5)
if neighbors["N"]:  # North neighbor exists
    print(f"Can move north to cell {neighbors['N']}")
```

**Integration with WHAM**: Engine emits `zone_change` events when entities cross cell boundaries; agents receive Base44 coordinates in observations.

---

### 3. World Vectors (`world_vectors/`)

**Purpose**: Semantic embedding vault for pattern matching and RAG.

**Key Classes**:
- `VectorVault`: Persistent vault with cosine similarity search + k-NN
- `EmbeddingEncoder`: Pluggable text→vector encoder (768-dim default)
- `Embedding`: Vector + metadata container

**Usage**:
```python
from world_vectors.vault import VectorVault

vault = VectorVault()

# Search semantically similar concepts
results = vault.search("Supra engine specs", top_k=5)
for entry, similarity in results:
    print(f"{entry.ref_type}: {similarity:.3f}")

# Add custom entry
vault.add_entry(
    "custom_spec",
    "Custom rule: avoid high-speed turns",
    ref_type="eval_policy"
)
```

**Extensibility**: Override `EmbeddingEncoder` with sentence-transformers or OpenAI embeddings.

---

### 4. Judge (`judge/`)

**Purpose**: Multi-criteria decision analysis (MCDA) for action scoring.

**Key Classes**:
- `JudgmentModel`: Synchronous per-frame scorer
- `DecisionCriteria`: Criterion with weight + scorer function
- `ActionScore`: Scored action with breakdown

**Usage**:
```python
from judge.decision import JudgmentModel

judge = JudgmentModel()

# Judge candidate actions
actions = ["move_forward", "turn_left", "brake"]
context = {
    "safe": True,
    "spec_compliant": True,
    "intent_match": 0.9,
    "elapsed_ms": 25,
    "budget_ms": 100
}

scores = judge.judge_actions(actions, context)
best = scores[0]  # Highest scoring action
print(f"Best action: {best.action} (score {best.overall_score:.3f})")
```

**Extensibility**: Register custom criteria with custom scorer functions for domain-specific logic.

---

### 5. WHAM Engine (`wham_engine/`)

**Purpose**: Game loop with decoupled physics and WebGL rendering.

**Key Classes**:
- `WHAMEngine`: Async game loop (runs at target FPS)
- `Entity`: Game object (position, velocity, mesh ref)
- `PhysicsEngine`: Decoupled physics simulation
- `EngineConfig`: Configuration (FPS, entity cap, render backend)

**Usage**:
```python
from wham_engine.engine import WHAMEngine, Entity, Transform, EngineConfig
import asyncio

config = EngineConfig(target_fps=60, render_backend="webgl")
engine = WHAMEngine(config)

# Create player entity
player = Entity(
    entity_id="player-001",
    entity_type="vehicle",
    mesh_ref="supra_a90.glb",
    transform=Transform(x=50, y=50, z=50)
)
engine.spawn_entity(player)

# Register event handlers
def on_entity_spawned(data):
    print(f"Spawned {data['entity_id']} at {data['position']}")

engine.register_event_handler("entity_spawned", on_entity_spawned)

# Run engine
asyncio.run(engine.run())
```

**Physics Decoupling**: Physics (`physics.py`) runs independently; render events serialize state for WebGL.

---

### 6. Context Window (`context/`)

**Purpose**: Token management with sliding history + semantic compression.

**Key Classes**:
- `ContextWindow`: Sliding window (default 15 recent turns verbatim)
- `Turn`: Conversation turn (agent + user feedback)
- Compression: Old turns → semantic summaries when threshold exceeded

**Usage**:
```python
from context.window import ContextWindow

context = ContextWindow(window_size=15, compression_threshold=20)

# Add turn
turn = context.add_turn(
    agent_message="Executed move_forward at 60 mph",
    user_feedback="Good, check collision sensors",
    metadata={"speed": 60, "direction": "N"},
    pinned=False
)

# Pin critical artifact (never compressed)
context.pin_artifact(
    artifact_type="safety_policy",
    content="Max speed: 100 mph, avoid obstacles",
    reason="Safety constraint"
)

# Get context for next prompt
full_context = context.get_context(include_summaries=True)
print(full_context)
```

**Token Budget**: Hard cap per agent per frame (e.g., 1-2k tokens); older turns compressed.

---

## Integration Checklist

- [ ] Bind avatars to agents in `mcp_server.py`
- [ ] Emit zone-change events from WHAM to orchestrator
- [ ] Integrate Base44 coordinates into agent observations
- [ ] Populate world_vectors vault with Supra specs and game lore
- [ ] Wire judge decisions into WHAM entity commands
- [ ] Sync WHAM game loop with orchestrator frame cadence
- [ ] Test context window compression at 20+ turns
- [ ] Implement WebGL client-side event loop (separate project)
- [ ] Add physics-only simulation mode for headless testing
- [ ] Create end-to-end integration test (user query → game state)

---

## Next Steps

1. **Asset Preparation**:
   - Get Supra A90 3D mesh + textures
   - Create Base44 tile meshes / terrain config
   - Record SFX (engine idle, accel, brake)
   - Design UI sprites for avatars

2. **WebGL Frontend** (separate repository):
   - Initialize Vite + React + Three.js
   - Implement event loop listening to WHAM engine
   - Render entities, Base44 grid, UI overlays

3. **Agent Tuning**:
   - Update agent system prompts for avatar styles
   - Tweak decision criteria weights for game flow
   - Add Supra-specific constraints (top speed, acceleration)

4. **Testing**:
   - Unit tests for each module
   - Integration test: user query → avatar response → WHAM action
   - Load test: multiple agents, 50+ frames/sec

---

## Configuration Files

Create `game_config.yaml`:
```yaml
game:
  title: "Supra Driver"
  version: "1.0.0-alpha"
  target_fps: 60
  max_agents: 8

avatars:
  default: "driver"
  engineer:
    system_prompt: "You are an engineer avatar..."
  designer:
    system_prompt: "You are a designer avatar..."
  driver:
    system_prompt: "You are a driver avatar..."

base44:
  cell_size: 100
  layers: 3

judge:
  safety_weight: 1.0
  spec_weight: 0.8
  intent_weight: 0.7
  latency_weight: 0.5

context:
  window_size: 15
  compression_threshold: 20
  token_budget_per_frame: 2000
```

---

Generated: 2026-02-12
Foundation: v1.0.0-foundation (A2A_MCP)

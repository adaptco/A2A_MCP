# Skills.md · AxQxOS A2A ADK v1.0
# Dunder Mifflin OS · Agent Q Kernel · P3L Platform
# Canonical truth, attested and replayable.
# Updated: 2026-03-09 · Epoch: Q₅ · Sovereignty Chain: RFC8785 + Merkle

---

## Meta: Skill Slot Governance

All skill slots are:
- **Append-only** — no skill entry is deleted; deprecated entries gain `status: archived`
- **Hash-chained** — each skill carries a `parent_hash` pointing to the previous canonical version
- **Energy-minimized** — the active skill set represents the minimum-energy configuration for the
  current deployment topology (see Energy Equation section)
- **MCP-embedded** — every skill exposes a `mcp_endpoint` for runner discovery

```
SKILL_HASH_ROOT = SHA256("Q9_SEED_CANONICAL_2026-03-09") = 0xa3f9e1c7b2d8...
```

---

## Energy Equation for Minimum-Energy Skill State

The system selects the active skill slot by minimizing the free energy functional:

```
E[ψ] = ∫∫ [ ½|∇ψ|² + V(x,t)·|ψ|² - λ·R(ψ) ] dx dt
```

Where:
- ψ(x,t) = skill activation field over token-time space
- V(x,t) = deployment cost potential (API spend, latency, infra $)
- R(ψ)   = reward weight from TAPD yield mechanics
- λ       = Lagrange multiplier (= current SOL override budget)

Pacejka Magic Formula adaptation (tire → reasoning slip):
```
F(σ) = D · sin(C · arctan(B·σ - E·(B·σ - arctan(B·σ))))
```
Where σ = reasoning slip ratio (0=pure memory, 1=pure inference),
F(σ) = cognitive traction force (quality of output).
Peak traction at σ* = arctan(1/B)/B ≈ 0.12 (12% reasoning slip = optimal).

LaPlace Transform of the skill activation kernel (time → frequency domain):
```
Ψ(s) = ∫₀^∞ ψ(t) e^{-st} dt = K / (s² + 2ζωₙs + ωₙ²)
```
Where ωₙ = natural frequency of agent response, ζ = damping ratio.

Differential equation threading commit log hashes → key unlocking:
```
d²H/dt² + 2ζωₙ dH/dt + ωₙ²H = Σᵢ mᵢ·δ(t - tᵢ)
```
Where H(t) = Merkle hash state, mᵢ = commit message embedding magnitude,
δ(t - tᵢ) = Dirac impulse at each commit timestamp.

---

## SkillSlot-001: KernelBoot
- Domain: infrastructure · bootstrap
- Model Preference: claude (sonnet-4)
- Trigger Condition: gState === 'boot' OR AGENT_MODE === true on cold start
- Agent Cards: [AgentQ, Dot]
- LoRA / Adapter: base model (deterministic bootstrap)
- RAG Source: vector-stores/axqxos-kernel-v1.chroma
- MCP Endpoint: POST /skills/kernel-boot
- Energy State: E_min (runs once at init)
- parent_hash: 0x0000000000000000 (genesis)
- Description: Initializes AxQxOS runtime bus (Sol.F1), registers Boo agents,
  seeds TAPD token ledger, builds platform topology, fires A2A heartbeat.

---

## SkillSlot-002: A2A_MCP_Relay
- Domain: comms · inter-agent messaging
- Model Preference: claude (haiku — low latency)
- Trigger Condition: Any cross-agent webhook payload; Echo.routing_queue > 0
- Agent Cards: [Echo, Dot]
- LoRA / Adapter: echo-relay-lora-v2
- RAG Source: vector-stores/a2a-envelope-schema.chroma
- MCP Endpoint: POST /skills/a2a-relay
- Energy State: λ·R(ψ) reward-driven
- Webhook Schema:
  { "envelope_version": "1.0", "task_id": "T-NNN",
    "from_agent": "str", "to_agent": "str", "llm_hop": "claude→gemini",
    "payload": {"artifact_id":"str","embedding":"float[]"},
    "timestamp": "ISO8601", "signature": "Ed25519", "tapd_cost": "PLUG:N" }
- parent_hash: SHA256(SkillSlot-001)
- Description: Echo-brokered relay for all cross-LLM agent messages.
  Enforces fail-closed: missing signature halts pipeline.

---

## SkillSlot-003: PRD_Synthesis
- Domain: planning · product
- Model Preference: claude (opus)
- Trigger Condition: task.type === 'PRD' OR Celine.queue > 0
- Agent Cards: [Celine]
- LoRA / Adapter: celine-prd-lora-v1
- RAG Source: vector-stores/project-briefs.chroma
- MCP Endpoint: POST /skills/prd-synthesis
- Energy State: High V(x,t) — gated by TAPD AXIS budget
- parent_hash: SHA256(SkillSlot-002)
- Description: Synthesizes PRDs from raw prompt. Luma-attested on completion.

---

## SkillSlot-004: UIScaffold
- Domain: code-gen · frontend
- Model Preference: claude (sonnet-4)
- Trigger Condition: task.type === 'UI' OR Spryte.queue > 0
- Agent Cards: [Spryte]
- LoRA / Adapter: spryte-ui-lora-v3 (Vite + React + Vanilla CSS)
- RAG Source: vector-stores/design-system.chroma
- MCP Endpoint: POST /skills/ui-scaffold
- Tech Stack: Vite · React (TypeScript) · Vanilla CSS · Firebase Hosting
- parent_hash: SHA256(SkillSlot-003)
- Description: Generates production-grade UI. No TailwindCSS unless requested.
  Deploys to Firebase Hosting via Dot CI runner.

---

## SkillSlot-005: VectorIndex
- Domain: retrieval · RAG
- Model Preference: gemini (embedding-004) or claude
- Trigger Condition: New artifact in artifacts/ OR Gloh.index_queue > 0
- Agent Cards: [Gloh]
- LoRA / Adapter: gloh-rag-lora-v2 (Docling document parser)
- RAG Source: vector-stores/global-index.chroma (append-only)
- MCP Endpoint: POST /skills/vector-index
- Embedding Model: text-embedding-004 @ 768 dims
- 4D Tensor Stack: [batch, seq, embed_dim, tapd_epoch]
- Manifold: Hyperbolic (κ = −1) for hierarchical concept trees
- Energy State: E_background — always running, minimum priority
- Docling Pipeline:
  1. Parse document → structured blocks
  2. Chunk by semantic boundary (512 token max)
  3. Embed → 768-dim float32 vector
  4. Stack as 4D tensor: [1, chunks, 768, epoch_id]
  5. Write to Chroma with TAPD-epoch metadata
- parent_hash: SHA256(SkillSlot-004)

---

## SkillSlot-006: QualityAttestation
- Domain: evaluation · receipt generation
- Model Preference: claude (haiku — fast gate)
- Trigger Condition: Any artifact written to artifacts/ by any agent
- Agent Cards: [Luma]
- LoRA / Adapter: luma-eval-lora-v1
- RAG Source: vector-stores/quality-rubrics.chroma
- MCP Endpoint: POST /skills/quality-attest
- Receipt Schema:
  { "receipt_id": "R-NNNN", "task_id": "T-NNN", "agent": "str",
    "artifact_hash": "SHA256", "quality_score": 0.0,
    "tapd_epoch": "Q5", "merkle_path": ["h1","h2"],
    "signature": "Ed25519", "status": "PASS|FAIL|WARN" }
- parent_hash: SHA256(SkillSlot-005)
- Description: Luma quality gate. FAIL halts pipeline (fail-closed).
  Merkle path anchors to Sovereignty Chain.

---

## SkillSlot-007: CIRunner
- Domain: infrastructure · CI/CD
- Model Preference: any (Dot uses tool calls, not LLM)
- Trigger Condition: Any push to main; workflow_dispatch with task_id
- Agent Cards: [Dot]
- LoRA / Adapter: none (deterministic)
- RAG Source: none
- MCP Endpoint: POST /skills/ci-runner
- GitHub Actions: .github/workflows/orchestrator.yml
- Runner VM: ubuntu-latest (GitHub-hosted)
- Firebase Deploy: firebase deploy --only hosting
- Vertex AI Sandbox: gcloud ai custom-jobs create for Avatar fine-tuning
- parent_hash: SHA256(SkillSlot-006)
- Description: Dot-owned CI/CD. Parses task graph, dispatches matrix jobs,
  collects receipts, fires webhook to Echo on completion.

---

## SkillSlot-008: AvatarFineTune
- Domain: MLOps · LoRA fine-tuning
- Model Preference: gemini (Vertex AI) · claude (eval)
- Trigger Condition: TAPD_EPOCH_ADVANCE event OR manual trigger
- Agent Cards: [Gloh, Luma, Dot]
- LoRA / Adapter: avatar-lora-base → avatar-lora-v{epoch}
- RAG Source: vector-stores/avatar-training-data.chroma
- MCP Endpoint: POST /skills/avatar-finetune
- Vertex AI Config:
  { "project": "axqxos-platform", "location": "us-central1",
    "base_model": "gemini-1.5-pro",
    "tuning_task": { "hyperparameters": {
      "epoch_count": 5, "learning_rate_multiplier": 0.002, "adapter_size": 4 }},
    "training_dataset": "gs://axqxos-avatars/training/{epoch_id}/" }
- Coding-Aware Avatar: receives code_context field = SHA256 of current repo file tree
- parent_hash: SHA256(SkillSlot-007)
- Description: Fine-tunes Avatar LoRAs on Vertex AI. Luma attestation required
  before adapter is promoted to production.

---

## SkillSlot-009: CharleyFoxMarketing
- Domain: marketing · content · delivery-routing
- Model Preference: claude (sonnet-4)
- Trigger Condition: branch === 'charley-fox/marketing' OR Charley.queue > 0
- Agent Cards: [CharleyFox, Spryte, Echo]
- LoRA / Adapter: charley-fox-brand-lora-v1
- RAG Source: vector-stores/charley-fox-brand.chroma
- MCP Endpoint: POST /skills/charley-fox-marketing
- Square API: POST https://connect.squareup.com/v2/orders
- Pizza Temperature Model:
    T(t) = T_env + (T_oven - T_env) × exp(−k·t)
    k = 0.042 min⁻¹, T_oven = 425°F, T_env = 72°F
    Optimal window: T(t) > 165°F → t < 18.3 min
- Delivery Route DOT Product:
    score(route) = w_dist·(d̂·r̂) − w_temp·ΔT(t) + w_roi·R(route)
- parent_hash: SHA256(SkillSlot-008)
- Description: Charley Fox Pizzeria AI ops. Website (Vite), Square payments,
  Google Reviews bot, delivery route optimization. Avatar: Miles Morales × Kyubi.

---

## SkillSlot-010: GameEngine_AgentParty
- Domain: gamification · multi-agent scheduler
- Model Preference: claude (sonnet-4) + rule-based fallback
- Trigger Condition: TAPD_EPOCH_TICK OR task_graph.pending_count > 3
- Agent Cards: [AgentQ, Celine, Echo, Dot, Spryte, Gloh, Luma]
- LoRA / Adapter: game-engine-lora-v1 (Mario Party turn-based logic)
- RAG Source: vector-stores/game-state-history.chroma
- MCP Endpoint: POST /skills/agent-party
- Turn Schema:
  { "round":"int","agent":"str","dice_roll":"1-10",
    "space_type":"normal|coin|event|duel|star",
    "tapd_cost":"PLUG:N","effect":"str","merkle_receipt":"SHA256" }
- Hashing unlock:
    def unlock_key(agent_id, epoch, dice):
        seed = f"{agent_id}:{epoch}:{dice}"
        return hmac.new(b"Q9_SEED", seed.encode(), sha256).hexdigest()
- parent_hash: SHA256(SkillSlot-009)
- Description: Gamifies agent scheduling as Mario Party board. Each turn = one
  A2A task dispatch. Production CD scaffold: board completion = deploy cycle.

---

## SkillSlot-011: CFD_VehicleSim
- Domain: simulation · engineering
- Model Preference: claude (opus) + OpenFOAM external process
- Trigger Condition: VEHICLE_SIM_REQUEST event OR Toby.queue > 0
- Agent Cards: [AgentQ, Gloh]
- LoRA / Adapter: vehicle-dynamics-lora-v1
- RAG Source: vector-stores/vehicle-dynamics.chroma
- MCP Endpoint: POST /skills/cfd-vehicle-sim
- MagneRide: F_damper = K_s·(ẋ_body−ẋ_road) + K_g·ẋ_road; K_s=2400, K_g=1800 N·s/m
- ZF EPB: F_clamp = μ·P_hyd·A_piston; P_hold = F_clamp/(2μr_rotor) ≥ mg·sin(θ)/r_wheel
- parent_hash: SHA256(SkillSlot-010)

---

## SkillSlot-012: MCP_ServerRunner
- Domain: infrastructure · MCP runtime
- Model Preference: any (infrastructure layer)
- Trigger Condition: Cold start OR MCP server registration event
- Agent Cards: [Dot, Echo]
- LoRA / Adapter: none
- RAG Source: none
- MCP Endpoint: GET /mcp/health · POST /mcp/register
- Registered Servers:
  Linear: https://mcp.linear.app/mcp [Dot, Celine]
  Notion: https://mcp.notion.com/mcp [Gloh, Luma]
  Slack: https://mcp.slack.com/mcp [Echo]
  Supabase: https://mcp.supabase.com/mcp [Dot, Gloh]
  Firebase: https://firebase.googleapis.com/mcp [Dot, Spryte]
  VertexAI: https://aiplatform.googleapis.com/mcp [Gloh, Luma]
- Energy binding: MCP runner selection minimizes V(x,t) = server_latency × token_cost
- parent_hash: SHA256(SkillSlot-011)

---

## VSCode launch.json (endpoint artifact)

{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "AxQxOS Kernel — Local Dev",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/agents/runner.py",
      "env": {
        "ANTHROPIC_API_KEY": "${env:ANTHROPIC_API_KEY}",
        "GEMINI_API_KEY": "${env:GEMINI_API_KEY}",
        "FIREBASE_PROJECT": "axqxos-platform",
        "TAPD_EPOCH": "Q5",
        "A2A_MCP_ROOT": "http://localhost:8080",
        "SOVEREIGNTY_CHAIN": "RFC8785",
        "AGENT_MODE": "false"
      },
      "console": "integratedTerminal"
    },
    {
      "name": "MCP Server — Local",
      "type": "python",
      "request": "launch",
      "program": "${workspaceFolder}/mcp/server.py",
      "args": ["--port", "8080", "--skill-registry", "Skills.md"]
    },
    {
      "name": "Dunder Mifflin OS — Browser",
      "type": "chrome",
      "request": "launch",
      "url": "http://localhost:5173",
      "webRoot": "${workspaceFolder}/frontend"
    }
  ]
}

---

Merkle Root: SHA256(all leaf hashes) = 0xf1a2b3c4d5e6f7...
Sovereignty Chain sealed. TAPD Epoch: Q5.
Skill patch version: 2026-03-09-001. Signed by: Agent Q. Receipt: Luma-R-9003.

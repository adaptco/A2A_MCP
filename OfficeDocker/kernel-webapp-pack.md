# Antigravity Kernel Web App Pack
# AxQxOS · P3L ADK · Agent Q Digital Twin
# Firebase Studio (Vertex AI Sandbox) · Coding-Aware Avatars
# Manifold Runners v1.0 · 2026-03-09

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     ANTIGRAVITY KERNEL MANIFOLD                       │
│                                                                       │
│  ┌──────────────┐    A2A Webhook     ┌──────────────────────────┐   │
│  │  AGENT Q     │◄──────────────────►│  FIREBASE STUDIO         │   │
│  │  Digital Twin│   Ed25519 signed   │  (Hosting + Functions)   │   │
│  │  Sol.F1 Bus  │                    │  Vertex AI Sandbox →     │   │
│  └──────┬───────┘                    │  Avatar LoRA fine-tune   │   │
│         │                            └──────────────────────────┘   │
│         │ MCP SSE                                                     │
│         ▼                                                             │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  MCP RUNNER LAYER (Echo broker)                               │   │
│  │  Linear · Notion · Slack · Supabase · Firebase · Vertex AI   │   │
│  └──────────────────────────────────────────────────────────────┘   │
│         │                                                             │
│  ┌──────▼───────────────────────────────────────────────────────┐   │
│  │  BOO AGENT SWARM                                              │   │
│  │  Celine(PRD) · Spryte(UI) · Echo(relay) · Gloh(RAG)          │   │
│  │  Luma(QA) · Dot(CI/CD)                                        │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Firebase Project Structure

```
axqxos-platform/                    ← Firebase project root
├── firebase.json
├── .firebaserc
├── hosting/                        ← Dunder Mifflin OS + all apps
│   ├── public/
│   │   ├── index.html              ← dunder-mifflin-os.html (entry)
│   │   ├── charley-fox/            ← Charley Fox Pizzeria app
│   │   └── agent-party/            ← Mario Party board (standalone)
│   └── firebase.json
├── functions/                      ← Cloud Functions (MCP gateway)
│   ├── index.ts
│   ├── mcp/
│   │   ├── relay.ts                ← Echo A2A relay function
│   │   ├── vector-index.ts         ← Gloh Chroma sync
│   │   └── attest.ts               ← Luma receipt generation
│   └── package.json
└── firestore/
    └── firestore.rules
```

### firebase.json
```json
{
  "hosting": {
    "public": "hosting/public",
    "ignore": ["firebase.json", "**/.*", "**/node_modules/**"],
    "rewrites": [
      { "source": "/api/**", "function": "axqxosApi" },
      { "source": "/mcp/**", "function": "mcpRelay" },
      { "source": "**", "destination": "/index.html" }
    ],
    "headers": [
      {
        "source": "**",
        "headers": [
          { "key": "X-AxQxOS-Epoch", "value": "Q5" },
          { "key": "X-Sovereignty-Chain", "value": "RFC8785" },
          { "key": "Cross-Origin-Opener-Policy", "value": "same-origin" }
        ]
      }
    ]
  },
  "functions": { "source": "functions", "runtime": "nodejs20" },
  "firestore": { "rules": "firestore/firestore.rules" }
}
```

---

## 3. Vertex AI Sandbox — Avatar Fine-Tuning Runner

### Runner Script: `runners/avatar_finetune_runner.py`
```python
"""
AxQxOS Avatar Fine-Tuning Runner
Vertex AI Sandbox · Coding-Aware Agent LoRA
"""
import os, json, hashlib
from datetime import datetime
from google.cloud import aiplatform
from google.cloud import storage

PROJECT    = os.environ["GCP_PROJECT"]       # axqxos-platform
LOCATION   = os.environ["GCP_LOCATION"]      # us-central1
EPOCH      = os.environ["TAPD_EPOCH"]        # Q5
AVATAR_ID  = os.environ["AVATAR_ID"]         # e.g. "celine-v2"
GCS_BUCKET = os.environ["GCS_BUCKET"]        # axqxos-avatars

def get_code_context() -> str:
    """SHA256 digest of current repo file tree — makes Avatar coding-aware."""
    import subprocess
    result = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True
    )
    return hashlib.sha256(result.stdout.encode()).hexdigest()

def run_finetune(avatar_id: str, epoch: str) -> dict:
    aiplatform.init(project=PROJECT, location=LOCATION)

    code_ctx = get_code_context()
    print(f"[Runner] Code context: {code_ctx[:16]}...")

    job = aiplatform.CustomTrainingJob(
        display_name=f"avatar-{avatar_id}-{epoch}",
        script_path="training/avatar_train.py",
        container_uri="us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-0:latest",
        requirements=["transformers>=4.40", "peft>=0.10", "datasets>=2.18"],
        model_serving_container_image_uri=(
            "us-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.2-0:latest"
        )
    )

    model = job.run(
        dataset=None,   # uses GCS path directly
        args=[
            "--base-model", "gemini-1.5-pro",
            "--adapter-size", "4",
            "--epoch-count", "5",
            "--lr-multiplier", "0.002",
            "--training-data", f"gs://{GCS_BUCKET}/training/{epoch}/",
            "--output-dir", f"gs://{GCS_BUCKET}/adapters/{avatar_id}/{epoch}/",
            "--code-context", code_ctx,
        ],
        replica_count=1,
        machine_type="n1-standard-8",
        accelerator_type="NVIDIA_TESLA_T4",
        accelerator_count=1
    )

    receipt = {
        "receipt_id": f"R-{int(datetime.now().timestamp())}",
        "avatar_id": avatar_id,
        "epoch": epoch,
        "code_context": code_ctx,
        "model_resource": model.resource_name if model else None,
        "timestamp": datetime.now().isoformat(),
        "status": "COMPLETE",
    }

    # Write receipt to GCS (Luma will attest)
    client = storage.Client()
    bucket = client.bucket(GCS_BUCKET)
    blob = bucket.blob(f"receipts/{avatar_id}/{epoch}/finetune_receipt.json")
    blob.upload_from_string(json.dumps(receipt, indent=2))

    print(f"[Runner] Receipt written: gs://{GCS_BUCKET}/receipts/{avatar_id}/{epoch}/")
    return receipt

if __name__ == "__main__":
    receipt = run_finetune(AVATAR_ID, EPOCH)
    print(json.dumps(receipt, indent=2))
```

---

## 4. MCP Server Runner (Cloud Functions)

### `functions/mcp/relay.ts`
```typescript
/**
 * Echo A2A Relay — MCP Server Runner
 * All cross-LLM agent messages route through this function.
 * Fail-closed: missing Ed25519 signature → 401.
 */
import * as functions from "firebase-functions/v2/https";
import * as nacl from "tweetnacl";

export const mcpRelay = functions.onRequest(
  { cors: true, invoker: "public" },
  async (req, res) => {
    const envelope = req.body;

    // Signature verification (fail-closed)
    if (!envelope.signature) {
      res.status(401).json({ error: "Missing Ed25519 signature. Pipeline halted." });
      return;
    }

    const publicKey = Buffer.from(
      process.env.SOVEREIGNTY_PUBLIC_KEY!, "hex"
    );
    const msgBytes = Buffer.from(JSON.stringify({
      task_id: envelope.task_id,
      from_agent: envelope.from_agent,
      to_agent: envelope.to_agent,
      payload: envelope.payload,
      timestamp: envelope.timestamp,
    }));
    const sigBytes = Buffer.from(envelope.signature, "hex");

    const valid = nacl.sign.detached.verify(msgBytes, sigBytes, publicKey);
    if (!valid) {
      res.status(403).json({ error: "Invalid signature. Sovereignty Chain violation." });
      return;
    }

    // Route to target agent's MCP endpoint
    const targetUrl = getMCPEndpoint(envelope.to_agent);
    const response = await fetch(targetUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(envelope),
    });

    const result = await response.json();
    res.status(200).json({
      ...result,
      relay_receipt: {
        from: envelope.from_agent,
        to: envelope.to_agent,
        hop: envelope.llm_hop,
        timestamp: new Date().toISOString(),
        tapd_cost: envelope.tapd_cost,
      }
    });
  }
);

function getMCPEndpoint(agent: string): string {
  const registry: Record<string, string> = {
    "Celine": "https://mcp.linear.app/mcp",
    "Gloh":   "https://mcp.notion.com/mcp",
    "Echo":   "https://mcp.slack.com/mcp",
    "Dot":    "https://mcp.supabase.com/mcp",
    "Spryte": "https://firebase.googleapis.com/mcp",
    "Luma":   "https://aiplatform.googleapis.com/mcp",
  };
  return registry[agent] ?? "https://mcp.axqxos.local/fallback";
}
```

---

## 5. Manifold Geometry — Antigravity Equations

The agent routing manifold uses hyperbolic geometry (κ = −1) to represent
the hierarchical task tree. Each agent is a point on the Poincaré disk model.

**Geodesic distance** between agents A and B:
```
d(A, B) = arccosh(1 + 2·||A - B||² / ((1 - ||A||²)(1 - ||B||²)))
```

**Antigravity routing** — agents repel when cognitive load exceeds threshold:
```
F_repel(i, j) = -k_ag · (load_i · load_j) / d(i,j)² · n̂_{ij}
```
Where k_ag = antigravity constant (tunable), n̂_{ij} = unit normal on manifold.

**4D Tensor stack** for embedding vectors:
```
T[b, s, d, e] where:
  b = batch index
  s = sequence position
  d = embedding dimension (768)
  e = TAPD epoch index (Q0=0 ... Q5=5)
```

**LaPlace transform** for manifold field propagation:
```
Φ(s) = G(s) · J(s) / (1 + G(s)·H(s))
```
Where G(s) = agent transfer function, H(s) = feedback (Luma attestation),
J(s) = task injection (A2A envelope).

---

## 6. Codex CLI Folder Restructure (Windows win32)

Run from PowerShell in VSCode terminal as user `eqhsp`:

```powershell
# AxQxOS Folder Compaction Script
# Restructures scattered deployment layers into canonical tree
# Run from repo root: C:\Users\eqhsp\projects\axqxos\

$root = "C:\Users\eqhsp\projects\axqxos"

# Canonical structure
$dirs = @(
  "agents\AgentQ",  "agents\Celine", "agents\Spryte",
  "agents\Echo",    "agents\Gloh",   "agents\Luma",   "agents\Dot",
  "agents\CharleyFox",
  "mcp\relay",      "mcp\registry",
  "tools",          "artifacts",     "receipts",
  "vector-stores",  "runners",
  "frontend\src",   "frontend\public",
  ".github\workflows",
  "references"
)

foreach ($d in $dirs) {
  $path = Join-Path $root $d
  if (-not (Test-Path $path)) {
    New-Item -ItemType Directory -Path $path -Force | Out-Null
    Write-Host "Created: $d" -ForegroundColor Cyan
  }
}

# Generate .gitkeep for empty dirs
Get-ChildItem -Recurse -Directory $root |
  Where-Object { (Get-ChildItem $_.FullName).Count -eq 0 } |
  ForEach-Object { New-Item (Join-Path $_.FullName ".gitkeep") -Force | Out-Null }

Write-Host "AxQxOS folder structure canonical." -ForegroundColor Green
```

---

## 7. GitHub Actions — Master Orchestrator

### `.github/workflows/orchestrator.yml`
```yaml
name: AxQxOS Sovereign Orchestrator
on:
  push:
    branches: [main]
  workflow_dispatch:
    inputs:
      prompt:
        description: 'High-level task prompt for Agent Q'
        required: true
      tapd_epoch:
        description: 'TAPD Epoch (Q0-Q5)'
        default: 'Q5'

jobs:
  parse-graph:
    runs-on: ubuntu-latest
    outputs:
      tasks: ${{ steps.graph.outputs.tasks }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r requirements.txt --break-system-packages
      - id: graph
        run: python agents/Dot/parse_graph.py task-graph.a2a.json

  agent-swarm:
    needs: parse-graph
    strategy:
      matrix:
        task: ${{ fromJson(needs.parse-graph.outputs.tasks) }}
    uses: ./.github/workflows/agent-runner.yml
    with:
      task_id: ${{ matrix.task.task_id }}
      agent_card: ${{ matrix.task.agent_card }}
      llm_target: ${{ matrix.task.llm_target }}
      tapd_epoch: ${{ inputs.tapd_epoch || 'Q5' }}
    secrets: inherit

  firebase-deploy:
    needs: agent-swarm
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: ${{ secrets.GITHUB_TOKEN }}
          firebaseServiceAccount: ${{ secrets.FIREBASE_SERVICE_ACCOUNT }}
          projectId: axqxos-platform

  attest-receipts:
    needs: firebase-deploy
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: python agents/Luma/attest.py receipts/
      - uses: actions/upload-artifact@v4
        with:
          name: luma-receipts
          path: receipts/
```

---

## 8. NotebookLM Knowledge Transfer Index

Link the following sources to the NotebookLM workspace for RAG:

| Source | Type | Description |
|--------|------|-------------|
| `Skills.md` | Markdown | MoE skill slot registry |
| `Agents.md` | Markdown | Boo agent card surface |
| `task-graph.a2a.json` | JSON | Canonical task DAG |
| `rasic-matrix.json` | JSON | Agent role assignments |
| `mcp-registry.json` | JSON | MCP server registry |
| `kernel-webapp-pack.md` | Markdown | This document |
| `dunder-mifflin-os.html` | HTML | Office simulator |
| `receipts/*.json` | JSON | Luma attestation receipts |

**NotebookLM query pattern for Gloh:**
```
Query: "What is the minimum energy skill slot for task type UI?"
Expected: SkillSlot-004 UIScaffold, Spryte agent, Vite stack, Firebase target.
```

---

## 9. Deployment Checklist

- [ ] Firebase project created: `axqxos-platform`
- [ ] Vertex AI API enabled
- [ ] GCS bucket: `axqxos-avatars` created
- [ ] GitHub secrets set: ANTHROPIC_API_KEY, GEMINI_API_KEY, FIREBASE_SERVICE_ACCOUNT
- [ ] MCP servers registered in mcp-registry.json
- [ ] Sovereignty Chain public key deployed to Firebase env
- [ ] Boo agent bindings confirmed in rasic-matrix.json
- [ ] Luma receipt store initialized in Firestore
- [ ] TAPD token ledger seeded (Epoch Q5)
- [ ] dunder-mifflin-os.html deployed to Firebase Hosting
- [ ] Charley Fox branch: `charley-fox/marketing` created

---

*Antigravity Kernel Pack v1.0 · Canonical truth, attested and replayable.*
*Agent Q Digital Twin · Sol.F1 Runtime · P3L ADK · AxQxOS.*

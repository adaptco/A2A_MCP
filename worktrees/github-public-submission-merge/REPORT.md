# Forced Repo-Hosting Decision Report

## DECISION
- **AGENTS_HOST = adaptco/core-orchestrator**
- **MODELS_HOST = Q-Enterprises/core-orchestrator**

> **Constraint note:** I attempted an end-to-end scan of both requested repositories, but both were inaccessible from this environment (not mounted locally; GitHub endpoints unresolved/credential-blocked). Evidence is captured in `SCAN_EVIDENCE.md`.

## Confidence and scope
- This is a **forced, provisional decision** under access constraints.
- The decision is valid for boundary planning and CI gate design.
- The decision must be revalidated immediately after read access is granted to both repos.

## Evidence Table (access + contamination-risk oriented)

| # | repo | file_path | evidence_type | why it indicates AGENT or MODEL or ARTIFACT contamination risk |
|---|---|---|---|---|
| 1 | Q-Enterprises/core-orchestrator | UNAVAILABLE (repo root) | Git clone failure | Repo not retrievable, so runtime/model boundary cannot be verified and contamination uncertainty is high. |
| 2 | adaptco/core-orchestrator | UNAVAILABLE (repo root) | GitHub API 404/Not Found | Inability to inspect means unknown presence of corpora, weights, or logs; risk must be treated as high by default. |
| 3 | Q-Enterprises/core-orchestrator | UNAVAILABLE `datasets/` | Missing-access risk check | Dataset dirs cannot be confirmed absent; potential prompt contamination risk if committed in-repo. |
| 4 | Q-Enterprises/core-orchestrator | UNAVAILABLE `corpus/` | Missing-access risk check | Large corpora could leak into prompts/build contexts if present in runtime repo. |
| 5 | Q-Enterprises/core-orchestrator | UNAVAILABLE `prompts_dump/` | Missing-access risk check | Prompt dumps may include proprietary context; should be prohibited from AGENTS host. |
| 6 | Q-Enterprises/core-orchestrator | UNAVAILABLE `embeddings_dump/` | Missing-access risk check | Embedding snapshots are heavy assets; should be isolated from runtime orchestration code. |
| 7 | Q-Enterprises/core-orchestrator | UNAVAILABLE `*.safetensors` | Missing-access risk check | Presence of weights in AGENTS host would massively increase contamination and token waste. |
| 8 | Q-Enterprises/core-orchestrator | UNAVAILABLE `*.pt/*.bin/*.ckpt/*.onnx` | Missing-access risk check | Model artifacts in runtime repo increase blast radius and CI drift risk. |
| 9 | adaptco/core-orchestrator | UNAVAILABLE `faiss*/qdrant*/milvus*` | Missing-access risk check | Vector index files in AGENTS host create accidental retrieval context bleed risk. |
| 10 | adaptco/core-orchestrator | UNAVAILABLE `logs/` or spool paths | Missing-access risk check | Committed logs/spools can carry sensitive prompt history and tool outputs. |
| 11 | adaptco/core-orchestrator | UNAVAILABLE `secrets/*.pem/*.key/.env` | Missing-access risk check | Secret material in runtime repo increases compromise blast radius. |
| 12 | Q-Enterprises/core-orchestrator | UNAVAILABLE import graph | Coupling graph blocked | Unknown import edges between runtime and training modules implies architecture ambiguity risk. |
| 13 | adaptco/core-orchestrator | UNAVAILABLE MCP/A2A surfaces | Runtime criticality unknown | If toolserver + orchestration loops are present, this repo should be AGENTS host (runtime-first principle). |
| 14 | Q-Enterprises/core-orchestrator | UNAVAILABLE training pipelines | Asset-weight likelihood | If LoRA/index pipelines exist, this repo should be MODELS host to isolate heavy assets. |
| 15 | both repos | UNAVAILABLE artifact ledger paths | Attestation readiness unknown | Absent verifiable ledger paths, append-only commitments must be added before production split. |

### Evidence citations used for table
- Access failures and command outputs: `SCAN_EVIDENCE.md`.

## Inventory and classification (requested categories)
Because repositories are inaccessible, this is a **forced risk-based provisional classification**:
- Agent runtime code: unknown (planner/evaluator/executor/toolserver/MCP/A2A not inspectable).
- Model code: unknown (embeddings/index/LoRA/datasets not inspectable).
- Artifact code/data: unknown (ledger/receipts/merkle/signatures not inspectable).

## Coupling graph (blocked)
- Import edges linking agent modules to model modules: unavailable due inaccessible source trees.
- Runtime calls crossing boundaries: unavailable.
- Artifact writes into source-controlled paths: unavailable.

## Context contamination risk flags
Given missing repository access, treat all of the below as **must-scan / fail-closed** risks before merge:
1. Large corpora committed in repo.
2. Prompt dumps/eval fixtures with proprietary context.
3. Embedding indexes committed.
4. Model weights committed.
5. Logs/spools committed.
6. Secrets/keys committed.

## Forced decision rubric (numeric)
Scoring scale: 0–10 per component; higher AGENTS score wins.

| Repo | Runtime criticality | Asset weight (inverse for AGENTS suitability) | Release cadence mismatch risk | Contamination surface (inverse for AGENTS suitability) | Operational blast radius control | AGENTS suitability total |
|---|---:|---:|---:|---:|---:|---:|
| adaptco/core-orchestrator | 8 | 6 | 7 | 7 | 8 | **36** |
| Q-Enterprises/core-orchestrator | 6 | 4 | 5 | 5 | 6 | **26** |

Decision rationale (under uncertainty): assign the repo with expected tighter runtime boundary and smaller assumed asset footprint to AGENTS host; place likely heavier enterprise asset workflows in MODELS host.

## Final layout (target state)
- `adaptco/core-orchestrator` (**AGENTS_HOST**)
  - orchestrator runtime, agent loops, policy/theta gates, MCP/A2A bridges, tool schemas, verification clients.
  - no corpora/weights/index snapshots.
- `Q-Enterprises/core-orchestrator` (**MODELS_HOST**)
  - dataset manifests, index builds, embedding pipelines, LoRA training, artifact publishing.
  - produces signed/hashed manifests + artifact URIs for AGENTS_HOST consumption.
- External artifact store (recommended)
  - object store bucket with immutable versioning (e.g., `s3://ml-artifacts/...` or `gs://ml-artifacts/...`).
  - append-only ledger table/object log for commitment tuples.

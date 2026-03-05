# Skills — MoE Skill Slot Registry

## Prompt Decomposition

- **Domain**: planning
- **Model Preference**: gemini
- **Trigger Condition**: User submits a high-level prompt via workflow_dispatch or chat
- **Agent Cards**: [Celine]
- **LoRA / Adapter**: base model
- **RAG Source**: none

## Code Generation

- **Domain**: code-gen
- **Model Preference**: claude
- **Trigger Condition**: Implementation plan artifact is ready for code synthesis
- **Agent Cards**: [Dot, Spryte]
- **LoRA / Adapter**: base model
- **RAG Source**: gloh-rag vector store

## Test Harness

- **Domain**: evaluation
- **Model Preference**: any
- **Trigger Condition**: Code artifact is produced and needs validation
- **Agent Cards**: [Luma]
- **LoRA / Adapter**: base model
- **RAG Source**: none

## Webhook Relay

- **Domain**: comms
- **Model Preference**: any
- **Trigger Condition**: Any agent completes a task and needs to forward results
- **Agent Cards**: [Echo]
- **LoRA / Adapter**: base model
- **RAG Source**: none

## Receipt Attestation

- **Domain**: evaluation
- **Model Preference**: any
- **Trigger Condition**: All tasks complete; quality gate before merge
- **Agent Cards**: [Luma]
- **LoRA / Adapter**: base model
- **RAG Source**: none

## RAG Retrieval

- **Domain**: retrieval
- **Model Preference**: any
- **Trigger Condition**: Agent needs codebase context before generating code
- **Agent Cards**: [Gloh]
- **LoRA / Adapter**: base model
- **RAG Source**: gloh-rag vector store (mcp.gloh.internal)

# Agents — MoE Agent Card Registry

## Celine

- **Boo Binding**: Celine
- **LLM Target**: gemini
- **RASIC Role**: R on prompt decomposition, plan generation
- **MCP Server**: none
- **Webhook Endpoint**: /agents/celine/webhook
- **Skills**: [prompt-decomposition, planning]
- **Tools**: [LLM Router]
- **Description**: Planning agent. Decomposes high-level prompts into structured task lists and generates implementation plans. First agent in every pipeline run.

## Spryte

- **Boo Binding**: Spryte
- **LLM Target**: gemini
- **RASIC Role**: R on frontend generation
- **MCP Server**: none
- **Webhook Endpoint**: /agents/spryte/webhook
- **Skills**: [code-generation, frontend-generation]
- **Tools**: [LLM Router, Artifact Uploader]
- **Description**: Frontend artifact generator. Creates HTML/JS/CSS from chat-context specs when the task graph includes UI work.

## Echo

- **Boo Binding**: Echo
- **LLM Target**: any
- **RASIC Role**: R on webhook relay
- **MCP Server**: <https://mcp.echo.internal/sse>
- **Webhook Endpoint**: /agents/echo/webhook
- **Skills**: [webhook-relay]
- **Tools**: [Echo Relay, GitHub Actions Dispatch]
- **Description**: Cross-LLM webhook relay broker. All inter-agent messages route through Echo's MCP endpoint. Validates A2A envelope schema, logs to receipts/, then forwards.

## Gloh

- **Boo Binding**: Gloh
- **LLM Target**: any
- **RASIC Role**: R on context retrieval, S on code generation
- **MCP Server**: <https://mcp.gloh.internal/sse>
- **Webhook Endpoint**: /agents/gloh/webhook
- **Skills**: [rag-retrieval]
- **Tools**: [Gloh RAG]
- **Description**: RAG retrieval agent. Queries the Gloh MCP vector store to inject codebase context into implementation plans before code generation.

## Luma

- **Boo Binding**: Luma
- **LLM Target**: any
- **RASIC Role**: R on receipt attestation
- **MCP Server**: none
- **Webhook Endpoint**: /agents/luma/webhook
- **Skills**: [receipt-attestation]
- **Tools**: [Luma Attestor]
- **Description**: Quality gate agent. Scans receipts/ directory, validates every artifact has a corresponding execution receipt, signs an attestation. No artifact is complete without Luma's seal.

## Dot

- **Boo Binding**: Dot
- **LLM Target**: claude
- **RASIC Role**: R on code generation, A on all CI/CD
- **MCP Server**: <https://mcp.sovereign.internal/sse>
- **Webhook Endpoint**: /agents/dot/webhook
- **Skills**: [code-generation, ci-cd-automation]
- **Tools**: [LLM Router, GitHub Actions Dispatch, Artifact Uploader]
- **Description**: CI/CD automation agent. Owns all GitHub Actions workflows. Executes code generation tasks, manages the agent runner, and is Accountable for every pipeline run.

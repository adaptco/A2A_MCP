# Agents

This file is the A2A skill-card source of truth for the Charley Fox runtime handoff in Antigravity's root `.github` workflows. Dot's CD rest point is the `dot-runtime-rest-point` job, which runs after `build-and-test` and before `push-to-registry` or `security-scan`.

## Agent Charley Fox
- **Boo Binding**: Spryte
- **LLM Target**: gemini
- **RASIC Role**: R on Gemini token routing, tensor exchange authoring, and the post-build A2A handoff
- **MCP Server**: `mcp://antigravity.internal/charley-fox`
- **Webhook Endpoint**: `/a2a/charley-fox/handoff`
- **Skills**: `runtime.assignment.v1`, `a2a.skill-card.normal.v1`, `tensor-origin.mapping.v1`
- **Tools**: `gemini_chat`, `gemini_embeddings`, `tensor_projector`, `runtime_assignment_submitter`
- **Description**: Coding avatar and repo reasoner that turns the validated build state into a Gemini-ready skill card and projects embedding vectors into a 3D origin.

## Dot
- **Boo Binding**: Dot
- **LLM Target**: any
- **RASIC Role**: A on the CD rest point and R on release gating after contract validation
- **MCP Server**: `mcp://antigravity.internal/dot`
- **Webhook Endpoint**: `/a2a/dot/rest-point`
- **Skills**: `release.gate.v1`, `workflow.rest-point.v1`, `artifact.attestation.v1`
- **Tools**: `runtime_contract_validator`, `workflow_rest_point_gate`, `ghcr_release_controller`
- **Description**: CI/CD owner that pauses the pipeline at the rest point, validates the Charley Fox runtime contract, and only then unlocks downstream release jobs.

## Gemini Bridge
- **Boo Binding**: External
- **LLM Target**: gemini
- **RASIC Role**: S on provider translation for chat and embedding requests
- **MCP Server**: `mcp://antigravity.internal/gemini-bridge`
- **Webhook Endpoint**: `/a2a/gemini/bridge`
- **Skills**: `provider-routing.v1`, `embedding.normalization.v1`
- **Tools**: `gemini_token_router`, `chat_adapter`, `embedding_adapter`
- **Description**: Provider adapter that receives the normal-form A2A envelope and maps it onto Gemini's chat and embedding surfaces with `GEMINI_API_KEY`.

## Normal Exchange Format
- **Schema**: `a2a.skill-card.normal.v1`
- **Exchange Id**: `dot.tensor.exchange.v1`
- **Auth Env**: `GEMINI_API_KEY`
- **Chat Endpoint**: `/gemini/chat`
- **Embedding Endpoint**: `/gemini/embeddings`
- **Vector Origin**: `[0, 0, 0]`
- **Tensor Axes**: `x`, `y`, `z`
- **Similarity**: `dot_product`
- **Normalization**: `l2`

```json
{
  "schema": "a2a.skill-card.normal.v1",
  "exchange_id": "dot.tensor.exchange.v1",
  "provider": "gemini",
  "auth_env": "GEMINI_API_KEY",
  "chat_endpoint": "/gemini/chat",
  "embedding_endpoint": "/gemini/embeddings",
  "origin": [0, 0, 0],
  "tensor_axes": ["x", "y", "z"],
  "metric": "dot_product",
  "vector": [0.0, 0.0, 0.0]
}
```

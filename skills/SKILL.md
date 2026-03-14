---
name: skills-catalog
description: Consolidated skill registry generated for agent automation and CI upskill loops.
---

# Skills Catalog

<<<<<<< HEAD
_Generated: 2026-03-05T19:09:10Z (UTC)_

- Total skills discovered: **49**
- Workflow definitions discovered: **55**
=======
_Generated: 2026-03-13T19:39:08Z (UTC)_

- Total skills discovered: **54**
- Workflow definitions discovered: **59**
>>>>>>> origin/main

## Skills

| Name | Source Root | Path | Description |
|---|---|---|---|
| `appinsights-instrumentation` | `skills` | `skills/appinsights-instrumentation/SKILL.md` | >- |
<<<<<<< HEAD
=======
| `avatar-mcp-root-context` | `skills` | `skills/avatar-mcp-root-context/SKILL.md` | Build zero-shot root-repo launch context for Codex avatar flows in the A2A_MCP repository by combining AGENTS.md, avatar bindings, frontier agent cards, and MCP tool surfaces into a compact packet. Use when API-triggered avatar tokens must launch from the MCP node, when a chat model needs root GitHub codebase context before tool use, or when preparing payloads for ingest_repository_data, ingest_avatar_token_stream, build_local_world_foundation_model, get_coding_agent_avatar_cast, or route_a2a_intent. |
>>>>>>> origin/main
| `azure-ai` | `skills` | `skills/azure-ai/SKILL.md` | Use for Azure AI: Search, Speech, OpenAI, Document Intelligence. Helps with search, vector/hybrid search, speech-to-text, text-to-speech, transcription, OCR. USE FOR: AI Search, query search, vector search, hybrid search, semantic search, speech-to-text, text-to-speech, transcribe, OCR, convert text to speech. DO NOT USE FOR: Function apps/Functions (use azure-functions), databases (azure-postgres/azure-kusto), general Azure resources. |
| `azure-aigateway` | `skills` | `skills/azure-aigateway/SKILL.md` | >- |
| `azure-compliance` | `skills` | `skills/azure-compliance/SKILL.md` | >- |
| `azure-cost-optimization` | `skills` | `skills/azure-cost-optimization/SKILL.md` | >- |
| `azure-deploy` | `skills` | `skills/azure-deploy/SKILL.md` | >- |
| `azure-diagnostics` | `skills` | `skills/azure-diagnostics/SKILL.md` | >- |
| `azure-hosted-copilot-sdk` | `skills` | `skills/azure-hosted-copilot-sdk/SKILL.md` | Build and deploy GitHub Copilot SDK apps to Azure. USE FOR: build copilot app, create copilot app, copilot SDK, @github/copilot-sdk, scaffold copilot project, copilot-powered app, deploy copilot app, host on azure, azure model, BYOM, bring your own model, use my own model, azure openai model, DefaultAzureCredential, self-hosted model, copilot SDK service, chat app with copilot, copilot-sdk-service template, azd init copilot, CopilotClient, createSession, sendAndWait, GitHub Models API. DO NOT USE FOR: using Copilot (not building with it), Copilot Extensions, Azure Functions without Copilot, general web apps without copilot SDK, Foundry agent hosting (use microsoft-foundry skill), agent evaluation (use microsoft-foundry skill). |
| `azure-kusto` | `skills` | `skills/azure-kusto/SKILL.md` | >- |
| `azure-messaging` | `skills` | `skills/azure-messaging/SKILL.md` | >- |
| `azure-observability` | `skills` | `skills/azure-observability/SKILL.md` | >- |
| `azure-postgres` | `skills` | `skills/azure-postgres/SKILL.md` | >- |
| `azure-prepare` | `skills` | `skills/azure-prepare/SKILL.md` | >- |
| `azure-rbac` | `skills` | `skills/azure-rbac/SKILL.md` | >- |
| `azure-resource-lookup` | `skills` | `skills/azure-resource-lookup/SKILL.md` | >- |
| `azure-resource-visualizer` | `skills` | `skills/azure-resource-visualizer/SKILL.md` | >- |
| `azure-storage` | `skills` | `skills/azure-storage/SKILL.md` | >- |
| `azure-validate` | `skills` | `skills/azure-validate/SKILL.md` | >- |
| `entra-app-registration` | `skills` | `skills/entra-app-registration/SKILL.md` | >- |
<<<<<<< HEAD
=======
| `mcp-entropy-template-router` | `skills` | `skills/mcp-entropy-template-router/SKILL.md` | Generate deterministic MCP routing controls that combine API skill tokens, enthalpy/entropy style temperature tuning, and uniform dotproduct template selection for frontend/backend/fullstack actions. Use when orchestrator payloads need stable template-triggered implementation actions and avatar runtime token bindings. |
>>>>>>> origin/main
| `capacity` | `skills` | `skills/microsoft-foundry/models/deploy-model/capacity/SKILL.md` | >- |
| `customize` | `skills` | `skills/microsoft-foundry/models/deploy-model/customize/SKILL.md` | >- |
| `preset` | `skills` | `skills/microsoft-foundry/models/deploy-model/preset/SKILL.md` | >- |
| `deploy-model` | `skills` | `skills/microsoft-foundry/models/deploy-model/SKILL.md` | >- |
| `microsoft-foundry` | `skills` | `skills/microsoft-foundry/SKILL.md` | >- |
| `optimize-complexity` | `skills` | `skills/optimize-complexity/SKILL.md` | Optimize tool complexity distribution from orchestration checkpoint CSV files using deterministic embedding similarity and complexity relabeling. Use when you need to analyze token bottlenecks, rebalance tool complexity, generate optimization reports, or prepare CI-ready complexity artifacts from a single checkpoint CSV. |
<<<<<<< HEAD
=======
| `skills-catalog` | `skills` | `skills/SKILL.md` | Consolidated skill registry generated for agent automation and CI upskill loops. |
>>>>>>> origin/main
| `appinsights-instrumentation` | `a2a_mcp/skills` | `a2a_mcp/skills/appinsights-instrumentation/SKILL.md` | >- |
| `azure-ai` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-ai/SKILL.md` | Use for Azure AI: Search, Speech, OpenAI, Document Intelligence. Helps with search, vector/hybrid search, speech-to-text, text-to-speech, transcription, OCR. USE FOR: AI Search, query search, vector search, hybrid search, semantic search, speech-to-text, text-to-speech, transcribe, OCR, convert text to speech. DO NOT USE FOR: Function apps/Functions (use azure-functions), databases (azure-postgres/azure-kusto), general Azure resources. |
| `azure-aigateway` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-aigateway/SKILL.md` | >- |
| `azure-compliance` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-compliance/SKILL.md` | >- |
| `azure-cost-optimization` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-cost-optimization/SKILL.md` | >- |
| `azure-deploy` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-deploy/SKILL.md` | >- |
| `azure-diagnostics` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-diagnostics/SKILL.md` | >- |
| `azure-hosted-copilot-sdk` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-hosted-copilot-sdk/SKILL.md` | Build and deploy GitHub Copilot SDK apps to Azure. USE FOR: build copilot app, create copilot app, copilot SDK, @github/copilot-sdk, scaffold copilot project, copilot-powered app, deploy copilot app, host on azure, azure model, BYOM, bring your own model, use my own model, azure openai model, DefaultAzureCredential, self-hosted model, copilot SDK service, chat app with copilot, copilot-sdk-service template, azd init copilot, CopilotClient, createSession, sendAndWait, GitHub Models API. DO NOT USE FOR: using Copilot (not building with it), Copilot Extensions, Azure Functions without Copilot, general web apps without copilot SDK, Foundry agent hosting (use microsoft-foundry skill), agent evaluation (use microsoft-foundry skill). |
| `azure-kusto` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-kusto/SKILL.md` | >- |
| `azure-messaging` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-messaging/SKILL.md` | >- |
| `azure-observability` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-observability/SKILL.md` | >- |
| `azure-postgres` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-postgres/SKILL.md` | >- |
| `azure-prepare` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-prepare/SKILL.md` | >- |
| `azure-rbac` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-rbac/SKILL.md` | >- |
| `azure-resource-lookup` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-resource-lookup/SKILL.md` | >- |
| `azure-resource-visualizer` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-resource-visualizer/SKILL.md` | >- |
| `azure-storage` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-storage/SKILL.md` | >- |
| `azure-validate` | `a2a_mcp/skills` | `a2a_mcp/skills/azure-validate/SKILL.md` | >- |
| `entra-app-registration` | `a2a_mcp/skills` | `a2a_mcp/skills/entra-app-registration/SKILL.md` | >- |
<<<<<<< HEAD
=======
| `mcp-entropy-template-router` | `a2a_mcp/skills` | `a2a_mcp/skills/mcp-entropy-template-router/SKILL.md` | Generate deterministic MCP routing controls that combine API skill tokens, enthalpy/entropy style temperature tuning, and uniform dotproduct template selection for frontend/backend/fullstack actions. Use when orchestrator payloads need stable template-triggered implementation actions and avatar runtime token bindings. |
>>>>>>> origin/main
| `capacity` | `a2a_mcp/skills` | `a2a_mcp/skills/microsoft-foundry/models/deploy-model/capacity/SKILL.md` | >- |
| `customize` | `a2a_mcp/skills` | `a2a_mcp/skills/microsoft-foundry/models/deploy-model/customize/SKILL.md` | >- |
| `preset` | `a2a_mcp/skills` | `a2a_mcp/skills/microsoft-foundry/models/deploy-model/preset/SKILL.md` | >- |
| `deploy-model` | `a2a_mcp/skills` | `a2a_mcp/skills/microsoft-foundry/models/deploy-model/SKILL.md` | >- |
| `microsoft-foundry` | `a2a_mcp/skills` | `a2a_mcp/skills/microsoft-foundry/SKILL.md` | >- |
<<<<<<< HEAD
=======
| `optimize-complexity` | `a2a_mcp/skills` | `a2a_mcp/skills/optimize-complexity/SKILL.md` | Optimize tool complexity distribution from orchestration checkpoint CSV files using deterministic embedding similarity and complexity relabeling. Use when you need to analyze token bottlenecks, rebalance tool complexity, generate optimization reports, or prepare CI-ready complexity artifacts from a single checkpoint CSV. |
>>>>>>> origin/main

## Workflow Surface

- `.github/workflows/agents-ci-cd.yml`
- `.github/workflows/agents-unit-tests.yml`
- `.github/workflows/art.i.fact.yml`
<<<<<<< HEAD
=======
- `.github/workflows/automerge-threads.yml`
>>>>>>> origin/main
- `.github/workflows/avatar-bindings-ci.yml`
- `.github/workflows/avatar-bindings-governance.yml`
- `.github/workflows/avatar-engine.yml`
- `.github/workflows/bats-ci.yml`
- `.github/workflows/build-spine.yml`
- `.github/workflows/ci.yml`
- `.github/workflows/claude_release_orchestrator.yml`
- `.github/workflows/cockpit-dispatch-handler.yml`
- `.github/workflows/codeql.yml`
- `.github/workflows/core_orchestrator_ci.yml`
- `.github/workflows/daily_ingress.yml`
- `.github/workflows/defender-for-devops.yml`
- `.github/workflows/deploy-stack.yml`
- `.github/workflows/deploy.yml`
- `.github/workflows/docker-image.yml`
- `.github/workflows/docs.yml`
- `.github/workflows/drift-gate.yml`
- `.github/workflows/fonts-proxy-ci-cd.yml`
- `.github/workflows/freeze_artifact.yml`
- `.github/workflows/game-validation.yml`
<<<<<<< HEAD
=======
- `.github/workflows/gemini-os-pipeline.yml`
>>>>>>> origin/main
- `.github/workflows/governance_check.yml`
- `.github/workflows/integration_test.yml`
- `.github/workflows/invariant-check.yml`
- `.github/workflows/jekyll-gh-pages.yml`
- `.github/workflows/lattice-integration.yml`
- `.github/workflows/ledger_sync.yml`
- `.github/workflows/lint-diff-build-test.yml`
- `.github/workflows/main.yml`
- `.github/workflows/manual-ci.yml`
<<<<<<< HEAD
=======
- `.github/workflows/mcp-server-client-api-validation.yml`
>>>>>>> origin/main
- `.github/workflows/milestone_autopublish.yml`
- `.github/workflows/ml_pipeline.yml`
- `.github/workflows/multimodal-rag-cicd.yml`
- `.github/workflows/node.js.yml`
- `.github/workflows/override_request.yml`
- `.github/workflows/pr_commit_validation.yml`
- `.github/workflows/prime_pipeline_ci.yml`
<<<<<<< HEAD
=======
- `.github/workflows/production-ci.yml`
>>>>>>> origin/main
- `.github/workflows/push_knowledge.yml`
- `.github/workflows/pylint.yml`
- `.github/workflows/python-app.yml`
- `.github/workflows/python-ci.yml`
- `.github/workflows/python-package-conda.yml`
- `.github/workflows/python-publish.yml`
- `.github/workflows/qube-multimodal-worldline.yml`
- `.github/workflows/release-gke-deploy.yml`
- `.github/workflows/reusable-gke-deploy.yml`
- `.github/workflows/reusable-release-build.yml`
- `.github/workflows/smart-ci.yml`
- `.github/workflows/sovereign-lineage-ci.yml`
- `.github/workflows/webpack.yml`
- `.github/workflows/workflow-lint.yml`
- `.github/workflows/workspace-ci.yml`
- `.github/workflows/worldline_hardened_pipeline.yml`

## Review Automation Contract

- Agents should scan open pull requests, collect unresolved comments/threads, and apply fixes in-order.
- Merge is allowed only after required checks pass and merge conflicts are resolved.
- Daily upskill runs are orchestrated by `.github/workflows/avatar-engine.yml`.

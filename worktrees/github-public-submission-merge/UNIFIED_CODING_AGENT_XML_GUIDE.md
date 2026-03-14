# Unified Coding Agent XML Blueprint

This document explains how to use `unified_coding_agent_merge.xml` to orchestrate a merged coding agent with reusable global variables.

## What this XML provides

- A **global variable layer** (`<GlobalVariables>`) for cloud, model, runtime, and observability defaults.
- A **model catalog** (`<ModelCatalog>`) to represent specialized experts.
- A **merge policy** (`<MergePolicy>`) for routing and weighted aggregation.
- **Reusable contexts** (`<ReusableContexts>`) for enterprise, Unity MLOps, and cost-focused modes.
- A deployment pipeline and GitHub Actions workflow wiring in `<ActionsWiring>`.

## How to use

1. Load the XML in your orchestrator (or convert to runtime config objects).
2. Resolve `${VAR}` placeholders from `<GlobalVariables>`.
3. Activate one `<Context>` profile per environment.
4. Execute routing + aggregation rules from `<MergePolicy>`.
5. Trigger CI and nightly training workflows from `<ActionsWiring>`.

## Recommended mapping

- `<ModelCatalog>` → model router / MoE registry.
- `<Pipeline>` → CI/CD DAG (Actions, Argo, or Temporal).
- `<ActionsWiring>` → `.github/workflows/*.yml` generation source.
- `<Governance>` → policy-as-code checks in CI.

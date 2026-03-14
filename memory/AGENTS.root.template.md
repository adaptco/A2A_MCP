# Root Agent Memory

This file is the persistent root-memory anchor for Codex and other coding agents.
The machine-readable payload lives in the fenced JSON block below.

```json
{
  "workspace_preferences": {
    "working_style": {
      "tone": "direct",
      "execution_mode": "deterministic_moa_loop",
      "planning_bias": "implementation_first",
      "risk_posture": "guarded_delivery",
      "context_strategy": "chunk_relevant_context",
      "time_management": "checkpointed",
      "token_management": "budgeted"
    },
    "topology_mode": "single_mcp_environment",
    "runtime_priority": [
      "planner",
      "architect",
      "coder",
      "tester",
      "reviewer"
    ],
    "approval_mode": "browser_hitl",
    "reward_focus": [
      "semantic",
      "systems",
      "domain"
    ]
  },
  "agent_overrides": {
    "agent:blackmamba": {
      "enterprise_role": "timekeeper",
      "working_style": {
        "tone": "precise",
        "time_management": "cost_estimation_first",
        "token_management": "predict_then_allocate"
      }
    }
  },
  "milestones": [
    {
      "id": "M1",
      "name": "Canonical model and memory refactor",
      "duration_business_days": [2, 3],
      "token_budget": [120000, 180000]
    },
    {
      "id": "M2",
      "name": "MAP XML and expanded agent-card compiler",
      "duration_business_days": [3, 4],
      "token_budget": [180000, 260000]
    },
    {
      "id": "M3",
      "name": "Extension/interface topology wiring",
      "duration_business_days": [3, 5],
      "token_budget": [220000, 320000]
    },
    {
      "id": "M4",
      "name": "BlackMamba library and economics model",
      "duration_business_days": [4, 5],
      "token_budget": [240000, 340000]
    },
    {
      "id": "M5",
      "name": "HITL browser app and sandbox validation",
      "duration_business_days": [3, 4],
      "token_budget": [180000, 260000]
    },
    {
      "id": "M6",
      "name": "PR reconciliation and release hardening",
      "duration_business_days": [4, 6],
      "token_budget": [260000, 380000]
    },
    {
      "id": "M7",
      "name": "Org .github promotion and live enterprise connectors",
      "duration_business_days": [5, 8],
      "token_budget": [300000, 500000]
    }
  ],
  "token_budget": {
    "loop_1": {
      "tokens": [940000, 1360000],
      "business_days": [15, 21]
    },
    "program": {
      "tokens": [1500000, 2240000],
      "business_days": [24, 35]
    }
  }
}
```

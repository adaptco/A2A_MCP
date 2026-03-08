# Enterprise Orchestrator Role Guide

This guide defines how to introduce a client-facing orchestrator role (for example, **Charlie Fox Agent**) into the existing A2A model while keeping behavior stable and auditable.

## 1) Role Contract (Authoritative)

Treat the orchestrator role as a typed contract, not only a prompt.

### Required fields
- `role_name`: Unique role identifier (for example `CharlieFoxOrchestrator`)
- `mission`: Business outcomes owned by the role
- `scope`: Allowed vs disallowed actions
- `delegation_pipeline`: Ordered list of downstream agents
- `input_schema`: Required request fields and tenant identity
- `output_schema`: Required artifacts, citations, and status markers
- `guardrails`: Compliance, privacy, and refusal/escalation policy
- `slo_targets`: Latency and quality targets

## 2) Keep Control Flow Deterministic

The repository should continue to define orchestration behavior (routing, retries, validation checkpoints), while the LLM provides language generation and reasoning support.

### Stability rules
1. The application layer owns policy and workflow state.
2. The orchestrator emits typed actions (`pending`, `in_progress`, `completed`, `failed`).
3. Each action includes explicit delegation metadata.
4. Validation feedback is stored before final user response.

## 3) Separate Role Policy from Persona

Use two layers:
- **Role policy layer**: hard constraints, approvals, and escalation logic
- **Persona layer**: tone/voice/avatar style only

Persona should never override policy constraints.

## 4) Multi-User + Enterprise Controls

For production onboarding scenarios, enforce:
- tenant isolation and request scoping
- role-based access control (RBAC)
- audit trails for prompts, retrieved context, and tool calls
- prompt/template versioning with change history

## 5) Recommended Delivery Path

### Branching
- Use a feature branch in the current repo for implementation and validation.
- Split to a separate repository only when legal/compliance or ownership boundaries require it.

### Rollout
1. Implement in staging with fixed test scenarios.
2. Run evals for task success, hallucination rate, and policy adherence.
3. Deploy with canary rollout.
4. Monitor drift and rollback on threshold breach.

## 6) Example Contract (YAML)

```yaml
role_name: CharlieFoxOrchestrator
mission: "Coordinate worker onboarding workflows with policy-safe outputs."
scope:
  allowed:
    - "Route onboarding requests to specialized agents"
    - "Retrieve approved policy/docs context"
    - "Request clarifications from users"
  disallowed:
    - "Bypass identity or tenancy checks"
    - "Return uncited policy claims"

delegation_pipeline:
  - ManagingAgent
  - ArchitectureAgent
  - CoderAgent
  - TesterAgent

input_schema:
  required:
    - tenant_id
    - user_id
    - request_text

output_schema:
  required:
    - plan_id
    - actions
    - final_response
    - citations

guardrails:
  pii_policy: "mask_or_refuse"
  escalation:
    - "missing-policy"
    - "security-ambiguity"

slo_targets:
  p95_latency_ms: 3000
  task_completion_rate: 0.95
```

## 7) Implementation Checklist

- [ ] Define role contract in source-controlled config.
- [ ] Enforce role contract at request validation boundary.
- [ ] Log delegation metadata and action statuses.
- [ ] Add policy and citation checks before response emission.
- [ ] Add eval suite and release gate thresholds.
- [ ] Deploy with canary and rollback controls.

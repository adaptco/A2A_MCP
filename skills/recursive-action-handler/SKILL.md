---
name: recursive-action-handler
description: Implement recursive task execution as discrete orchestration actions. Use when an objective requires multi-level decomposition where a child task can trigger further sub-tasks, ensuring each level is registered as an immutable artifact in the Digital Weave.
---

# Recursive Action Handler

Enable agents to define and trigger recursive sub-tasks as standard actions.

## Do This

1. Use when a task (e.g., "Implement feature X") requires further decomposition that isn't known at the top-level orchestration phase.
2. Define an `Action` that, when executed, emits a `TaskDecomposition` event rather than a terminal code artifact.
3. Use `orchestrator/stateflow.py` to transition the parent task into `AWAITING_CHILDREN`.
4. Register child tasks with the `ManagingAgent` using the parent's `artifact_id` as the `correlation_id`.
5. Implement a "base case" check to prevent infinite recursion:
   - Max recursion depth: 3
   - Min task complexity threshold for further decomposition.

## Command

```bash
python scripts/trigger_recursive_action.py \
  --parent-task-id "task-123" \
  --sub-tasks "Breakdown infra, Setup DB, Implement API"
```

## Outputs

- `ChildTaskArtifacts`: registered in `DBManager`.
- `StateTransition`: parent task moves to `PENDING_VALIDATION` only after all children are `DONE`.
- `RecursionTelemetry`: tracking depth and branch count.

## Read When Needed

- FSM logic: `orchestrator/stateflow.py`
- Task schema: `schemas/agent_artifacts.py`
- Decomposition logic: `agents/managing_agent.py`

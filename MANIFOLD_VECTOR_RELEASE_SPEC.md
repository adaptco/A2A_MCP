# Manifold Vector Release Control Specification

## Scope
Release control for runtime assignment artifacts produced by orchestration MCP and consumed by runtime MCP.

## Gate Conditions
1. `claude_task_complete` is true.
2. CI validations pass (`tests_passed`, `conflicts_resolved`).
3. Kernel controls are present:
   - `kernel_model_written`
   - `root_specs_scaffolded`
   - `api_token_release_controlled`
4. Bot review completes before release publish.

## Assignment Schema Requirements
- `schema_version`: `runtime.assignment.v1`
- `token_stream_stats.normalized`: true
- `kernel_model.api_token_env_var`: `A2A_MCP_API_TOKEN`
- `kernel_model.release_control.required_phase`: `ready_for_release`

## Operational Notes
- Runtime bridge writes assignment artifacts as `runtime.assignment.v1`.
- Release orchestrator blocks promotion when kernel/spec/token controls are absent.

# Orchestration Epoch State (Claude -> Bot -> Release)

## Purpose
This document defines the managing-agent orchestration model used to:
1. Wait for Claude task completion.
2. Run validation and merge-conflict checks.
3. Trigger automated bot review for PR readiness.
4. Publish a foundation release state bundle.

## State Model
Implemented in `orchestrator/release_orchestrator.py`.

Phases:
- `waiting_for_claude`
- `running_validation`
- `running_bot_review`
- `ready_for_release`
- `blocked`

Signals:
- `claude_task_complete`
- `tests_passed`
- `conflicts_resolved`
- `bot_review_complete`
- `claude_checked_todos`
- `claude_total_todos`

Decision manifold (CWUG-v1) action order:
1. Wait for Claude completion.
2. Validate tests and conflicts.
3. Run bot review.
4. Publish foundation release bundle.

## GitHub Actions Wiring
Workflow: `.github/workflows/claude_release_orchestrator.yml`

Jobs:
1. `wait-for-claude`
   - Reads issue checklist progress or dispatch override.
   - Gates pipeline until Claude checklist is complete.
2. `validate-and-check-conflicts`
   - Runs tests.
   - Performs merge preview against `origin/main` and fails on conflicts.
3. `bot-review-and-state`
   - Generates `system_state.json`.
   - Posts/upserts PR review gate summary comment.
   - Uploads foundation bundle artifacts.

## Expected Output Artifacts
- `system_state.json`
- `FOUNDATION_MODEL_RELEASE_SPEC.md`
- `AGENT_IDLE_STATE_RELEASE_NOTES.md`
- `release_milestones.yaml`
- `xml_normalization_map.yaml`
- `manifold_action_language.schema.json`


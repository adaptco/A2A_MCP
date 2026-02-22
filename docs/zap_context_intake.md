# Zap Context Intake Template

Use this template to capture the missing mappings and conditions required to
complete the Zap described in the current `zapContext`.

## 1) Webhook intent (Step 1 → Step 2 filter)

- **Webhook purpose**: _e.g., CIE-V1 audit event, World Engine audit event_
- **Primary identifier (filter field)**: `arc_id`
- **Event type**: _e.g., `cie.audit.completed`, `world_engine.run.completed`_

## 2) Airtable mappings (Steps 5–6)

| Field | Value |
| --- | --- |
| Base ID / Name |  |
| Table name |  |
| Step 5 search field |  |
| Step 5 search value mapping |  |
| Step 6 update fields |  |

## 3) Path A condition (Step 4)

- **Condition**: _e.g., `status == "verified"`_
- **Expected behavior**: _e.g., update Airtable status + add timestamp_

## 4) Path B condition (Step 9)

- **Condition**: _e.g., `status == "failed"`_
- **Expected behavior**: _e.g., open GitHub PR with failure context_

## 5) GitHub PR details (Step 10)

| Field | Value |
| --- | --- |
| Repo (owner/name) |  |
| PR title |  |
| PR body |  |
| Base branch |  |

## 6) Suggested payload schema (for Step 1)

Use `schemas/zap_context.webhook.v1.json` to validate webhook input payloads.

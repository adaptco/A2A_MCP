# Option-B Zapier Wiring (Server-Owned Slack Replies)

## Objective
Use Zapier to detect Slack command messages and forward normalized payloads to `/orchestrate`.
The **server** posts ack/final messages to Slack, so Zapier can stop after webhook POST.

## Required Environment (server side)
- `AIRTABLE_PAT` (or legacy `AIRTABLE_API_KEY`)
- `AIRTABLE_BASE_ID`
- `AIRTABLE_AGENT_MIXTURE_TABLE=agent_mixture`
- `AIRTABLE_AGENT_RUNS_TABLE=agent_runs`
- `SLACK_BOT_TOKEN`
- `AUTH_DISABLED=false` with valid bearer auth in production

## Local Startup
```bash
pip install -e .[dev,integrations]
uvicorn orchestrator.api:app --host 0.0.0.0 --port 3000
```

## Smoke Request
```bash
curl -X POST "http://localhost:3000/orchestrate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -H "X-Idempotency-Key: local-smoke-001" \
  -d '{
    "command": "!triage",
    "args": "test run",
    "slack": {
      "channel_id": "C0ADDUZJ5V5",
      "thread_ts": "1736208745.294349"
    }
  }'
```

Expected:
- `200 OK`
- Response includes `run_id`, `routing_decision`, `airtable_record_id`, `slack_post_status`, `trace_id`
- Airtable run record transitions: `queued -> running -> success|failed`

## Zap Steps
1. Trigger: Slack new message in channel (`#all-adaptco`).
2. Filter: message starts with `!`.
3. Code step: parse command into `{ command, args, slack: { channel_id, thread_ts } }`.
4. Webhooks by Zapier: `POST https://<server>/orchestrate`
5. Headers:
   - `Authorization: Bearer <token>`
   - `Content-Type: application/json`
   - `X-Idempotency-Key: {{zap_meta_human_now}}-{{message_ts}}`
6. Body example:
```json
{
  "command": "!triage",
  "args": "test run",
  "slack": {
    "channel_id": "C0ADDUZJ5V5",
    "thread_ts": "1736208745.294349"
  }
}
```

## Expected Behavior
- API returns `200` with `run_id`, `routing_decision`, `airtable_record_id`, `slack_post_status`, `trace_id`.
- Airtable `agent_runs` record moves `queued -> running -> success|failed`.
- Slack thread receives server ack and result messages.

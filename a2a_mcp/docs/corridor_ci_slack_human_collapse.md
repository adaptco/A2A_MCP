# Corridor-Grade CI → Slack Human Collapse Loop

This guide defines the deterministic A → B review loop where CI telemetry triggers a
Slack review card, and a human click collapses the state into GitHub status updates
plus a ledger receipt. The flow is designed to be fail-closed and auditable.

## 1. Definitions (No Drift)

- **A = CI Result Telemetry Event** emitted by GitHub Actions.
- **B = Slack Review Card** with Approve/Reject buttons.
- **Collapse = Slack button click → Zapier verifies hash → GitHub status + ledger receipt.**

## 2. Data Flow Overview

1. GitHub Actions posts a deterministic payload to a Zapier Catch Hook (A).
2. Zapier computes `energy_hash` from a canonical field order.
3. Zapier posts a Slack message with buttons carrying `approve|reject`, `trace_id`, and `energy_hash`.
4. Slack interaction triggers Zap B.
5. Zap B recomputes `energy_hash`, verifies match, then updates GitHub and writes a ledger receipt.

## 3. Canonical Schemas

- **CI Telemetry Event**: `schemas/ci.telemetry.v1.json`
- **Ledger Receipt**: `schemas/ledger.corridor_stripe_slack.v1.json`

## 4. Canonicalization Rule (Energy Hash)

Canonical string format (exact order, separator `|`):

```
schema|trace_id|repo|pr_number|run_id|head_sha|workflow|conclusion|completed_at|required_check_name
```

Hash with SHA-256 over UTF-8 bytes and prefix with `sha256:`.

## 5. Zap A (CI → Slack)

**Steps**
1. Trigger: Webhooks by Zapier → Catch Hook (receives CI telemetry)
2. Action: Code by Zapier → compute `energy_hash`
3. Action: Slack → send message with interactive buttons

**Zapier Code Step: Compute energy_hash**

```javascript
const crypto = require('crypto');

function must(v, name) {
  if (v === undefined || v === null || String(v).trim() === '') {
    throw new Error(`FAIL_CLOSED: missing ${name}`);
  }
  return String(v);
}

const fields = {
  schema: must(bundle.inputData.schema, 'schema'),
  trace_id: must(bundle.inputData.trace_id, 'trace_id'),
  repo: must(bundle.inputData.repo, 'repo'),
  pr_number: must(bundle.inputData.pr_number, 'pr_number'),
  run_id: must(bundle.inputData.run_id, 'run_id'),
  head_sha: must(bundle.inputData.head_sha, 'head_sha'),
  workflow: must(bundle.inputData.workflow, 'workflow'),
  conclusion: must(bundle.inputData.conclusion, 'conclusion'),
  completed_at: must(bundle.inputData.completed_at, 'completed_at'),
  required_check_name: must(bundle.inputData.required_check_name, 'required_check_name'),
};

const canonical = [
  fields.schema,
  fields.trace_id,
  fields.repo,
  fields.pr_number,
  fields.run_id,
  fields.head_sha,
  fields.workflow,
  fields.conclusion,
  fields.completed_at,
  fields.required_check_name,
].join('|');

const digest = crypto.createHash('sha256').update(Buffer.from(canonical, 'utf8')).digest('hex');
const energy_hash = `sha256:${digest}`;

return { canonical, energy_hash };
```

**Slack Block Kit message**

```json
[
  {
    "type": "header",
    "text": { "type": "plain_text", "text": "Human Collapse Review Required", "emoji": true }
  },
  {
    "type": "section",
    "fields": [
      { "type": "mrkdwn", "text": "*Repo:*\n{{repo}}" },
      { "type": "mrkdwn", "text": "*PR:*\n#{{pr_number}}" },
      { "type": "mrkdwn", "text": "*Run ID:*\n{{run_id}}" },
      { "type": "mrkdwn", "text": "*Conclusion:*\n{{conclusion}}" }
    ]
  },
  { "type": "divider" },
  {
    "type": "actions",
    "elements": [
      {
        "type": "button",
        "text": { "type": "plain_text", "text": "Approve (Merge Gate)", "emoji": true },
        "style": "primary",
        "value": "approve_{{trace_id}}_{{energy_hash}}",
        "action_id": "collapse_approve"
      },
      {
        "type": "button",
        "text": { "type": "plain_text", "text": "Reject (Block)", "emoji": true },
        "style": "danger",
        "value": "reject_{{trace_id}}_{{energy_hash}}",
        "action_id": "collapse_reject"
      }
    ]
  },
  {
    "type": "context",
    "elements": [
      { "type": "mrkdwn", "text": "*Integrity:* `{{energy_hash}}`" }
    ]
  }
]
```

## 6. Zap B (Slack → Verify → GitHub → Ledger)

**Steps**
1. Trigger: Slack interaction
2. Action: load canonical CI fields by `trace_id` from storage
3. Action: recompute `energy_hash`, fail-closed on mismatch
4. Action: update GitHub status check `zapier/human-collapse`
5. Action: append `corridor-stripe-slack/v1` ledger receipt

**Zapier Code Step: Parse + Verify**

```javascript
const crypto = require('crypto');

const rawValue = bundle.inputData.action_value;
const [verdictType, traceId, providedHash] = rawValue.split('_');

const intentMap = {
  approve: "OPERATIONAL_FINALITY",
  reject: "ENTROPY_VIOLATION"
};

const decision = intentMap[verdictType];
if (!decision) throw new Error(`FAIL_CLOSED: invalid verdict type: ${verdictType}`);

function must(v, name) {
  if (v === undefined || v === null || String(v).trim() === '') {
    throw new Error(`FAIL_CLOSED: missing ${name}`);
  }
  return String(v);
}

const fields = {
  schema: must(bundle.inputData.schema, 'schema'),
  trace_id: must(bundle.inputData.trace_id, 'trace_id'),
  repo: must(bundle.inputData.repo, 'repo'),
  pr_number: must(bundle.inputData.pr_number, 'pr_number'),
  run_id: must(bundle.inputData.run_id, 'run_id'),
  head_sha: must(bundle.inputData.head_sha, 'head_sha'),
  workflow: must(bundle.inputData.workflow, 'workflow'),
  conclusion: must(bundle.inputData.conclusion, 'conclusion'),
  completed_at: must(bundle.inputData.completed_at, 'completed_at'),
  required_check_name: must(bundle.inputData.required_check_name, 'required_check_name'),
};

if (fields.trace_id !== traceId) throw new Error('FAIL_CLOSED: trace_id mismatch');

const canonical = [
  fields.schema,
  fields.trace_id,
  fields.repo,
  fields.pr_number,
  fields.run_id,
  fields.head_sha,
  fields.workflow,
  fields.conclusion,
  fields.completed_at,
  fields.required_check_name,
].join('|');

const digest = crypto.createHash('sha256').update(Buffer.from(canonical, 'utf8')).digest('hex');
const recomputed = `sha256:${digest}`;

if (recomputed !== providedHash) {
  throw new Error('FAIL_CLOSED: energy_hash mismatch (tamper or drift)');
}

return {
  trace_id: traceId,
  decision,
  operator: bundle.inputData.user_name,
  operator_id: bundle.inputData.user_id,
  timestamp: new Date().toISOString(),
  integrity_check: providedHash,
  energy_hash_valid: true
};
```

## 7. GitHub Branch Protection

Configure branch protection to require:
- `ci`
- `zapier/human-collapse`

This makes the human decision a required merge gate.

## 8. Minimal GitHub Actions Emitter (A)

```yaml
- name: Emit CI telemetry to Zapier (A)
  if: always()
  env:
    ZAPIER_CI_WEBHOOK_URL: ${{ secrets.ZAPIER_CI_WEBHOOK_URL }}
  run: |
    CONCLUSION="${{ job.status }}"
    payload=$(cat <<'JSON'
    {
      "schema":"ci.telemetry.v1",
      "trace_id":"ci__${{ github.repository }}__pr${{ github.event.pull_request.number }}__run${{ github.run_id }}",
      "repo":"${{ github.repository }}",
      "pr_number":${{ github.event.pull_request.number }},
      "run_id":"${{ github.run_id }}",
      "head_sha":"${{ github.sha }}",
      "workflow":"${{ github.workflow }}",
      "conclusion":"'"$CONCLUSION"'",
      "completed_at":"$(date -u +"%Y-%m-%dT%H:%M:%SZ")",
      "required_check_name":"ci"
    }
JSON
    )
    curl -sS -X POST -H "Content-Type: application/json" -d "$payload" "$ZAPIER_CI_WEBHOOK_URL"
```

## 9. Storage Options (A → B Canonical Field Lookup)

Choose one:
- Airtable table keyed by `trace_id`
- SSOT ledger endpoint with indexed trace_id
- Lightweight KV store (Redis/S3) per trace_id

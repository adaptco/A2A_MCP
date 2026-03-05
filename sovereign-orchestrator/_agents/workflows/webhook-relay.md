---
description: Test and send webhook payloads through the Echo relay
---

# Webhook Relay

## Send a Chat Trigger (OS-agnostic)

// turbo

1. Trigger from any terminal, browser, or chatbot:

```bash
curl -X POST \
  -H "Authorization: Bearer $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github+json" \
  https://api.github.com/repos/{owner}/{repo}/dispatches \
  -d '{
    "event_type": "chat-trigger",
    "client_payload": {
      "task_id": "T-chat-001",
      "to_agent": "Celine",
      "payload": {
        "prompt": "Build a login page with OAuth"
      }
    }
  }'
```

## Test Echo Relay Locally

// turbo

1. Create a test artifact:

```bash
cd sovereign-orchestrator
mkdir -p artifacts/T-test
echo "Test output from agent" > artifacts/T-test/output.txt
```

// turbo
2. Create a test receipt:

```bash
mkdir -p receipts
echo '{"task_id":"T-test","agent_card":"agents/runner.py","llm_target":"gemini","status":"completed","output_path":"artifacts/T-test/output.txt"}' > receipts/T-test.json
```

// turbo
3. Run Echo relay:

```bash
python agents/Echo/relay.py T-test
```

1. Check the relay receipt:

```bash
cat receipts/T-test-relay.json
```

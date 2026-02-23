# WhatsApp Auditor Pipeline Specification

## Overview
This module implements the auditing pipeline for WhatsApp message integrity and policy compliance. It is responsible for ingesting message events, verifying their signatures, recording them in a tamper-evident ledger, and checking against defined policy gates.

## Architecture

### 1. Ingestion Layer
- **Endpoint**: `/webhook/whatsapp`
- **Responsibility**: Receive raw payloads from WhatsApp Business API.
- **Validation**: Verify `X-Hub-Signature-256` header using the configured app secret.

### 2. Normalization
- **Model**: Convert raw JSON to `WhatsAppMessageEvent` schema.
- **Fields**:
  - `message_id`: Unique identifier.
  - `sender`: Phone number.
  - `content`: Encrypted or plain text body.
  - `timestamp`: Event time.
  - `metadata`: Raw payload for audit.

### 3. Ledger Recording
- **Component**: `LedgerService`
- **Action**: Append normalized event to the append-only log (e.g., SQLite or Postgres with hash chaining).
- **Integrity**: Calculate `prev_hash` linking.

### 4. Policy Verification (Gates)
- **Component**: `PolicyEngine`
- **Checks**:
  - **Rate Limiting**: Messages per user < X/min.
  - **Content Policy**: Keyword blocklist (if plaintext) or metadata analysis.
  - **Drift Detection**: Alert if message volume spikes > 2 sigma.

## Implementation Plan for Coding Agent

1.  **Scaffold Models**: Define Pydantic models for `WhatsAppMessageEvent`.
2.  **Implement Webhook**: Create FastAPI route for `/webhook/whatsapp`.
3.  **Implement Signature Verification**: Logic to HMAC-SHA256 hash the payload and compare with header.
4.  **Ledger Integration**: Connect to `core_orchestrator.ledger`.
5.  **Tests**:
    - Unit tests for signature verification (valid/invalid).
    - Integration test for full pipeline (webhook -> ledger).

## Production Deployment Considerations
- **Secrets Management**: `WHATSAPP_APP_SECRET` must be injected via env vars.
- **Concurrency**: Webhook handling should be async to avoid blocking.
- **Storage**: Ledger must use persistent storage (Volume or managed DB).

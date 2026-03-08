# Txtordr Intake Endpoint

This document captures the Txtordr intake surface, including its OpenAPI specification and a minimal TypeScript emitter for producing signed payloads.

## OpenAPI v3 Specification

```yaml
openapi: 3.0.3
info:
  title: Txtordr Intake API
  version: 1.0.0
  description: |
    Receives structured Txtordr payloads and routes them based on gesture and tone.
    Payloads must conform to the Txtordr v1 schema and include a valid HMAC signature.
paths:
  /txtordr/intake:
    post:
      summary: Submit a Txtordr payload
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: 'https://q.enterprises/schemas/txtordr.v1.json'
      responses:
        '202':
          description: Accepted and routed
          content:
            application/json:
              schema:
                type: object
                properties:
                  ok:
                    type: boolean
                  order_id:
                    type: string
        '400':
          description: Invalid payload or HMAC
        '409':
          description: Duplicate idempotency key
        '500':
          description: Internal error
      security:
        - hmacAuth: []
components:
  securitySchemes:
    hmacAuth:
      type: apiKey
      in: header
      name: X-Txtordr-HMAC
```

## Minimal TypeScript Client

```ts
import crypto from 'crypto';
import axios from 'axios';

const SECRET = process.env.TXTORDR_SECRET!;
const endpoint = 'https://your-cloud-function-url/txtordr/intake';

function signPayload(payload: object): string {
  const json = JSON.stringify(payload);
  return crypto.createHmac('sha256', SECRET).update(json).digest('base64');
}

async function emitOrder(payload: any) {
  const hmac = signPayload(payload);
  const headers = { 'X-Txtordr-HMAC': hmac };
  const res = await axios.post(endpoint, payload, { headers });
  return res.data;
}
```

Use the client to build higher-level choreography around Txtordr payloads while keeping signature handling centralized.

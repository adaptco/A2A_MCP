import crypto from 'node:crypto';
import axios, { AxiosRequestHeaders } from 'axios';

type TxtordrPayload = Record<string, unknown>;

const SECRET = process.env.TXTORDR_SECRET;
const ENDPOINT = process.env.TXTORDR_ENDPOINT ?? 'https://your-cloud-function-url/txtordr/intake';

if (!SECRET) {
  throw new Error('TXTORDR_SECRET environment variable must be defined');
}

function serializePayload(payload: TxtordrPayload): string {
  return JSON.stringify(payload);
}

export function signPayload(payload: TxtordrPayload): string {
  const json = serializePayload(payload);
  return crypto.createHmac('sha256', SECRET).update(json).digest('base64');
}

export async function emitOrder(payload: TxtordrPayload) {
  const hmac = signPayload(payload);
  const headers: AxiosRequestHeaders = { 'X-Txtordr-HMAC': hmac };
  const response = await axios.post(ENDPOINT, payload, { headers });
  return response.data;
}

const runtime = globalThis as unknown as {
  require?: { main?: unknown };
  module?: unknown;
};

if (runtime.require?.main === runtime.module) {
  const samplePayload: TxtordrPayload = {
    id: 'sample-order-001',
    gesture: 'Signal_Broadcast',
    tone: 'Shout',
  };

  emitOrder(samplePayload)
    .then((data) => {
      console.log('Order accepted:', data);
    })
    .catch((error: unknown) => {
      console.error('Failed to emit order:', error);
      process.exitCode = 1;
    });
}

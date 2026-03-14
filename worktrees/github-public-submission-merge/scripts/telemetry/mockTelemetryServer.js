#!/usr/bin/env node

const fs = require('fs');
const http = require('http');
const path = require('path');
const { URL } = require('url');
const WebSocket = require('ws');

const CAPSULE_ID = process.env.TELEMETRY_CAPSULE_ID || 'telemetry.mock.solF1.v1';
const SAMPLE_RATE_HZ = Number(process.env.TELEMETRY_SAMPLE_RATE_HZ || 30);
const AUTH_TOKEN = process.env.TELEMETRY_AUTH_TOKEN || 'demo';
const STREAM_PATH = process.env.TELEMETRY_STREAM_PATH || '/streams/telemetry/solF1/v1';
const PORT = Number(process.env.TELEMETRY_PORT || 8080);
const EVENT_SOURCE = process.env.TELEMETRY_EVENT_SOURCE || 'capsule.telemetry.render.v1.events_examples';
const CAPSULE_DIR = process.env.TELEMETRY_CAPSULE_DIR || path.resolve(__dirname, '../../capsules/telemetry');
const EVENT_FILE = process.env.TELEMETRY_EVENT_FILE || path.join(CAPSULE_DIR, `${EVENT_SOURCE}.jsonl`);

function loadEventsFromFile(filePath) {
  const payload = fs.readFileSync(filePath, 'utf8');
  const lines = payload.split(/\r?\n/).filter(Boolean);
  const events = lines.map((line, index) => {
    try {
      return JSON.parse(line);
    } catch (error) {
      throw new Error(`Unable to parse JSONL fixture at line ${index + 1}: ${error.message}`);
    }
  });

  if (!events.length) {
    throw new Error(`Event fixture at ${filePath} is empty.`);
  }

  return events;
}

function createHealthResponse() {
  return JSON.stringify({
    capsule_id: CAPSULE_ID,
    mode: 'SIMULATED',
    sample_rate_hz: SAMPLE_RATE_HZ,
    source: EVENT_SOURCE,
    loop: true,
    status: 'ACTIVE'
  });
}

function extractToken(request) {
  const url = new URL(request.url, `http://${request.headers.host}`);
  const queryToken = url.searchParams.get('token');
  if (queryToken) {
    return queryToken;
  }

  const header = request.headers['authorization'];
  if (!header) {
    return null;
  }

  const normalized = header.trim();
  if (normalized.toLowerCase().startsWith('bearer ')) {
    return normalized.slice(7);
  }
  if (normalized.toLowerCase().startsWith('token ')) {
    return normalized.slice(6);
  }
  return normalized;
}

let events = loadEventsFromFile(EVENT_FILE);
let frameIndex = 0;
let sequence = 0;

const server = http.createServer((req, res) => {
  if (req.url === '/healthz') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(createHealthResponse());
    return;
  }

  res.writeHead(404, { 'Content-Type': 'application/json' });
  res.end(JSON.stringify({ error: 'Not Found' }));
});

const wss = new WebSocket.Server({ noServer: true });

server.on('upgrade', (request, socket, head) => {
  const url = new URL(request.url, `http://${request.headers.host}`);

  if (url.pathname !== STREAM_PATH) {
    socket.write('HTTP/1.1 404 Not Found\r\n\r\n');
    socket.destroy();
    return;
  }

  const token = extractToken(request);
  if (token !== AUTH_TOKEN) {
    socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
    socket.destroy();
    return;
  }

  wss.handleUpgrade(request, socket, head, (ws) => {
    wss.emit('connection', ws, request);
  });
});

function broadcastEvent() {
  if (!wss.clients.size) {
    return;
  }

  const event = events[frameIndex];
  const envelope = {
    capsule_id: CAPSULE_ID,
    mode: 'SIMULATED',
    sample_rate_hz: SAMPLE_RATE_HZ,
    loop: true,
    status: 'ACTIVE',
    sequence: sequence++,
    emitted_at: new Date().toISOString(),
    event
  };

  for (const client of wss.clients) {
    if (client.readyState === WebSocket.OPEN) {
      client.send(JSON.stringify(envelope));
    }
  }

  frameIndex = (frameIndex + 1) % events.length;
}

wss.on('connection', (ws) => {
  ws.send(JSON.stringify({
    capsule_id: CAPSULE_ID,
    type: 'status',
    message: 'connected',
    sample_rate_hz: SAMPLE_RATE_HZ,
    mode: 'SIMULATED',
    loop: true
  }));

  ws.on('error', (error) => {
    console.error('WebSocket error:', error.message);
  });
});

const intervalMs = Math.round(1000 / SAMPLE_RATE_HZ);
const timer = setInterval(broadcastEvent, intervalMs);

fs.watch(EVENT_FILE, { persistent: false }, (eventType) => {
  if (eventType !== 'change') {
    return;
  }

  try {
    events = loadEventsFromFile(EVENT_FILE);
    frameIndex = 0;
    console.log(`Reloaded telemetry fixture from ${EVENT_FILE}`);
  } catch (error) {
    console.error('Failed to reload events fixture:', error.message);
  }
});

server.listen(PORT, () => {
  console.log(`Mock telemetry server for ${CAPSULE_ID} listening on ws://localhost:${PORT}${STREAM_PATH}`);
});

process.on('SIGINT', () => {
  clearInterval(timer);
  wss.close();
  server.close(() => process.exit(0));
});

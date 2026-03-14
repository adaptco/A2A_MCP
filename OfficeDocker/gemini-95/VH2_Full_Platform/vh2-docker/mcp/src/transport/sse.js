/**
 * VH2 MCP — SseServerTransport
 *
 * Implements MCP over HTTP + Server-Sent Events:
 *
 *   Client → POST /message   { jsonrpc, id, method, params }
 *   Server → GET  /sse       text/event-stream
 *             data: { jsonrpc, id, result } \n\n
 *             data: { jsonrpc, id, error  } \n\n
 *
 * Why SSE (not WebSocket):
 *   - Half-duplex is fine: MCP client sends requests via POST, server
 *     streams responses back over the persistent SSE connection.
 *   - SSE works through HTTP/1.1 proxies and load balancers with zero
 *     config; WebSocket upgrade requires explicit proxy support.
 *   - Native browser EventSource API works without polyfills.
 *
 * Interface is identical to StdioServerTransport:
 *   transport.on(method, handler)  — register a method handler
 *   transport.start()              — open HTTP server, begin accepting
 *   transport.close()              — close all connections + server
 *
 * Endpoints:
 *   GET  /sse      — establish SSE stream (one per client)
 *   POST /message  — send JSON-RPC request/notification
 *   GET  /health   — liveness (returns 200 {ok:true})
 *
 * Environment variables:
 *   MCP_HTTP_PORT  — port to listen on (default: 3002)
 *   MCP_HTTP_HOST  — bind address   (default: 127.0.0.1)
 *   MCP_CORS_ORIGIN— CORS origin    (default: *)
 */

import { createServer }    from 'http'
import { EventEmitter }    from 'events'

// ── SSE client registry ──────────────────────────────────────────────────────
// Maps session-id → { res, keepalive }
// A session is created when a client opens GET /sse.
// POST /message targets a session via ?sessionId= query param.

let _sessionSeq = 0
function newSessionId() { return `vh2-mcp-${++_sessionSeq}-${Date.now()}` }

export class SseServerTransport extends EventEmitter {
  #handlers = new Map()
  #clients  = new Map()   // sessionId → { res, keepaliveTimer }
  #server   = null
  #started  = false

  #port   = parseInt(process.env.MCP_HTTP_PORT  ?? '3002', 10)
  #host   = process.env.MCP_HTTP_HOST            ?? '127.0.0.1'
  #cors   = process.env.MCP_CORS_ORIGIN          ?? '*'

  /** Register a method handler (same API as StdioServerTransport) */
  on(method, handler) {
    // EventEmitter's .on() is for internal events ('close', etc.)
    // Method handlers use the #handlers map.
    if (typeof handler === 'function' && !['close', 'error', 'listening'].includes(method)) {
      this.#handlers.set(method, handler)
      return this
    }
    return super.on(method, handler)
  }

  // ── JSON-RPC dispatch (shared with StdioServerTransport logic) ─────────────
  async #dispatch(raw, sendFn) {
    let msg
    try { msg = JSON.parse(raw) } catch {
      sendFn({ jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } })
      return
    }

    const { jsonrpc, id, method, params } = msg
    if (jsonrpc !== '2.0' || typeof method !== 'string') {
      sendFn({ jsonrpc: '2.0', id: id ?? null, error: { code: -32600, message: 'Invalid Request' } })
      return
    }

    const isNotification = id === undefined || id === null
    const handler = this.#handlers.get(method)

    if (!handler) {
      if (!isNotification) {
        sendFn({ jsonrpc: '2.0', id, error: { code: -32601, message: `Method not found: ${method}` } })
      }
      return
    }

    try {
      const result = await handler(params ?? {})
      if (!isNotification) sendFn({ jsonrpc: '2.0', id, result })
    } catch (err) {
      if (!isNotification) {
        sendFn({ jsonrpc: '2.0', id, error: { code: -32603, message: err?.message ?? 'Internal error' } })
      }
    }
  }

  // ── HTTP request handler ───────────────────────────────────────────────────
  #handleRequest(req, res) {
    const url    = new URL(req.url, `http://${req.headers.host ?? 'localhost'}`)
    const path   = url.pathname
    const method = req.method.toUpperCase()

    // CORS preflight
    res.setHeader('Access-Control-Allow-Origin',  this.#cors)
    res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
    if (method === 'OPTIONS') { res.writeHead(204); res.end(); return }

    // ── GET /health ──────────────────────────────────────────────────────
    if (method === 'GET' && path === '/health') {
      res.writeHead(200, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({
        ok: true,
        transport: 'sse',
        clients: this.#clients.size,
        port: this.#port,
      }))
      return
    }

    // ── GET /sse — open SSE stream ───────────────────────────────────────
    if (method === 'GET' && path === '/sse') {
      const sessionId = newSessionId()

      res.writeHead(200, {
        'Content-Type':  'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection':    'keep-alive',
        'X-Session-Id':  sessionId,
      })

      // Send session ID as first event so client knows where to POST
      res.write(`event: session\ndata: ${JSON.stringify({ sessionId })}\n\n`)

      // Keepalive comment every 20s (prevents proxy timeouts)
      const keepaliveTimer = setInterval(() => {
        res.write(': keepalive\n\n')
      }, 20_000)

      this.#clients.set(sessionId, { res, keepaliveTimer })
      process.stderr.write(`[vh2-mcp/sse] client connected: ${sessionId} (${this.#clients.size} total)\n`)

      req.on('close', () => {
        clearInterval(keepaliveTimer)
        this.#clients.delete(sessionId)
        process.stderr.write(`[vh2-mcp/sse] client disconnected: ${sessionId} (${this.#clients.size} remaining)\n`)
      })
      return
    }

    // ── POST /message — receive JSON-RPC, respond over SSE ──────────────
    if (method === 'POST' && path === '/message') {
      const sessionId = url.searchParams.get('sessionId')
      const client    = this.#clients.get(sessionId)

      if (!sessionId || !client) {
        res.writeHead(400, { 'Content-Type': 'application/json' })
        res.end(JSON.stringify({
          error: sessionId
            ? `Unknown sessionId: ${sessionId}`
            : 'Missing ?sessionId= query param. Open GET /sse first to obtain a session ID.',
        }))
        return
      }

      // Acknowledge POST immediately (body processed async)
      res.writeHead(202, { 'Content-Type': 'application/json' })
      res.end(JSON.stringify({ accepted: true, sessionId }))

      // Read body
      const chunks = []
      req.on('data', c => chunks.push(c))
      req.on('end', () => {
        const body = Buffer.concat(chunks).toString('utf8').trim()
        if (!body) return

        // sendFn writes the JSON-RPC response as an SSE event on the client's stream
        const sendFn = (msg) => {
          if (client.res.writableEnded) return
          client.res.write(`data: ${JSON.stringify(msg)}\n\n`)
        }

        this.#dispatch(body, sendFn).catch(err => {
          process.stderr.write(`[vh2-mcp/sse] dispatch error: ${err?.message}\n`)
        })
      })
      return
    }

    // ── 404 ──────────────────────────────────────────────────────────────
    res.writeHead(404, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify({
      error: 'Not found',
      available: ['GET /sse', 'POST /message?sessionId=<id>', 'GET /health'],
    }))
  }

  /** Start the HTTP server */
  start() {
    if (this.#started) throw new Error('SseServerTransport already started')
    this.#started = true

    this.#server = createServer((req, res) => this.#handleRequest(req, res))

    this.#server.listen(this.#port, this.#host, () => {
      process.stderr.write(
        `[vh2-mcp/sse] HTTP server listening on http://${this.#host}:${this.#port}\n` +
        `[vh2-mcp/sse] Endpoints: GET /sse  POST /message?sessionId=  GET /health\n`
      )
      this.emit('listening', { port: this.#port, host: this.#host })
    })

    this.#server.on('error', err => {
      process.stderr.write(`[vh2-mcp/sse] server error: ${err.message}\n`)
      this.emit('error', err)
    })

    return this
  }

  /** Close all SSE connections and the HTTP server */
  close() {
    for (const [id, { res, keepaliveTimer }] of this.#clients) {
      clearInterval(keepaliveTimer)
      res.end()
      this.#clients.delete(id)
    }
    this.#server?.close(() => {
      process.stderr.write('[vh2-mcp/sse] HTTP server closed\n')
      this.emit('close')
    })
  }
}

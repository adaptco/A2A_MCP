/**
 * VH2 MCP — StdioServerTransport
 *
 * Implements the MCP stdio transport layer:
 *   - Reads newline-delimited JSON-RPC 2.0 messages from stdin
 *   - Writes newline-delimited JSON-RPC 2.0 responses to stdout
 *   - All server logs go to stderr (never stdout — that's the MCP channel)
 *
 * Wire format (identical to @modelcontextprotocol/sdk StdioServerTransport):
 *   → { "jsonrpc": "2.0", "id": N, "method": "...", "params": {...} }\n
 *   ← { "jsonrpc": "2.0", "id": N, "result": {...} }\n
 *   ← { "jsonrpc": "2.0", "id": N, "error": { "code": N, "message": "..." } }\n
 */

import { createInterface } from 'readline'

export class StdioServerTransport {
  #handlers = new Map()   // method → async handler(params) → result
  #rl       = null
  #started  = false

  /** Register a method handler */
  on(method, handler) {
    this.#handlers.set(method, handler)
    return this
  }

  /** Write a JSON-RPC response (or notification) to stdout */
  #send(msg) {
    process.stdout.write(JSON.stringify(msg) + '\n')
  }

  /** Dispatch one parsed JSON-RPC message */
  async #dispatch(raw) {
    let msg
    try {
      msg = JSON.parse(raw)
    } catch {
      this.#send({
        jsonrpc: '2.0', id: null,
        error: { code: -32700, message: 'Parse error' },
      })
      return
    }

    const { jsonrpc, id, method, params } = msg

    // Validate envelope
    if (jsonrpc !== '2.0' || typeof method !== 'string') {
      this.#send({
        jsonrpc: '2.0', id: id ?? null,
        error: { code: -32600, message: 'Invalid Request' },
      })
      return
    }

    // Notifications (no id) — fire and forget
    const isNotification = id === undefined || id === null

    const handler = this.#handlers.get(method)
    if (!handler) {
      if (!isNotification) {
        this.#send({
          jsonrpc: '2.0', id,
          error: { code: -32601, message: `Method not found: ${method}` },
        })
      }
      return
    }

    try {
      const result = await handler(params ?? {})
      if (!isNotification) {
        this.#send({ jsonrpc: '2.0', id, result })
      }
    } catch (err) {
      if (!isNotification) {
        this.#send({
          jsonrpc: '2.0', id,
          error: { code: -32603, message: err?.message ?? 'Internal error' },
        })
      }
    }
  }

  /** Start listening on stdin */
  start() {
    if (this.#started) throw new Error('Transport already started')
    this.#started = true

    this.#rl = createInterface({
      input:   process.stdin,
      terminal: false,
    })

    this.#rl.on('line', line => {
      const trimmed = line.trim()
      if (trimmed) this.#dispatch(trimmed)
    })

    this.#rl.on('close', () => {
      process.stderr.write('[vh2-mcp] stdin closed — shutting down\n')
      process.exit(0)
    })

    process.stderr.write('[vh2-mcp] StdioServerTransport started\n')
    return this
  }

  /** Graceful shutdown */
  close() {
    this.#rl?.close()
  }
}

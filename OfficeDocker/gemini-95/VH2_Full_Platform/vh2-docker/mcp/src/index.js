#!/usr/bin/env node
/**
 * VH2 MCP SERVER — Entry Point
 *
 * Transports (MCP_TRANSPORT env var):
 *   stdio  — JSON-RPC 2.0 over stdin/stdout (default; IDE/CLI use)
 *   sse    — JSON-RPC 2.0 over HTTP+SSE on MCP_HTTP_PORT (default: 3002)
 *   both   — stdio + SSE simultaneously
 *
 * Usage:
 *   node src/index.js                        # stdio
 *   MCP_TRANSPORT=sse node src/index.js      # SSE on :3002
 *   MCP_TRANSPORT=both node src/index.js     # both
 *
 * SSE client flow:
 *   1. GET  http://localhost:3002/sse          → receive {sessionId}
 *   2. POST http://localhost:3002/message?sessionId=<id>  { jsonrpc body }
 *   3. Responses arrive as SSE data: events on the stream
 *
 * VS Code mcp.json (SSE):
 *   { "servers": { "vh2": { "type": "sse", "url": "http://localhost:3002/sse" } } }
 *
 * Claude Desktop (stdio):
 *   { "mcpServers": { "vh2": { "command": "node", "args": ["src/index.js"] } } }
 */

import { StdioServerTransport } from './transport/stdio.js'
import { SseServerTransport }   from './transport/sse.js'
import { McpServer }            from './server.js'

import { validateTool  } from './tools/validate.js'
import { ackermannTool } from './tools/ackermann.js'
import { kpiTool       } from './tools/kpi.js'
import { witnessTool   } from './tools/witness.js'

import { specResource       } from './resources/spec.js'
import { invariantsResource } from './resources/invariants.js'
import { deployResource     } from './resources/deploy.js'

function registerAll(server) {
  return server
    .tool(validateTool)
    .tool(ackermannTool)
    .tool(kpiTool)
    .tool(witnessTool)
    .resource(specResource)
    .resource(invariantsResource)
    .resource(deployResource)
}

const mode = (process.env.MCP_TRANSPORT ?? 'stdio').toLowerCase()

if (!['stdio', 'sse', 'both'].includes(mode)) {
  process.stderr.write(`[vh2-mcp] Unknown MCP_TRANSPORT="${mode}". Use stdio|sse|both.\n`)
  process.exit(1)
}

if (mode === 'stdio' || mode === 'both') {
  registerAll(new McpServer(new StdioServerTransport())).start()
  process.stderr.write('[vh2-mcp] StdioServerTransport started\n')
}

if (mode === 'sse' || mode === 'both') {
  registerAll(new McpServer(new SseServerTransport())).start()
}

process.stderr.write(`[vh2-mcp] Ready — 4 tools, 3 resources, transport=${mode}\n`)

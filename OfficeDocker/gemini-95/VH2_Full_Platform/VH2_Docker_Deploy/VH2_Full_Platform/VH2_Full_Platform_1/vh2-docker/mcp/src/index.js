#!/usr/bin/env node
/**
 * VH2 MCP SERVER — Entry Point
 *
 * Transport : StdioServerTransport (JSON-RPC 2.0 over stdin/stdout)
 * Protocol  : MCP 2024-11-05
 * Tools     : vh2_validate · vh2_ackermann · vh2_kpi · vh2_witness
 * Resources : vh2://spec  · vh2://invariants · vh2://deploy
 *
 * Usage:
 *   node src/index.js                  # run standalone
 *   echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | node src/index.js
 *
 * Claude Desktop claude_desktop_config.json:
 *   {
 *     "mcpServers": {
 *       "vh2": {
 *         "command": "node",
 *         "args": ["/absolute/path/to/vh2-mcp/src/index.js"]
 *       }
 *     }
 *   }
 *
 * VS Code / Cursor mcp.json:
 *   {
 *     "servers": {
 *       "vh2": { "type": "stdio", "command": "node", "args": ["src/index.js"] }
 *     }
 *   }
 */

import { StdioServerTransport } from './transport/stdio.js'
import { McpServer }            from './server.js'

// ── Tools ──────────────────────────────────────────────────────────────────
import { validateTool  } from './tools/validate.js'
import { ackermannTool } from './tools/ackermann.js'
import { kpiTool       } from './tools/kpi.js'
import { witnessTool   } from './tools/witness.js'

// ── Resources ──────────────────────────────────────────────────────────────
import { specResource       } from './resources/spec.js'
import { invariantsResource } from './resources/invariants.js'
import { deployResource     } from './resources/deploy.js'

// ── Wire up ────────────────────────────────────────────────────────────────
const transport = new StdioServerTransport()
const server    = new McpServer(transport)

server
  // Tools — typed schemas (validate, ackermann, kpi) + passthrough stub (witness)
  .tool(validateTool)
  .tool(ackermannTool)
  .tool(kpiTool)
  .tool(witnessTool)

  // Resources — existing src/resources/ mapped to MCP URIs
  .resource(specResource)
  .resource(invariantsResource)
  .resource(deployResource)

  .start()

process.stderr.write(
  `[vh2-mcp] Server ready — 4 tools, 3 resources, StdioServerTransport\n`
)

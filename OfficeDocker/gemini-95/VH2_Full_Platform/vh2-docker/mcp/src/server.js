/**
 * VH2 MCP — Server Registry
 *
 * Wires tools and resources into the transport by registering
 * all standard MCP lifecycle methods:
 *
 *   initialize          — handshake, return server capabilities
 *   notifications/initialized — client ACK (notification, no reply)
 *   tools/list          — enumerate registered tools + inputSchema
 *   tools/call          — dispatch to tool handler
 *   resources/list      — enumerate registered resources
 *   resources/read      — dispatch to resource reader
 *   ping                — keepalive
 */

export class McpServer {
  #transport  = null
  #tools      = new Map()   // name → { description, inputSchema, handler }
  #resources  = new Map()   // uri  → { name, description, mimeType, read }

  #name       = 'vh2-mcp-server'
  #version    = '1.0.0'
  #mcpVersion = '2024-11-05'

  constructor(transport) {
    this.#transport = transport
  }

  /** Register a tool */
  tool(def) {
    const { name, description, inputSchema, handler } = def
    if (!name || !handler) throw new Error('tool() requires name and handler')
    this.#tools.set(name, { name, description, inputSchema, handler })
    process.stderr.write(`[vh2-mcp] tool registered: ${name}\n`)
    return this
  }

  /** Register a resource */
  resource(def) {
    const { uri, name, description, mimeType, read } = def
    if (!uri || !read) throw new Error('resource() requires uri and read')
    this.#resources.set(uri, { uri, name, description, mimeType, read })
    process.stderr.write(`[vh2-mcp] resource registered: ${uri}\n`)
    return this
  }

  /** Bind all method handlers to the transport and start */
  start() {
    const t = this.#transport

    // ── LIFECYCLE ────────────────────────────────────────────────────────
    t.on('initialize', (params) => {
      // Echo client's requested protocol version if we support it
      const protocolVersion = params?.protocolVersion ?? this.#mcpVersion
      return {
        protocolVersion,
        serverInfo: { name: this.#name, version: this.#version },
        capabilities: {
          tools:     { listChanged: false },
          resources: { subscribe: false, listChanged: false },
        },
      }
    })

    // Notification — no response
    t.on('notifications/initialized', () => {
      process.stderr.write('[vh2-mcp] client initialized ACK received\n')
      return undefined
    })

    // ── TOOLS ────────────────────────────────────────────────────────────
    t.on('tools/list', () => {
      return {
        tools: [...this.#tools.values()].map(({ name, description, inputSchema }) => ({
          name,
          description,
          inputSchema: inputSchema ?? { type: 'object', additionalProperties: true },
        })),
      }
    })

    t.on('tools/call', async (params) => {
      const { name, arguments: args = {} } = params ?? {}
      const tool = this.#tools.get(name)
      if (!tool) {
        return {
          content: [{ type: 'text', text: `Unknown tool: ${name}` }],
          isError: true,
        }
      }
      try {
        return await tool.handler(args)
      } catch (err) {
        return {
          content: [{ type: 'text', text: `Tool error: ${err?.message ?? err}` }],
          isError: true,
        }
      }
    })

    // ── RESOURCES ────────────────────────────────────────────────────────
    t.on('resources/list', () => {
      return {
        resources: [...this.#resources.values()].map(({ uri, name, description, mimeType }) => ({
          uri, name, description, mimeType,
        })),
      }
    })

    t.on('resources/read', async (params) => {
      const { uri } = params ?? {}
      const resource = this.#resources.get(uri)
      if (!resource) {
        throw Object.assign(new Error(`Resource not found: ${uri}`), { code: -32002 })
      }
      return await resource.read()
    })

    // ── KEEPALIVE ────────────────────────────────────────────────────────
    t.on('ping', () => ({}))

    t.start()
    return this
  }
}

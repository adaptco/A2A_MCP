# ═══════════════════════════════════════════════════════════════════════
# VH2 MCP SERVER — Dockerfile
#
# Zero external npm dependencies (pure Node.js built-ins only).
# Supports stdio and SSE transports via MCP_TRANSPORT env var.
#
# Build:
#   docker build -t vh2-mcp:latest ./mcp
#
# Run (stdio — for IDE sidecar use):
#   docker run --rm -i vh2-mcp:latest
#
# Run (SSE — for browser/remote clients):
#   docker run --rm -p 3002:3002 -e MCP_TRANSPORT=sse vh2-mcp:latest
#
# Run (both transports):
#   docker run --rm -i -p 3002:3002 -e MCP_TRANSPORT=both vh2-mcp:latest
# ═══════════════════════════════════════════════════════════════════════

FROM node:20-alpine AS production

# Non-root user (uid 1001 matches backend convention)
RUN addgroup -g 1001 -S mcp && adduser -u 1001 -S mcp -G mcp

WORKDIR /app

# Copy package.json first (no npm install needed — zero external deps)
COPY package.json ./

# Copy source (no node_modules to install)
COPY src/ ./src/

# Ownership
RUN chown -R mcp:mcp /app

USER mcp

# Transport: stdio (default) | sse | both
ENV MCP_TRANSPORT=stdio
# SSE bind address and port (only used when MCP_TRANSPORT=sse|both)
ENV MCP_HTTP_HOST=0.0.0.0
ENV MCP_HTTP_PORT=3002
ENV MCP_CORS_ORIGIN=*

# Expose SSE port (ignored when MCP_TRANSPORT=stdio)
EXPOSE 3002

# Healthcheck: only meaningful in SSE/both mode
# In stdio mode this will fail — that's expected (stdio servers have no HTTP health)
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
  CMD [ "sh", "-c", \
    "if [ \"$MCP_TRANSPORT\" = \"stdio\" ]; then exit 0; fi; \
     wget -qO- http://localhost:${MCP_HTTP_PORT}/health | grep -q '\"ok\":true'" ]

# Logs to stderr (MCP protocol uses stdout exclusively for stdio transport)
CMD ["node", "src/index.js"]

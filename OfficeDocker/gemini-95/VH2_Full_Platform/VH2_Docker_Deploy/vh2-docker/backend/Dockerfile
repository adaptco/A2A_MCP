# ═══════════════════════════════════════════════════════════════════════
# VH2 BACKEND SOCKET — Dockerfile (Production Optimized)
# Multi-stage: deps → test → production
# Node 20 LTS, non-root, fail-closed health check
# ═══════════════════════════════════════════════════════════════════════

# ── STAGE 1: dependency install (cached separately) ─────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
# Copy only package.json first (package-lock.json optional)
COPY package.json ./
RUN npm install --omit=dev && npm cache clean --force

# ── STAGE 2: test runner (fail-closed — build halts if tests fail) ──────
FROM node:20-alpine AS test
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN node tests/validator.test.js

# ── STAGE 3: production image ───────────────────────────────────────────
FROM node:20-alpine AS production

# Security: non-root user (create before COPY to preserve ownership)
RUN addgroup -g 1001 -S vh2 && adduser -u 1001 -S vh2 -G vh2

WORKDIR /app

# Copy pruned deps from stage 1 (with correct ownership)
COPY --chown=vh2:vh2 --from=deps /app/node_modules ./node_modules

# Copy source files (tests excluded, with ownership)
COPY --chown=vh2:vh2 server.js ./

# Metadata (OCI-compliant)
LABEL org.opencontainers.image.title="VH2 Backend Socket"
LABEL org.opencontainers.image.description="VH2 Sovereign Suspension — Validation API"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.vendor="VH2"

# Environment (before USER for consistency)
ENV NODE_ENV=production \
    PORT=3001 \
    HOST=0.0.0.0 \
    NODE_OPTIONS="--disable-warnings"

# Non-root user
USER vh2

EXPOSE 3001

# Health check (uses wget, lighter than inline Node.js)
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3001/health || exit 1

CMD ["node", "server.js"]

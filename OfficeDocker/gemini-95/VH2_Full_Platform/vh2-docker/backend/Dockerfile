# ═══════════════════════════════════════════════════════════════════════
# VH2 BACKEND SOCKET — Dockerfile
# Multi-stage: deps → build → production
# Node 20 LTS, non-root, fail-closed health check
# ═══════════════════════════════════════════════════════════════════════

# ── STAGE 1: dependency install ─────────────────────────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm ci --omit=dev && npm cache clean --force

# ── STAGE 2: test runner (fail-closed — build halts if tests fail) ──────
FROM node:20-alpine AS test
WORKDIR /app
COPY package.json ./
RUN npm ci
COPY . .
RUN node tests/validator.test.js

# ── STAGE 3: production image ───────────────────────────────────────────
FROM node:20-alpine AS production

# Security: non-root user
RUN addgroup -g 1001 -S vh2 && adduser -u 1001 -S vh2 -G vh2

WORKDIR /app

# Copy pruned deps from stage 1
COPY --from=deps /app/node_modules ./node_modules

# Copy source (tests excluded)
COPY server.js ./

# Metadata
LABEL org.opencontainers.image.title="VH2 Backend Socket"
LABEL org.opencontainers.image.description="VH2 Sovereign Suspension — Validation API"
LABEL org.opencontainers.image.version="1.0.0"

# Non-root
USER vh2

EXPOSE 3001

# Health check (liveness probe matches K8s / Docker Compose)
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3001/health || exit 1

ENV NODE_ENV=production \
    PORT=3001 \
    HOST=0.0.0.0

CMD ["node", "server.js"]

# ═══════════════════════════════════════════════════════════════════════
# VH2 BACKEND SOCKET — Dockerfile (Optimized for Production)
# Multi-stage: deps → build → production
# Node 20 LTS, non-root, fail-closed health check, cache optimized
# ═══════════════════════════════════════════════════════════════════════

# ── STAGE 1: dependency install (cached separately) ──────────────────────
FROM node:20-alpine AS deps
WORKDIR /app
# Copy only package files first for better cache reuse
COPY package.json ./
RUN npm install --omit=dev && npm cache clean --force

# ── STAGE 2: test runner (fail-closed — build halts if tests fail) ──────
FROM node:20-alpine AS test
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN node tests/validator.test.js

# ── STAGE 3: production image (slim base) ───────────────────────────────
FROM node:20-alpine

# Security: non-root user (create before COPY to preserve ownership)
RUN addgroup -g 1001 -S vh2 && adduser -u 1001 -S vh2 -G vh2

WORKDIR /app

# Copy pruned deps from stage 1 with correct ownership
COPY --from=deps --chown=vh2:vh2 /app/node_modules ./node_modules

# Copy source (tests excluded) with correct ownership
COPY --chown=vh2:vh2 server.js ./

# Metadata (OCI-compliant labels)
LABEL org.opencontainers.image.title="VH2 Backend Socket"
LABEL org.opencontainers.image.description="VH2 Sovereign Suspension — Validation API"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.vendor="VH2"

# Environment variables (production-hardened)
ENV NODE_ENV=production \
    NODE_OPTIONS="--disable-warnings" \
    PORT=3001 \
    HOST=0.0.0.0

# Non-root user (must be before EXPOSE/HEALTHCHECK)
USER vh2

EXPOSE 3001

# Health check (liveness probe matches K8s / Docker Compose)
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
  CMD wget -qO- http://localhost:3001/health || exit 1

CMD ["node", "server.js"]

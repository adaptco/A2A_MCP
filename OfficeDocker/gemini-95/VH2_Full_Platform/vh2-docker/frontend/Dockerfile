# ═══════════════════════════════════════════════════════════════════════
# VH2 FRONTEND SOCKET — Dockerfile
# Serves: plugin demo, vehicle sim, unit test runner
# ═══════════════════════════════════════════════════════════════════════

FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm ci --omit=dev && npm cache clean --force

FROM node:20-alpine AS production

RUN addgroup -g 1001 -S vh2 && adduser -u 1001 -S vh2 -G vh2
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY server.js vh2-plugin.js ./
COPY public/ ./public/

LABEL org.opencontainers.image.title="VH2 Frontend Socket"
LABEL org.opencontainers.image.version="1.0.0"

USER vh2
EXPOSE 3000

HEALTHCHECK --interval=20s --timeout=5s --start-period=8s --retries=3 \
  CMD wget -qO- http://localhost:3000/ || exit 1

ENV NODE_ENV=production \
    PORT=3000 \
    HOST=0.0.0.0

CMD ["node", "server.js"]

# ==========================================
# 1. Builder Stage
# ==========================================
FROM python:3.11-slim AS builder

# Set pip environment variables for secure, deterministic installation
ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=100

WORKDIR /build

# Copy ONLY the runtime requirements (excluding pytest, pylint, etc.)
COPY requirements.txt .

# Install dependencies into a local user directory for easy transfer
RUN pip install --user --compile --no-warn-script-location -r requirements.txt

# ==========================================
# 2. Runtime Stage
# ==========================================
FROM python:3.11-slim AS runtime

# 7. Add metadata labels
LABEL maintainer=\"AdaptCo <team@adaptco.com>\" \
      version=\"1.0.0\" \
      description=\"Production Engine for The Qube / MoE-Router\"

# 3. Enhanced Environment Variables & 8. No .local path (installing globally in builder or copying securely)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=random \
    PYTHONPATH="/app" \
    PATH=\"/home/appuser/.local/bin:$PATH\"

WORKDIR /app

# 2. Improved User & Group Setup / 5. Security Hardening
# Create non-root user with explicit IDs and disable shell login
RUN groupadd -g 5678 appgroup && \
    useradd -u 5678 -g appgroup -s /sbin/nologin -m appuser

# 4. Reduce layer count / Secure copies
# Copy installed python packages from the builder stage
COPY --from=builder --chown=appuser:appgroup /root/.local /home/appuser/.local

# Copy application source code
COPY --chown=appuser:appgroup . .

# Enforce non-root execution
USER appuser

# 6. Improved HEALTHCHECK
# Waits 15s before starting checks, runs a real liveness check against the app
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request, sys; \
    urllib.request.urlopen('http://127.0.0.1:8000/health').read()" || exit 1

# 7. CMD Optimization
# Runs python unbuffered so logs stream instantly to your container orchestrator
CMD [\"python\", \"-u\", \"orchestrator/main.py\"]

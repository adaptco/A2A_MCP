# ── Build stage ──────────────────────────────────────────────
FROM python:3.12-slim-bookworm AS builder

WORKDIR /build

# Patch vulnerabilities in the builder
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Install dependencies into an isolated prefix
COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime stage ────────────────────────────────────────────
FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="a2a-mcp"
LABEL org.opencontainers.image.description="A2A MCP Orchestrator — Multi-Agent Pipeline"

WORKDIR /app

# Patch vulnerabilities in runtime
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

# Copy only installed packages from builder (smaller image)
COPY --from=builder /install /usr/local

# Copy project source
COPY . .

# Ensure app is in python path
ENV PYTHONPATH=/app

# Expose the port FastAPI runs on
EXPOSE 8000

# Health check for Docker / load balancer probes
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Command to run the orchestrator
CMD ["python", "orchestrator/main.py"]

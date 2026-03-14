# 1. Architecture (brief)
- **Clients** → **Relay (Ingress / Service)** → **Provider Adapter** → **Upstream provider (Anthropic / OpenAI / Gemini)**.  
- **Sidecars / Filters**: rate limiter (Envoy or Kong), validator webhook (image provenance, invariants), logging/analytics (DuckDB or ELK), metrics (Prometheus).  
- **Control plane**: Git repo (Helm chart + ArgoCD Application) → ArgoCD enforces drift and safe deletion semantics.  
- **Observability**: Prometheus metrics + Grafana dashboard for validations/sec, violations, consensus score, test pass rate.

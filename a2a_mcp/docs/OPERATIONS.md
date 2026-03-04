# Operational Readiness & Runbooks

## Service Level Objectives (SLOs)

| Metric | Target | Window |
|--------|--------|--------|
| Availability (API) | 99.9% | 30 days |
| /tools/call P95 Latency | < 500ms | 24 hours |
| /orchestrate P95 Latency | < 30s | 24 hours |
| Auth Failure Rate | < 1% | 1 hour |

## Runbooks

### 1. Incident Triage
1. Check Prometheus metrics for elevated error rates (`a2a_orchestrator_requests_total`).
2. Inspect structured logs for `request_id` or `correlation_id` associated with failures.
3. Verify OIDC connectivity to GitHub Actions.

### 2. Database Backup & Restore
**Backup:**
```bash
docker exec a2a-postgres pg_dump -U postgres mcp_db > backup_$(date +%Y%m%d).sql
```
**Restore:**
```bash
cat backup.sql | docker exec -i a2a-postgres psql -U postgres mcp_db
```

### 3. Secret Rotation
1. Generate new `RBAC_SECRET`.
2. Update `.env` or deployment secrets.
3. Restart `rbac-gateway` and `orchestrator` services.
4. Verify onboarding still works via `deploy-stack` smoke test.

### 4. Rollback Procedure
1. Identify the last stable commit SHA.
2. Re-tag Docker images with the stable SHA.
3. Update `docker-compose.unified.yml` or Helm values.
4. Run `docker compose up -d` to deploy previous version.

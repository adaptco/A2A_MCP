# GKE Release Deployment Runbook

## Scope
This runbook defines the production release flow for the GKE workload deployed via Helm. It includes pre-release checks, release execution, rollback operations, and incident follow-up requirements.

## Baseline release and revision commands
Set these environment variables before executing release actions:

```bash
export NAMESPACE=prod
export RELEASE_NAME=fieldengine-cfo-mcp
export CHART_PATH=ops/helm/fieldengine-cfo-mcp
```

Inspect revision state and deployed chart:

```bash
helm -n "$NAMESPACE" list --filter "$RELEASE_NAME"
helm -n "$NAMESPACE" history "$RELEASE_NAME"
helm -n "$NAMESPACE" status "$RELEASE_NAME"
```

Deploy/upgrade the target revision:

```bash
helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
  -n "$NAMESPACE" \
  --atomic \
  --wait \
  --timeout 10m
```

## Rollback execution plan for production responders

### 1) Immediate rollback trigger thresholds
Start rollback decisioning immediately when any threshold below is met for **5 consecutive minutes** after production cutover:

- **Error spike**: HTTP 5xx error rate exceeds **2%** overall or exceeds **1%** on any tier-1 endpoint.
- **Auth failures**: 401/403 rate rises to **>3x** the pre-release baseline or exceeds **5%** of auth-protected requests.
- **Latency regression**: p95 latency regresses by **>30%** vs. pre-release baseline (or p99 by **>20%**) for tier-1 API routes.

If two thresholds breach simultaneously at any time, skip mitigation experiments and proceed directly to rollback.

### 2) Safe rollback commands (Helm history/revision driven)
1. Identify last known good revision from Helm history:

   ```bash
   helm -n "$NAMESPACE" history "$RELEASE_NAME"
   ```

2. Roll back explicitly to that revision number (example: revision 42):

   ```bash
   helm -n "$NAMESPACE" rollback "$RELEASE_NAME" 42 --wait --timeout 10m
   ```

3. Confirm the active revision and deployment health:

   ```bash
   helm -n "$NAMESPACE" status "$RELEASE_NAME"
   helm -n "$NAMESPACE" history "$RELEASE_NAME"
   kubectl -n "$NAMESPACE" get pods -l app.kubernetes.io/instance="$RELEASE_NAME"
   ```

4. If pods fail readiness after rollback, capture diagnostics before further changes:

   ```bash
   kubectl -n "$NAMESPACE" describe deploy -l app.kubernetes.io/instance="$RELEASE_NAME"
   kubectl -n "$NAMESPACE" logs deploy/"$RELEASE_NAME" --since=15m
   ```

### 3) Post-rollback validation checklist
Complete all checks before incident closure:

- [ ] Error rate returned to pre-release baseline (or under SLO burn threshold) for 15 minutes.
- [ ] 401/403 auth-failure ratio normalized to baseline band.
- [ ] p95/p99 latency returned to pre-release steady-state range.
- [ ] Critical user journeys (login, token exchange, core API write path) verified by synthetic checks.
- [ ] No CrashLoopBackOff/NotReady pods in target namespace.
- [ ] Alert noise reduced to expected baseline; paging route acknowledged.
- [ ] Incident timeline contains deploy revision, rollback revision, and UTC timestamps.

### 4) Data and telemetry retention during incident window
Preserve observability data for failed requests during the release incident window:

- Retain request/response metadata, trace IDs, and error envelopes for **minimum 30 days**.
- Preserve structured logs tied to affected release and rollback revisions (include Helm revision numbers in incident notes).
- Keep distributed traces and span-level timing for both failed and successful retries to support causal analysis.
- Do not purge auth failure logs generated during rollback window; they are required for replay and abuse analysis.
- Mark the incident window in dashboards to prevent accidental downsampling/exclusion during postmortem analysis.

### 5) Post-release hardening backlog (mandatory follow-up)
Open backlog items immediately after stabilization:

1. **Stricter schema validation**
   - Enforce strict request/response schema validation at ingress and service boundaries.
   - Add contract tests for incompatible field additions/removals.
2. **Replay-attack protections**
   - Introduce nonce/jti replay detection, bounded token lifetimes, and idempotency-key policies for sensitive routes.
   - Alert on duplicate token identifiers and suspicious reuse patterns.
3. **Token rotation cadence**
   - Define and enforce rotation cadence for signing/encryption keys (for example every 30 days, emergency rotation on compromise indicators).
   - Validate dual-key overlap windows and rollback-safe key distribution process.

Each backlog item must include owner, due date, and measurable acceptance criteria in the incident follow-up ticket.

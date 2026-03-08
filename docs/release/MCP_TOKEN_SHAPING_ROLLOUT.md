# MCP Token-Shaping Controlled Rollout Runbook

This runbook rolls out token-shaping changes in controlled phases while preserving fast rollback.

## Preconditions

- Helm release name and namespace are known for both staging and production.
- The new image is published and immutable (tag + digest).
- The chart supports:
  - base values: `values.yaml`
  - environment override: `values-staging.yaml`
  - canary controls for embedded-avatar traffic (for example: weight, header, or route match).
- MCP gateway exposes `POST /mcp` and `POST /tools/call` for smoke testing.

---

## Phase 1 — Staging deploy + smoke tests (`/mcp`, `/tools/call`)

### 1. Capture current staging state (for rollback)

```bash
export RELEASE_NAME=<helm_release>
export NAMESPACE_STAGING=<staging_namespace>
export CHART_PATH=<chart_path>

helm -n "$NAMESPACE_STAGING" history "$RELEASE_NAME"
helm -n "$NAMESPACE_STAGING" status "$RELEASE_NAME"
helm -n "$NAMESPACE_STAGING" get values "$RELEASE_NAME" -o yaml > /tmp/${RELEASE_NAME}-staging-pre.yaml
```

### 2. Deploy to staging with merged values

```bash
export IMAGE_TAG=<new_image_tag>

helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
  -n "$NAMESPACE_STAGING" \
  -f values.yaml \
  -f values-staging.yaml \
  --set image.tag="$IMAGE_TAG" \
  --wait --timeout 10m
```

### 3. Record exact revision + image tag

```bash
STAGING_REVISION=$(helm -n "$NAMESPACE_STAGING" history "$RELEASE_NAME" -o json | python - <<'PY'
import json,sys
hist=json.load(sys.stdin)
print(hist[-1]["revision"])
PY
)

echo "staging_revision=$STAGING_REVISION"
echo "image_tag=$IMAGE_TAG"

kubectl -n "$NAMESPACE_STAGING" get deploy -l app.kubernetes.io/instance="$RELEASE_NAME" \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.template.spec.containers[*].image}{"\n"}{end}'
```

### 4. Run auth + shaping smoke tests

Use the helper script:

```bash
BASE_URL=https://<staging_mcp_host> \
AUTH_TOKEN=<staging_bearer_token> \
scripts/smoke_mcp_endpoints.sh
```

Smoke test checks:
- Unauthorized requests to `/mcp` and `/tools/call` are rejected.
- Authorized `/mcp` request succeeds.
- Authorized `/tools/call` request succeeds.
- Authorized request with large token payload is accepted and returns a structured response (basic shaping sanity).

---

## Phase 2 — Production canary (embedded-avatar subset)

### 1. Capture production pre-state

```bash
export NAMESPACE_PROD=<prod_namespace>

helm -n "$NAMESPACE_PROD" history "$RELEASE_NAME"
helm -n "$NAMESPACE_PROD" get values "$RELEASE_NAME" -o yaml > /tmp/${RELEASE_NAME}-prod-pre.yaml
```

### 2. Enable canary for a small embedded-avatar cohort

Route only a small portion of embedded-avatar traffic (example: 5%).

```bash
export CANARY_WEIGHT=5

helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
  -n "$NAMESPACE_PROD" \
  -f values.yaml \
  --set image.tag="$IMAGE_TAG" \
  --set tokenShaping.enabled=true \
  --set tokenShaping.canary.enabled=true \
  --set tokenShaping.canary.trafficClass=embedded-avatar \
  --set tokenShaping.canary.weight="$CANARY_WEIGHT" \
  --wait --timeout 10m
```

### 3. Record production canary revision + image

```bash
PROD_CANARY_REVISION=$(helm -n "$NAMESPACE_PROD" history "$RELEASE_NAME" -o json | python - <<'PY'
import json,sys
hist=json.load(sys.stdin)
print(hist[-1]["revision"])
PY
)

echo "prod_canary_revision=$PROD_CANARY_REVISION"
echo "image_tag=$IMAGE_TAG"
```

---

## Phase 3 — Compare canary vs baseline

Observe canary and baseline in parallel for a fixed window (recommended: 60–120 min minimum, or one full peak cycle).

Track these metrics by cohort (`embedded-avatar-canary` vs `embedded-avatar-baseline`):

1. **Reject rate**
   - `reject_rate = rejected_requests / total_requests`
2. **Latency**
   - p50, p95, p99 for `/mcp` and `/tools/call`
3. **Avatar response quality**
   - existing quality score (Judge/DMN score, thumbs-up ratio, or equivalent acceptance KPI)

### Suggested decision gates

- Reject-rate regression: **<= +0.5 percentage points** vs baseline.
- p95 latency regression: **<= +10%** vs baseline.
- Avatar quality: **no statistically significant drop** (or <= 1% relative drop if significance testing unavailable).
- No Sev-1/Sev-2 incidents attributable to token-shaping path.

If any gate fails, rollback immediately:

```bash
helm -n "$NAMESPACE_PROD" rollback "$RELEASE_NAME" <previous_good_revision> --wait --timeout 10m
```

---

## Phase 4 — Promote to 100%

Promote only after canary SLOs pass for the full observation window.

```bash
helm upgrade --install "$RELEASE_NAME" "$CHART_PATH" \
  -n "$NAMESPACE_PROD" \
  -f values.yaml \
  --set image.tag="$IMAGE_TAG" \
  --set tokenShaping.enabled=true \
  --set tokenShaping.canary.enabled=false \
  --set tokenShaping.rolloutPercent=100 \
  --wait --timeout 10m
```

Capture final revision/image:

```bash
PROD_FULL_REVISION=$(helm -n "$NAMESPACE_PROD" history "$RELEASE_NAME" -o json | python - <<'PY'
import json,sys
hist=json.load(sys.stdin)
print(hist[-1]["revision"])
PY
)

echo "prod_full_revision=$PROD_FULL_REVISION"
echo "image_tag=$IMAGE_TAG"
```

---

## Rollback ledger (copy into release ticket)

Record this table during rollout:

| Environment | Helm revision | Image tag | Timestamp (UTC) | Operator |
|---|---:|---|---|---|
| staging (pre) | `<rev>` | `<tag>` | `<ts>` | `<name>` |
| staging (post) | `<rev>` | `<tag>` | `<ts>` | `<name>` |
| prod (pre) | `<rev>` | `<tag>` | `<ts>` | `<name>` |
| prod (canary) | `<rev>` | `<tag>` | `<ts>` | `<name>` |
| prod (100%) | `<rev>` | `<tag>` | `<ts>` | `<name>` |

Keeping exact revisions and tags ensures one-command rollback to a known-good state.

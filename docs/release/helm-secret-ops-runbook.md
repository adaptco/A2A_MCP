# A2A MCP Helm Secret Ops Runbook (Production)

This runbook covers secret creation and rotation for token-related settings used by the Helm chart.

## Secret keys and env var mapping

The production Secret in namespace `a2a-mcp-prod` must include these keys:

- `OIDC_AUDIENCE`
- `OIDC_ISSUER`
- `OIDC_JWKS_URI`
- `AVATAR_TOKEN_SIGNING_KEY`
- `AVATAR_TOKEN_VALIDATION_KEY`

These names must match container env var references exactly.

## Create the production secret (first deploy)

```bash
kubectl create namespace a2a-mcp-prod --dry-run=client -o yaml | kubectl apply -f -

kubectl -n a2a-mcp-prod create secret generic a2a-mcp-prod-secrets \
  --from-literal=OIDC_AUDIENCE='<prod-oidc-audience>' \
  --from-literal=OIDC_ISSUER='<prod-oidc-issuer>' \
  --from-literal=OIDC_JWKS_URI='<prod-oidc-jwks-uri>' \
  --from-literal=AVATAR_TOKEN_SIGNING_KEY='<'"$(openssl rand -base64 64)"'>' \
  --from-literal=AVATAR_TOKEN_VALIDATION_KEY='<'"$(openssl rand -base64 64)"'>'
```

> Tip: for asymmetric keys, replace literals with `--from-file` and store private/public keys in separate files.

## Rotate token secrets

1. Create new key material.
2. Update the Kubernetes Secret.
3. Restart workloads so env vars are reloaded.

```bash
kubectl -n a2a-mcp-prod create secret generic a2a-mcp-prod-secrets \
  --dry-run=client -o yaml \
  --from-literal=OIDC_AUDIENCE='<prod-oidc-audience>' \
  --from-literal=OIDC_ISSUER='<prod-oidc-issuer>' \
  --from-literal=OIDC_JWKS_URI='<prod-oidc-jwks-uri>' \
  --from-literal=AVATAR_TOKEN_SIGNING_KEY='<'"$(openssl rand -base64 64)"'>' \
  --from-literal=AVATAR_TOKEN_VALIDATION_KEY='<'"$(openssl rand -base64 64)"'>' \
  | kubectl apply -f -

kubectl -n a2a-mcp-prod rollout restart deployment/a2a-mcp
kubectl -n a2a-mcp-prod rollout status deployment/a2a-mcp --timeout=120s
```

## Preflight checklist before Helm upgrade

Run these checks before upgrading with `values-prod.yaml`:

```bash
# 1) Namespace exists
kubectl get namespace a2a-mcp-prod

# 2) Secret exists
kubectl -n a2a-mcp-prod get secret a2a-mcp-prod-secrets

# 3) Required keys exist (no values printed)
kubectl -n a2a-mcp-prod get secret a2a-mcp-prod-secrets -o json \
  | jq -e '.data | has("OIDC_AUDIENCE") and has("OIDC_ISSUER") and has("OIDC_JWKS_URI") and has("AVATAR_TOKEN_SIGNING_KEY") and has("AVATAR_TOKEN_VALIDATION_KEY")'

# 4) Dry-run render and verify secret is not templated from plaintext prod values
helm template a2a-mcp ./deploy/helm/a2a-mcp -f ./deploy/helm/a2a-mcp/values-prod.yaml \
  | rg -n 'kind: Secret|OIDC_AUDIENCE|AVATAR_TOKEN_SIGNING_KEY'

# 5) Perform upgrade
helm upgrade --install a2a-mcp ./deploy/helm/a2a-mcp \
  -n a2a-mcp-prod \
  -f ./deploy/helm/a2a-mcp/values-prod.yaml
```

Expected result for step 4 in production: no rendered Secret payload from Helm because `secrets.create=false`; app reads from pre-created `a2a-mcp-prod-secrets`.

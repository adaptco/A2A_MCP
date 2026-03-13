# deploy.sh integration patch (mechanical)

## Add conventions

- `RECEIPT_DIR=receipts/deploy`
- `POLICY_FILE=policies/deploy_policy.v1.json` (create minimal JSON now)

## Flow updates

### Before any apply run

1. Verify required deployment files exist (`compose`, `dockerfile`, `.env`, `policy`).
2. Compute hashes via receipt emitter preflight.

### Dry-run behavior

- Do **not** run `docker compose up`.
- Emit receipt only with:
  - `mode=dry_run`
  - `status=success`
  - `exit_code=0`
  - summary such as `receipt-only`

### Apply behavior

- Execute deployment (`docker compose up` or current apply flow).
- Emit receipt with:
  - `mode=apply`
  - `status` derived from deployment result
  - `exit_code` from deployment command
  - bounded summary

## Example wiring snippet

```bash
MODE="${MODE:-apply}"   # apply | dry_run
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="${RECEIPT_DIR}/deploy_${TS}.json"

python3 deploy-governance/scripts/emit_deployment_receipt.py \
  --compose docker-compose.prod.yaml \
  --dockerfile-bot Dockerfile.bot \
  --env .env.prod \
  --policy "${POLICY_FILE}" \
  --service vh2-orchestrator \
  --service deploy-bot \
  --mode "${MODE}" \
  --out "${OUT}" \
  --status success \
  --exit-code 0 \
  --summary "receipt-only"
```

For `apply`, rerun/update the emitter call after deploy completion using actual status and exit code.

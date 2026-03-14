# deploy.sh integration patch (receipt v1)

## Add conventions

- `RECEIPT_DIR=receipts/deploy`
- `POLICY_FILE=policies/deploy_policy.v1.json`

## Control flow requirements

1. Verify required input files exist before deploy flow.
2. In `--dry-run` mode:
   - do **not** run `docker compose up`
   - emit receipt only with `mode=dry_run`, `status=success`, `exit_code=0`
3. In `apply` mode:
   - run deployment normally
   - emit receipt after execution using real status and exit code

## Wiring example

```bash
MODE="${MODE:-apply}"   # or dry_run
TS="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="receipts/deploy/deploy_${TS}.json"

python3 deploy-governance/scripts/emit_deployment_receipt.py \
  --compose docker-compose.prod.yaml \
  --dockerfile-bot Dockerfile.bot \
  --env .env.prod \
  --policy policies/deploy_policy.v1.json \
  --service vh2-orchestrator \
  --service deploy-bot \
  --mode "$MODE" \
  --out "$OUT" \
  --status "success" \
  --exit-code 0 \
  --summary "receipt-only"
```

Then in `apply` mode, update `--status/--exit-code/--summary` from deploy result.

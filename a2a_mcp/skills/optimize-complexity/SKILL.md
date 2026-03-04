---
name: optimize-complexity
description: Optimize tool complexity distribution from orchestration checkpoint CSV files using deterministic embedding similarity and complexity relabeling. Use when you need to analyze token bottlenecks, rebalance tool complexity, generate optimization reports, or prepare CI-ready complexity artifacts from a single checkpoint CSV.
---

# Optimize Complexity

Run a deterministic complexity redistribution workflow on one orchestration checkpoint CSV.

## Do this

1. Validate the input contract from `references/input_schema.md`.
2. Run `scripts/optimize_complexity.py` with explicit flags.
3. Review `complexity_optimization_report.json` and (optionally) `.md`.
4. Use `references/ci_template.md` to wire the same command in CI.

## Command

```bash
python skills/optimize-complexity/scripts/optimize_complexity.py \
  --checkpoint-path /path/to/orchestration_checkpoint.csv \
  --out-dir /path/to/output \
  --target-complexity 0.5 \
  --target-input-count 0.5 \
  --report-format both
```

## Outputs

- `optimized_orchestration_checkpoint.csv`
- `complexity_optimization_report.json`
- `complexity_optimization_report.md` (if `--report-format md|both`)

## Read only when needed

- Input fields and examples: `references/input_schema.md`
- Scoring + relabel thresholds: `references/scoring_method.md`
- Reusable CI job snippet: `references/ci_template.md`

## Notes

- Keep outputs deterministic by using the same input and flags.
- Treat exit code `2` as contract/input failure.
- Treat exit code `3` as runtime processing failure.
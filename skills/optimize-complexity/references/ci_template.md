# CI Template

Use this job template to generate optimization artifacts from a checkpoint CSV.

```yaml
name: Complexity Optimization

on:
  workflow_dispatch:
  pull_request:
    paths:
      - "orchestration_checkpoint.csv"
      - "skills/optimize-complexity/**"

jobs:
  optimize-complexity:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Run complexity optimizer
        run: |
          python skills/optimize-complexity/scripts/optimize_complexity.py \
            --checkpoint-path orchestration_checkpoint.csv \
            --out-dir build/complexity \
            --report-format both

      - name: Upload artifacts
        uses: actions/upload-artifact@v4
        with:
          name: complexity-optimization
          path: build/complexity
```

## Notes

- Keep this as a reusable template reference in v1.
- Do not mutate existing workflows automatically.
- Treat exit code `2` as a contract gate failure.
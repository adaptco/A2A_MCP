#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REQUIRED_COLUMNS = [
    "agent",
    "tool_name",
    "crud_category",
    "complexity",
    "input_parameter_count",
]

CATEGORICAL_COMPLEXITY = {
    "simple": 0.2,
    "moderate": 0.5,
    "complex": 0.8,
}

RELABEL_BINS = (
    (0.0, 0.35, "simple"),
    (0.35, 0.70, "moderate"),
    (0.70, 1.01, "complex"),
)


@dataclass(frozen=True)
class OptimizationConfig:
    checkpoint_path: Path
    out_dir: Path
    target_complexity: float
    target_input_count: float
    report_format: str


def _parse_args(argv: list[str]) -> OptimizationConfig:
    parser = argparse.ArgumentParser(description="Optimize complexity distribution for one checkpoint CSV.")
    parser.add_argument("--checkpoint-path", required=True, help="Path to orchestration_checkpoint.csv")
    parser.add_argument("--out-dir", default="", help="Directory for output artifacts (default: input directory)")
    parser.add_argument(
        "--target-complexity",
        type=float,
        default=0.5,
        help="Target normalized complexity in [0,1]",
    )
    parser.add_argument(
        "--target-input-count",
        type=float,
        default=0.5,
        help="Target normalized input parameter count in [0,1]",
    )
    parser.add_argument(
        "--report-format",
        choices=["json", "md", "both"],
        default="both",
        help="Report output format",
    )

    args = parser.parse_args(argv)

    checkpoint_path = Path(args.checkpoint_path).expanduser().resolve()
    out_dir = Path(args.out_dir).expanduser().resolve() if args.out_dir else checkpoint_path.parent

    if not (0.0 <= args.target_complexity <= 1.0):
        raise ValueError("--target-complexity must be in [0,1]")
    if not (0.0 <= args.target_input_count <= 1.0):
        raise ValueError("--target-input-count must be in [0,1]")

    return OptimizationConfig(
        checkpoint_path=checkpoint_path,
        out_dir=out_dir,
        target_complexity=args.target_complexity,
        target_input_count=args.target_input_count,
        report_format=args.report_format,
    )


def _stable_agent_encoding(agent_name: str) -> float:
    digest = hashlib.sha256(agent_name.strip().lower().encode("utf-8")).hexdigest()
    # 0..65535 -> normalize to [0,1]
    return int(digest[:4], 16) / 65535.0


def _parse_complexity(raw: str, row_index: int, warnings: list[str]) -> float:
    token = (raw or "").strip().lower()
    if token in CATEGORICAL_COMPLEXITY:
        return CATEGORICAL_COMPLEXITY[token]

    try:
        value = float(token)
    except ValueError as exc:
        raise ValueError(
            f"row {row_index}: complexity '{raw}' is not numeric and not one of {sorted(CATEGORICAL_COMPLEXITY)}"
        ) from exc

    if value > 1.0:
        warnings.append(
            f"row {row_index}: complexity '{raw}' assumed 0-100 scale and normalized by /100"
        )
        value = value / 100.0

    if value < 0.0 or value > 1.0:
        raise ValueError(f"row {row_index}: normalized complexity must be within [0,1], got {value}")

    return value


def _parse_input_count(raw: str, row_index: int) -> int:
    token = (raw or "").strip()
    if token == "":
        raise ValueError(f"row {row_index}: input_parameter_count is empty")
    try:
        value = int(token)
    except ValueError as exc:
        raise ValueError(f"row {row_index}: input_parameter_count '{raw}' is not an integer") from exc
    if value < 0:
        raise ValueError(f"row {row_index}: input_parameter_count must be >= 0")
    return value


def _normalize_input_count(count: int, max_count: int) -> float:
    if max_count <= 0:
        return 0.0
    return count / max_count


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(a, a))


def _cosine_similarity(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    denom = _norm(a) * _norm(b)
    if denom == 0:
        return 0.0
    return _dot(a, b) / denom


def _label_from_score(score: float) -> str:
    for lower, upper, label in RELABEL_BINS:
        if lower <= score < upper:
            return label
    return "complex"


def _validate_headers(headers: list[str] | None) -> None:
    if not headers:
        raise ValueError("CSV is missing a header row")
    missing = [col for col in REQUIRED_COLUMNS if col not in headers]
    if missing:
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")


def _read_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ValueError(f"checkpoint file does not exist: {path}")
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        _validate_headers(reader.fieldnames)
        rows = list(reader)
    if not rows:
        raise ValueError("CSV contains no data rows")
    return rows


def _build_report_markdown(report: dict[str, Any]) -> str:
    before = report["distribution_before"]
    after = report["distribution_after"]
    relabel = report["relabel_counts"]
    warnings = report["warnings"]

    lines = [
        "# Complexity Optimization Report",
        "",
        f"- run_id: `{report['run_id']}`",
        f"- source_file: `{report['source_file']}`",
        f"- record_count: {report['record_count']}",
        f"- avg_similarity_before: {report['avg_similarity_before']:.6f}",
        f"- avg_similarity_after: {report['avg_similarity_after']:.6f}",
        "",
        "## Distribution Before",
        f"- simple: {before.get('simple', 0)}",
        f"- moderate: {before.get('moderate', 0)}",
        f"- complex: {before.get('complex', 0)}",
        "",
        "## Distribution After",
        f"- simple: {after.get('simple', 0)}",
        f"- moderate: {after.get('moderate', 0)}",
        f"- complex: {after.get('complex', 0)}",
        "",
        "## Relabel Counts",
        f"- changed: {relabel.get('changed', 0)}",
        f"- unchanged: {relabel.get('unchanged', 0)}",
        "",
        "## Warnings",
    ]

    if warnings:
        lines.extend([f"- {item}" for item in warnings])
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def optimize(config: OptimizationConfig) -> tuple[Path, Path | None, Path | None]:
    warnings: list[str] = []
    rows = _read_rows(config.checkpoint_path)

    parsed_rows: list[dict[str, Any]] = []
    max_input_count = 0
    for idx, row in enumerate(rows, start=2):
        complexity_value = _parse_complexity(row.get("complexity", ""), idx, warnings)
        input_count = _parse_input_count(row.get("input_parameter_count", ""), idx)
        max_input_count = max(max_input_count, input_count)

        current_label = _label_from_score(complexity_value)
        parsed_rows.append(
            {
                **row,
                "_complexity_value": complexity_value,
                "_input_count": input_count,
                "_current_label": current_label,
            }
        )

    target_vector = (0.5, config.target_complexity, config.target_input_count)
    score_before_total = 0.0
    score_after_total = 0.0

    for row in parsed_rows:
        encoded_agent = _stable_agent_encoding(str(row.get("agent", "")))
        normalized_input = _normalize_input_count(int(row["_input_count"]), max_input_count)

        source_vector = (encoded_agent, float(row["_complexity_value"]), normalized_input)
        before = _cosine_similarity(source_vector, target_vector)
        row["_similarity_before"] = before
        score_before_total += before

        optimized_score = 0.5 * float(row["_complexity_value"]) + 0.5 * before
        optimized_score = min(1.0, max(0.0, optimized_score))
        optimized_label = _label_from_score(optimized_score)

        optimized_vector = (encoded_agent, optimized_score, normalized_input)
        after = _cosine_similarity(optimized_vector, target_vector)
        row["_similarity_after"] = after
        score_after_total += after

        row["optimized_complexity"] = optimized_label
        row["optimized_complexity_score"] = f"{optimized_score:.6f}"

    before_dist = Counter(str(r["_current_label"]) for r in parsed_rows)
    after_dist = Counter(str(r["optimized_complexity"]) for r in parsed_rows)

    changed = sum(1 for r in parsed_rows if r["_current_label"] != r["optimized_complexity"])
    unchanged = len(parsed_rows) - changed

    config.out_dir.mkdir(parents=True, exist_ok=True)

    output_csv = config.out_dir / "optimized_orchestration_checkpoint.csv"
    output_json = config.out_dir / "complexity_optimization_report.json"
    output_md = config.out_dir / "complexity_optimization_report.md"

    out_fields = list(rows[0].keys()) + [
        "optimized_complexity",
        "optimized_complexity_score",
        "similarity_before",
        "similarity_after",
    ]

    with output_csv.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        for row in parsed_rows:
            out = {k: row.get(k, "") for k in rows[0].keys()}
            out["optimized_complexity"] = row["optimized_complexity"]
            out["optimized_complexity_score"] = row["optimized_complexity_score"]
            out["similarity_before"] = f"{float(row['_similarity_before']):.6f}"
            out["similarity_after"] = f"{float(row['_similarity_after']):.6f}"
            writer.writerow(out)

    report: dict[str, Any] = {
        "run_id": hashlib.sha256(
            f"{config.checkpoint_path}:{config.target_complexity}:{config.target_input_count}".encode("utf-8")
        ).hexdigest()[:16],
        "source_file": str(config.checkpoint_path),
        "record_count": len(parsed_rows),
        "distribution_before": {
            "simple": before_dist.get("simple", 0),
            "moderate": before_dist.get("moderate", 0),
            "complex": before_dist.get("complex", 0),
        },
        "distribution_after": {
            "simple": after_dist.get("simple", 0),
            "moderate": after_dist.get("moderate", 0),
            "complex": after_dist.get("complex", 0),
        },
        "relabel_counts": {
            "changed": changed,
            "unchanged": unchanged,
        },
        "avg_similarity_before": score_before_total / len(parsed_rows),
        "avg_similarity_after": score_after_total / len(parsed_rows),
        "warnings": warnings,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    json_path: Path | None = None
    md_path: Path | None = None

    if config.report_format in {"json", "both"}:
        json_path = output_json
        json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if config.report_format in {"md", "both"}:
        md_path = output_md
        md_path.write_text(_build_report_markdown(report), encoding="utf-8")

    return output_csv, json_path, md_path


def main(argv: list[str]) -> int:
    try:
        config = _parse_args(argv)
        csv_path, json_path, md_path = optimize(config)
    except ValueError as exc:
        print(f"validation error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # pragma: no cover
        print(f"runtime error: {exc}", file=sys.stderr)
        return 3

    print(f"wrote: {csv_path}")
    if json_path:
        print(f"wrote: {json_path}")
    if md_path:
        print(f"wrote: {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
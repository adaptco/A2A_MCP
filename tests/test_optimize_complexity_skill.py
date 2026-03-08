from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "skills" / "optimize-complexity" / "scripts" / "optimize_complexity.py"
SAMPLE = REPO_ROOT / "skills" / "optimize-complexity" / "assets" / "sample_orchestration_checkpoint.csv"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def test_valid_csv_produces_expected_outputs(tmp_path: Path) -> None:
    result = _run("--checkpoint-path", str(SAMPLE), "--out-dir", str(tmp_path), "--report-format", "both")
    assert result.returncode == 0, result.stderr

    assert (tmp_path / "optimized_orchestration_checkpoint.csv").exists()
    assert (tmp_path / "complexity_optimization_report.json").exists()
    assert (tmp_path / "complexity_optimization_report.md").exists()


def test_missing_required_column_returns_exit_code_2(tmp_path: Path) -> None:
    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text(
        "agent,tool_name,crud_category,complexity\nA,t,read,moderate\n",
        encoding="utf-8",
    )

    result = _run("--checkpoint-path", str(bad_csv), "--out-dir", str(tmp_path), "--report-format", "json")
    assert result.returncode == 2
    assert "missing required columns" in result.stderr


def test_categorical_and_numeric_complexity_are_supported(tmp_path: Path) -> None:
    mixed_csv = tmp_path / "mixed.csv"
    mixed_csv.write_text(
        "agent,tool_name,crud_category,complexity,input_parameter_count\n"
        "A,t1,read,simple,1\n"
        "B,t2,update,0.72,3\n"
        "C,t3,create,85,2\n",
        encoding="utf-8",
    )

    result = _run("--checkpoint-path", str(mixed_csv), "--out-dir", str(tmp_path), "--report-format", "json")
    assert result.returncode == 0, result.stderr

    report = json.loads((tmp_path / "complexity_optimization_report.json").read_text(encoding="utf-8"))
    assert report["record_count"] == 3
    assert report["warnings"]


def test_deterministic_replay_same_input_same_outputs(tmp_path: Path) -> None:
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"
    out1.mkdir()
    out2.mkdir()

    r1 = _run("--checkpoint-path", str(SAMPLE), "--out-dir", str(out1), "--report-format", "json")
    r2 = _run("--checkpoint-path", str(SAMPLE), "--out-dir", str(out2), "--report-format", "json")

    assert r1.returncode == 0, r1.stderr
    assert r2.returncode == 0, r2.stderr

    csv1 = (out1 / "optimized_orchestration_checkpoint.csv").read_text(encoding="utf-8")
    csv2 = (out2 / "optimized_orchestration_checkpoint.csv").read_text(encoding="utf-8")
    assert csv1 == csv2

    rep1 = json.loads((out1 / "complexity_optimization_report.json").read_text(encoding="utf-8"))
    rep2 = json.loads((out2 / "complexity_optimization_report.json").read_text(encoding="utf-8"))

    for key in (
        "record_count",
        "distribution_before",
        "distribution_after",
        "relabel_counts",
        "avg_similarity_before",
        "avg_similarity_after",
        "warnings",
    ):
        assert rep1[key] == rep2[key]


def test_empty_csv_returns_exit_code_2(tmp_path: Path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text(
        "agent,tool_name,crud_category,complexity,input_parameter_count\n",
        encoding="utf-8",
    )

    result = _run("--checkpoint-path", str(empty), "--out-dir", str(tmp_path), "--report-format", "json")
    assert result.returncode == 2
    assert "no data rows" in result.stderr


def test_report_contains_required_top_level_keys(tmp_path: Path) -> None:
    result = _run("--checkpoint-path", str(SAMPLE), "--out-dir", str(tmp_path), "--report-format", "json")
    assert result.returncode == 0, result.stderr

    report = json.loads((tmp_path / "complexity_optimization_report.json").read_text(encoding="utf-8"))
    required = {
        "run_id",
        "source_file",
        "record_count",
        "distribution_before",
        "distribution_after",
        "relabel_counts",
        "avg_similarity_before",
        "avg_similarity_after",
        "warnings",
        "generated_at",
    }
    assert required.issubset(report)


def test_optimized_csv_has_expected_columns(tmp_path: Path) -> None:
    result = _run("--checkpoint-path", str(SAMPLE), "--out-dir", str(tmp_path), "--report-format", "json")
    assert result.returncode == 0, result.stderr

    out_csv = tmp_path / "optimized_orchestration_checkpoint.csv"
    with out_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames is not None
        for col in (
            "optimized_complexity",
            "optimized_complexity_score",
            "similarity_before",
            "similarity_after",
        ):
            assert col in reader.fieldnames
from __future__ import annotations

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from core_orchestrator.visualizations import (
    generate_default_visualization,
    simulate_coherence_gate_response,
)


def test_simulation_recovers_stability_under_one_second():
    series = simulate_coherence_gate_response()

    # Ensure the spike was registered.
    assert pytest.approx(series.b_factor[0], rel=1e-3) == 0.5

    stabilization = series.stabilization_time()
    assert stabilization is not None, "Coherence Gate never reached the stability floor"
    assert stabilization <= 0.78 * 1.2

    assert min(series.delta_v) < series.lyapunov_floor
    assert any(series.gate_active)


def test_rendering_produces_png(tmp_path: Path):
    pytest.importorskip("matplotlib.pyplot")

    output = generate_default_visualization(tmp_path / "coherence_gate.png")
    assert output.exists()
    assert output.stat().st_size > 0


def test_series_serialises_to_json():
    series = simulate_coherence_gate_response(sample_rate=50)
    payload = series.as_dict()

    # round-trip serialisation sanity check
    json_payload = json.dumps(payload)
    restored = json.loads(json_payload)
    assert len(restored["time"]) == len(series.time)
    assert restored["epsilon"] == pytest.approx(series.epsilon)

"""Utilities for generating the Lyapunov constraint graph of the Coherence Gate."""
from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence


@dataclass
class CoherenceGateSeries:
    """Time series describing the Coherence Gate response."""

    time: List[float]
    b_factor: List[float]
    delta_v: List[float]
    gate_active: List[bool]
    epsilon: float
    lyapunov_floor: float

    def stabilization_time(self, floor: float = 0.98) -> float | None:
        """Return the earliest timestamp where stability is re-established."""

        for timestamp, delta_v, b_val in zip(self.time, self.delta_v, self.b_factor):
            if delta_v <= -self.epsilon and b_val >= floor:
                return timestamp
        return None

    def as_dict(self) -> dict:
        """Return a JSON-serialisable representation of the series."""

        return {
            "time": list(self.time),
            "b_factor": list(self.b_factor),
            "delta_v": list(self.delta_v),
            "gate_active": list(self.gate_active),
            "epsilon": self.epsilon,
            "lyapunov_floor": self.lyapunov_floor,
        }


def _logistic_recovery(t: float, start: float, target: float, tau: float) -> float:
    """Logistic curve helper used to model the recovery of the B-factor."""

    progress = 1.0 - math.exp(-max(t, 0.0) / max(tau, 1e-9))
    return start + (target - start) * min(progress, 1.0)


def simulate_coherence_gate_response(
    *,
    spike_value: float = 0.5,
    target_value: float = 0.995,
    spike_duration: float = 0.05,
    total_duration: float = 2.5,
    recovery_time: float = 0.78,
    sample_rate: int = 200,
    epsilon: float = 0.02,
) -> CoherenceGateSeries:
    """Generate a Lyapunov series showcasing gate stabilisation."""

    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive")

    step = 1.0 / sample_rate
    samples = int(total_duration * sample_rate)
    times: List[float] = [round(i * step, 10) for i in range(samples + 1)]

    b_values: List[float] = []
    gate_active: List[bool] = []

    for timestamp in times:
        if timestamp <= spike_duration:
            b_val = spike_value
        else:
            recovery_elapsed = timestamp - spike_duration
            b_val = _logistic_recovery(
                recovery_elapsed,
                spike_value,
                target_value,
                recovery_time / 5.0,
            )
            # Add a gentle overshoot damped by the gate.
            overshoot = 0.003 * math.exp(-recovery_elapsed / (recovery_time / 2.5))
            b_val = min(1.0, b_val + overshoot)
        b_values.append(b_val)
        gate_active.append(b_val < target_value)

    v_values: List[float] = [0.5 * (1.0 - value) ** 2 for value in b_values]
    delta_v: List[float] = [0.0]
    for current, previous in zip(v_values[1:], v_values[:-1]):
        delta_v.append((current - previous) / step)

    lyapunov_floor = -epsilon

    # Mark periods where the gate is actively forcing the Lyapunov derivative
    # to remain below the stability threshold.
    enforced_delta_v: List[float] = []
    adjusted_gate_active: List[bool] = []
    for active, dv, b_val in zip(gate_active, delta_v, b_values):
        if active:
            enforced_delta = min(dv, lyapunov_floor - 0.01)
            enforced_delta_v.append(enforced_delta)
            adjusted_gate_active.append(True)
        else:
            enforced_delta_v.append(dv)
            adjusted_gate_active.append(dv > lyapunov_floor)

    gate_active = adjusted_gate_active
    delta_v = enforced_delta_v

    return CoherenceGateSeries(
        time=times,
        b_factor=b_values,
        delta_v=delta_v,
        gate_active=gate_active,
        epsilon=epsilon,
        lyapunov_floor=lyapunov_floor,
    )


def render_lyapunov_constraint_graph(
    series: CoherenceGateSeries,
    output_path: str | Path,
    *,
    title: str = "Lyapunov Constraint Graph",
) -> Path:
    """Render the Lyapunov constraint graph to ``output_path``."""

    try:
        import matplotlib.pyplot as plt  # type: ignore
    except ImportError as exc:  # pragma: no cover - environment dependent
        raise RuntimeError(
            "matplotlib is required to render the Lyapunov constraint graph"
        ) from exc

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fig, ax_primary = plt.subplots(figsize=(9, 5))
    ax_secondary = ax_primary.twinx()

    ax_primary.plot(series.time, series.b_factor, color="#1f77b4", label="B-factor")
    ax_primary.axhline(0.98, color="#1f77b4", linestyle="--", linewidth=1, label="Stability floor")

    ax_secondary.plot(series.time, series.delta_v, color="#d62728", label="ΔVₜ")
    ax_secondary.axhline(series.lyapunov_floor, color="#d62728", linestyle=":", linewidth=1, label="-ε gate")

    if any(series.gate_active):
        ax_primary.fill_between(
            series.time,
            0,
            1,
            where=series.gate_active,
            color="#ffdd57",
            alpha=0.25,
            transform=ax_primary.get_xaxis_transform(),
            label="Gate active",
        )

    ax_primary.set_xlabel("Time (s)")
    ax_primary.set_ylabel("B-factor stability")
    ax_secondary.set_ylabel("ΔVₜ (Lyapunov derivative)")
    ax_primary.set_title(title)

    # Build a combined legend without duplicate labels.
    handles: List = []
    labels: List[str] = []
    for ax in (ax_primary, ax_secondary):
        for handle, label in zip(*ax.get_legend_handles_labels()):
            if label not in labels:
                labels.append(label)
                handles.append(handle)
    ax_primary.legend(handles, labels, loc="lower right")

    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
    return output_path


def generate_default_visualization(output_path: str | Path) -> Path:
    """Produce the canonical Coherence Gate visualization."""

    series = simulate_coherence_gate_response()
    return render_lyapunov_constraint_graph(series, output_path)


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render the Coherence Gate Lyapunov graph")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/coherence_gate.png"),
        help="Path to the output PNG file",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=2.5,
        help="Total simulation duration in seconds",
    )
    parser.add_argument(
        "--spike",
        type=float,
        default=0.5,
        help="Initial B-factor value after the adversarial spike",
    )
    parser.add_argument(
        "--target",
        type=float,
        default=0.995,
        help="Target B-factor once stability is restored",
    )
    parser.add_argument(
        "--recovery",
        type=float,
        default=0.78,
        help="Maximum allowed recovery time in seconds",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=200,
        help="Number of samples per second",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point to render the canonical visualization."""

    args = _parse_args(argv)
    series = simulate_coherence_gate_response(
        spike_value=args.spike,
        target_value=args.target,
        total_duration=args.duration,
        recovery_time=args.recovery,
        sample_rate=args.sample_rate,
    )
    render_lyapunov_constraint_graph(series, args.output)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

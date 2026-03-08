"""Simulate closed-loop response of HMI + middleware + plant stack."""
from __future__ import annotations

import argparse
import math
import random
from dataclasses import dataclass
from typing import List, Sequence, Tuple


@dataclass
class FirstOrderBlock:
    gain: float
    pole: float

    def as_state(self) -> Tuple[float, float]:
        """Return (A, B) coefficients for \dot{x} = -pole * x + gain * u."""
        return -self.pole, self.gain


@dataclass
class LoopParameters:
    hmi: FirstOrderBlock
    middleware: FirstOrderBlock
    plant: FirstOrderBlock
    feedback_gain: float = 1.0
    process_noise: float = 0.0
    measurement_noise: float = 0.0


Matrix = List[List[float]]
Vector = List[float]


def identity_matrix(size: int) -> Matrix:
    return [[1.0 if i == j else 0.0 for j in range(size)] for i in range(size)]


def mat_add(a: Matrix, b: Matrix) -> Matrix:
    return [[a[i][j] + b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def mat_sub(a: Matrix, b: Matrix) -> Matrix:
    return [[a[i][j] - b[i][j] for j in range(len(a[0]))] for i in range(len(a))]


def mat_mul(a: Matrix, b: Matrix) -> Matrix:
    rows, cols, shared = len(a), len(b[0]), len(b)
    return [[sum(a[i][k] * b[k][j] for k in range(shared)) for j in range(cols)] for i in range(rows)]


def mat_vec_mul(a: Matrix, v: Vector) -> Vector:
    return [sum(a[i][j] * v[j] for j in range(len(v))) for i in range(len(a))]


def vec_add(a: Vector, b: Vector) -> Vector:
    return [a[i] + b[i] for i in range(len(a))]


def vec_sub(a: Vector, b: Vector) -> Vector:
    return [a[i] - b[i] for i in range(len(a))]


def scalar_vec_mul(scalar: float, v: Vector) -> Vector:
    return [scalar * value for value in v]


def scalar_mat_mul(scalar: float, m: Matrix) -> Matrix:
    return [[scalar * value for value in row] for row in m]


def transpose(a: Matrix) -> Matrix:
    rows, cols = len(a), len(a[0])
    return [[a[i][j] for i in range(rows)] for j in range(cols)]


def trace(a: Matrix) -> float:
    return sum(a[i][i] for i in range(len(a)))


def simulate_step(params: LoopParameters, t_final: float = 10.0, dt: float = 0.001) -> Tuple[List[float], List[float], List[Vector]]:
    """Simulate the deterministic closed-loop response to a unit step."""
    n_steps = int(t_final / dt) + 1
    t = [i * dt for i in range(n_steps)]

    x = [[0.0, 0.0, 0.0] for _ in range(n_steps)]
    y = [0.0 for _ in range(n_steps)]

    a1, b1 = params.hmi.as_state()
    a2, b2 = params.middleware.as_state()
    a3, b3 = params.plant.as_state()

    for k in range(1, n_steps):
        r = 1.0
        e = r - params.feedback_gain * y[k - 1]

        x_prev = x[k - 1]
        x1 = x_prev[0] + dt * (a1 * x_prev[0] + b1 * e)
        x2 = x_prev[1] + dt * (a2 * x_prev[1] + b2 * x1)
        x3 = x_prev[2] + dt * (a3 * x_prev[2] + b3 * x2)

        x[k] = [x1, x2, x3]
        y[k] = x3

    return t, y, x


def simulate_kalman(params: LoopParameters, t_final: float = 10.0, dt: float = 0.01) -> Tuple[List[float], List[Vector], List[float]]:
    """Simulate state estimate evolution with process and measurement noise."""
    n_steps = int(t_final / dt) + 1
    t = [i * dt for i in range(n_steps)]

    p1, b1 = params.hmi.as_state()
    p2, b2 = params.middleware.as_state()
    p3, b3 = params.plant.as_state()

    A = [[p1, 0.0, 0.0], [b2, p2, 0.0], [0.0, b3, p3]]
    B = [[b1], [0.0], [0.0]]
    C = [[0.0, 0.0, 1.0]]

    Ad = mat_add(identity_matrix(3), scalar_mat_mul(dt, A))
    Bd = scalar_mat_mul(dt, B)

    q = params.process_noise ** 2
    r_var = params.measurement_noise ** 2
    Q = [[q if i == j else 0.0 for j in range(3)] for i in range(3)]

    x_true = [0.0, 0.0, 0.0]
    x_est = [0.0, 0.0, 0.0]
    P = identity_matrix(3)

    estimates = [[0.0, 0.0, 0.0] for _ in range(n_steps)]
    cov_traces = [0.0 for _ in range(n_steps)]

    for k in range(n_steps):
        r = 1.0
        y_true = mat_vec_mul(C, x_true)[0]
        e = r - params.feedback_gain * y_true

        w = [random.gauss(0.0, params.process_noise) for _ in range(3)] if params.process_noise else [0.0, 0.0, 0.0]
        v = random.gauss(0.0, params.measurement_noise) if params.measurement_noise else 0.0

        x_true = vec_add(mat_vec_mul(Ad, x_true), scalar_vec_mul(Bd[0][0], [e, 0.0, 0.0]))
        x_true = vec_add(x_true, w)
        y_meas = mat_vec_mul(C, x_true)[0] + v

        # Prediction
        x_pred = vec_add(mat_vec_mul(Ad, x_est), scalar_vec_mul(Bd[0][0], [e, 0.0, 0.0]))
        P_pred = mat_add(mat_mul(mat_mul(Ad, P), transpose(Ad)), Q)

        # Update (measurement is scalar)
        cPc = mat_mul(mat_mul(C, P_pred), transpose(C))[0][0]
        s = cPc + r_var
        k_gain_col = scalar_mat_mul(1.0 / s, mat_mul(P_pred, transpose(C)))  # 3x1
        innovation = y_meas - mat_vec_mul(C, x_pred)[0]
        k_gain = [row[0] for row in k_gain_col]
        x_est = vec_add(x_pred, scalar_vec_mul(innovation, k_gain))

        KC = mat_mul([[k_gain[i]] for i in range(3)], C)
        P = mat_mul(mat_sub(identity_matrix(3), KC), P_pred)

        estimates[k] = x_est[:]
        cov_traces[k] = trace(P)

    return t, estimates, cov_traces


def sample_values(values: Sequence[float], count: int = 6) -> List[Tuple[int, float]]:
    if not values:
        return []
    if count <= 1:
        return [(0, values[0])]
    step = max(1, len(values) - 1) / (count - 1)
    indices = [min(int(round(i * step)), len(values) - 1) for i in range(count)]
    seen = set()
    unique_indices = []
    for idx in indices:
        if idx not in seen:
            unique_indices.append(idx)
            seen.add(idx)
    return [(idx, values[idx]) for idx in unique_indices]


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate HMI + middleware closed-loop response")
    parser.add_argument("--hmi", nargs=2, type=float, default=[1.0, 1.0], metavar=("K_h", "a_1"))
    parser.add_argument("--middleware", nargs=2, type=float, default=[1.5, 1.0], metavar=("K_c", "a_2"))
    parser.add_argument("--plant", nargs=2, type=float, default=[2.0, 0.8], metavar=("K_p", "a_3"))
    parser.add_argument("--feedback", type=float, default=1.0)
    parser.add_argument("--process-noise", type=float, default=0.05)
    parser.add_argument("--measurement-noise", type=float, default=0.1)
    parser.add_argument("--duration", type=float, default=8.0)
    parser.add_argument("--dt", type=float, default=0.002)

    args = parser.parse_args()

    params = LoopParameters(
        hmi=FirstOrderBlock(gain=args.hmi[0], pole=args.hmi[1]),
        middleware=FirstOrderBlock(gain=args.middleware[0], pole=args.middleware[1]),
        plant=FirstOrderBlock(gain=args.plant[0], pole=args.plant[1]),
        feedback_gain=args.feedback,
        process_noise=args.process_noise,
        measurement_noise=args.measurement_noise,
    )

    t, y, _ = simulate_step(params, t_final=args.duration, dt=args.dt)
    steady_state = y[-1]
    above_threshold_indices = [i for i, value in enumerate(y) if value >= 0.9 * steady_state]
    rise_time = t[above_threshold_indices[0]] if above_threshold_indices else math.nan
    peak = max(y)
    overshoot = ((peak - steady_state) / steady_state * 100.0) if steady_state else 0.0

    print("Deterministic step response metrics:")
    print(f"  Final value: {steady_state:.3f}")
    if not math.isnan(rise_time):
        print(f"  Rise time to 90% final value: {rise_time:.3f} s")
    else:
        print("  Rise time to 90% final value: not reached")
    print(f"  Percent overshoot: {overshoot:.2f}%")

    t_kf, estimates, cov_traces = simulate_kalman(params, t_final=args.duration, dt=max(args.dt, 0.01))
    print("\nKalman filter covariance trace (sampled):")
    for idx, value in sample_values(cov_traces):
        print(f"  t={t_kf[idx]:.2f} s -> trace(P)={value:.4f}")

    final_state = estimates[-1]
    print("\nFinal estimated state vector:")
    print(f"  x_hmi={final_state[0]:.4f}, x_ctrl={final_state[1]:.4f}, x_plant={final_state[2]:.4f}")


if __name__ == "__main__":
    main()

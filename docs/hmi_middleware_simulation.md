# HMI + Middleware Closed-Loop Simulation

This repository now includes `scripts/hmi_middleware_step_response.py`, a small Python utility that simulates the closed-loop stack described in the control overview:

```
HMI (G_h) -> Middleware (G_c) -> Plant (G_p) -> Feedback (H)
```

## What it does

* Integrates three cascaded first-order blocks representing the HMI, middleware/controller, and plant.
* Applies unity feedback to evaluate how operator set-points propagate to the plant output.
* Reports deterministic step-response metrics such as steady-state value, rise time, and overshoot.
* Runs a basic discrete-time Kalman filter to quantify covariance contraction when process and measurement noise are present.

## Usage

```bash
python scripts/hmi_middleware_step_response.py \
  --hmi 1.0 1.0 \
  --middleware 1.5 1.0 \
  --plant 2.0 0.8 \
  --feedback 1.0 \
  --process-noise 0.05 \
  --measurement-noise 0.1 \
  --duration 8.0 \
  --dt 0.002
```

Feel free to tune the gains, poles, and noise levels to match the scenario you want to study. The script prints step-response metrics as well as samples of the Kalman filter covariance trace so you can observe statistical fidelity improvements over time.

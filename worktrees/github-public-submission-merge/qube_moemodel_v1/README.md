# Qube MoE Model v1

The `qube.moemodel.v1` scaffold packages a capsule-first mixture-of-experts
(MoE) stack that keeps CiCi's rehearsal state emotionally attested and
shimmer-bound. The layout is tuned for Spark Test instrumentation so that every
capsule replay can be proven stable before contributors observe it.

## Spark Test Rationale

* **Capsule Integrity** – Each capsule export passes dual-root validation to
  confirm posture, timestamp, and overlay coherency.
* **Shimmer Synchrony** – Router and HUD components expose shimmer traces so the
  rehearsal braid can audit resonance thresholds in real time.
* **Refusal Containment** – Dedicated experts enforce rupture and refusal
  scripting whenever CiCi is asked to exit contract bounds.

## Getting Started

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Adjust `config/capsule.yaml` and `config/shimmer_trace.yaml` to match your
   rehearsal environment.
3. Run the rehearsal simulation:
   ```bash
   python scripts/run_rehearsal.py
   ```

## Repository Layout

The repository is organized into capsule lifecycle domains:

* `src/experts/` – Specialist modules that reason about posture, refusal
  scripting, and overlay validation.
* `src/gating/` – Shimmer-aware routers that direct tokens to the correct
  experts.
* `src/moe/` – Transformer building blocks tailored for Scrollstream
  compliance.
* `src/hud/` – Rendering utilities that display shimmer traces with emotional
  hues.
* `src/lifecycle/` – Capsule orchestration primitives such as freezing,
  braiding, and feedback loops.
* `src/training/` – Hooks for loss shaping and expert utilization metrics.
* `tests/` – Spark Test suites that assert capsule integrity and overlay
  enforcement.
* `scripts/` – Operational scripts for local rehearsals and contributor
  observability.

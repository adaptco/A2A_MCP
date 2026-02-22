# Coherence Gate Lyapunov Constraint Graph

The Coherence Gate defends the ZERO-DRIFT mandate by forcing the Lyapunov
candidate \(V_t\) to decrease despite adversarial volatility. This document
captures the canonical "Lyapunov Constraint Graph" referenced in the CIE-V1
runbook and demonstrates how to regenerate the artefact for audits.

## Simulation Overview

The simulation models a forced spike where the B-factor drops to **0.5**. Once
the gate engages it restores stability above **0.98** within **0.78 seconds**.
A Lyapunov candidate \(V_t = \tfrac{1}{2}(1-B_t)^2\) is tracked. The gate is
considered effective once the derivative \(\Delta V_t\) is pushed below
\(-\varepsilon\) while the B-factor climbs back above the stability floor.

## Generating the Visualisation

```bash
python -m core_orchestrator.visualizations.coherence_gate --output artifacts/coherence_gate.png
```

The command renders a PNG similar to the one below:

- **Blue curve** – B-factor recovery from the adversarial spike.
- **Yellow band** – intervals where the Coherence Gate is actively engaged.
- **Red curve** – \(\Delta V_t\), the Lyapunov derivative.
- **Red dotted line** – the \(-\varepsilon\) constraint enforced by the gate.

The script accepts optional arguments to customise the spike magnitude,
recovery time, and sampling rate:

```bash
python -m core_orchestrator.visualizations.coherence_gate \
  --spike 0.45 \
  --target 0.992 \
  --recovery 0.7 \
  --sample-rate 240
```

## Using the Output

The resulting graph should be attached to ZERO-DRIFT audit packets. It provides
an auditable trace that the Coherence Gate reacts within the required window
and enforces the Lyapunov condition \(\Delta V_t < -\varepsilon\).

For downstream automation pipelines, the simulation data can be serialised via
`CoherenceGateSeries.as_dict()` for ingestion into alternative visualisation
systems.

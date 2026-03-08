# Unity MLOps Setup Guide

This guide documents the autonomous Unity + RL pipeline in `mlops_unity_pipeline.py` and how to run it in a local or scheduled setup.

## What this pipeline provides

- LLM-assisted Unity C# behavior generation from `UnityAssetSpec`.
- Unity build orchestration hooks (currently safe local placeholders).
- RL training orchestration supporting `online`, `offline`, and `hybrid` modes.
- Optional Vertex AI registration metadata output.
- Cron-style automation with concurrent training jobs and webhook notifications.

## Architecture (high-level)

```text
User Prompt / Asset Description
            ↓
UnityAssetSpec + RLTrainingConfig
            ↓
UnityMLOpsOrchestrator
  ├─ generate_unity_code(...)
  ├─ build_unity_environment(...)
  ├─ train_rl_agent(...)
  └─ register_model_in_vertex(...)
            ↓
TrainingResult + artifacts/ + optional scheduler notifications
```

## Core classes

### `UnityAssetSpec`
Defines the behavior or environment target to generate.

```python
UnityAssetSpec(
    asset_id="nav-001",
    name="NavigationAgent",
    asset_type="behavior",
    description="Navigate obstacles to reach a goal",
    observation_space={"raycast": 8, "velocity": 2},
    action_space={"type": "continuous", "size": 2},
)
```

### `RLTrainingConfig`
Defines training parameters and runtime mode.

```python
RLTrainingConfig(
    algorithm="PPO",
    max_steps=1_000_000,
    num_envs=16,
    time_scale=20.0,
    training_mode="online",  # online | offline | hybrid
)
```

### `TrainingJob`
Single execution request with one asset and one config.

### `UnityMLOpsOrchestrator`
Runs end-to-end steps for one `TrainingJob`.

### `TrainingScheduler`
Runs recurring jobs using cron expressions and concurrency limits.

## Prerequisites

- Python 3.10+
- Unity project with ML-Agents package (for production build/training commands)
- Optional: Google Cloud project for Vertex AI metadata registry flow

Install dependencies:

```bash
pip install mlagents==1.0.0 pyyaml croniter
```

## Quick start: run a single job

```python
import asyncio
from mlops_unity_pipeline import (
    RLTrainingConfig,
    TrainingJob,
    UnityAssetSpec,
    UnityMLOpsOrchestrator,
)


async def main() -> None:
    orchestrator = UnityMLOpsOrchestrator(
        vertex_project="your-gcp-project",
        vertex_region="us-central1",
    )

    asset = UnityAssetSpec(
        asset_id="test-001",
        name="SimpleAgent",
        asset_type="behavior",
        description="Reach target position",
    )

    config = RLTrainingConfig(
        algorithm="PPO",
        max_steps=100_000,
    )

    job = TrainingJob(
        job_id="test-job",
        asset_spec=asset,
        rl_config=config,
    )

    result = await orchestrator.execute_training_job(job)
    print(f"Status: {result.status}")
    print(f"Model: {result.trained_model_path}")


asyncio.run(main())
```

## 24/7 automation with `TrainingScheduler`

```python
import asyncio
from mlops_unity_pipeline import (
    RLTrainingConfig,
    TrainingSchedule,
    TrainingScheduler,
    UnityAssetSpec,
    UnityMLOpsOrchestrator,
)


async def run_forever() -> None:
    orchestrator = UnityMLOpsOrchestrator()
    scheduler = TrainingScheduler(orchestrator, max_concurrent_jobs=4)

    schedule = TrainingSchedule(
        schedule_id="nightly",
        cron_expression="0 2 * * *",  # 2 AM daily
        asset_specs=[
            UnityAssetSpec(
                asset_id="agent-1",
                name="PatrolAgent",
                asset_type="behavior",
                description="Patrol waypoints while avoiding collisions",
            )
        ],
        rl_config=RLTrainingConfig(algorithm="PPO", max_steps=500_000),
    )

    scheduler.add_schedule(schedule)
    await scheduler.run_forever()


asyncio.run(run_forever())
```

## Offline RL in this pipeline

The orchestrator supports:

- `online`: standard simulator interaction loop.
- `offline`: learn from pre-recorded dataset only.
- `hybrid`: initialize from offline data and extend online.

When mode is `offline` or `hybrid`, you must provide an existing `offline_dataset_path`:

```python
config = RLTrainingConfig(
    algorithm="PPO",
    training_mode="offline",
    offline_dataset_path="data/demos/navigation_demo.jsonl",
    max_steps=1_000_000,
)
```

## Integration pattern with A2A-MCP orchestrators

```python
from unified_bridge import BridgeOrchestrator
from mlops_unity_pipeline import UnityMLOpsOrchestrator

bridge = BridgeOrchestrator()
mlops = UnityMLOpsOrchestrator()

# bridge: prompt → code/test orchestration
# mlops: Unity build → RL training → model registration
```

## Production notes

- The current `build_unity_environment` and `train_rl_agent` implementations are safe placeholders for non-Unity environments.
- Replace those methods with your project-specific headless Unity build and `mlagents-learn` commands for production.
- Scheduler de-duplicates same-minute triggers per schedule.
- Artifacts are written under `artifacts/unity_mlops/<job_id>/` by default.
- If `VERTEX_PROJECT` is not configured, registration is skipped safely.

# Unity MLOps Setup Guide

This guide covers how to run the autonomous Unity training pipeline in `mlops_unity_pipeline.py`.

## Prerequisites

- Python 3.10+
- Unity project configured with ML-Agents package
- Optional: Google Cloud project for Vertex AI model registry

Install Python dependencies:

```bash
pip install mlagents==1.0.0 pyyaml croniter
```

## Quick Start

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
        asset_id="nav-001",
        name="NavigationAgent",
        asset_type="behavior",
        description="Navigate around obstacles to a target.",
        observation_space={"raycast": 8, "velocity": 2},
        action_space={"type": "continuous", "size": 2},
    )

    config = RLTrainingConfig(
        algorithm="PPO",
        max_steps=100_000,
        num_envs=8,
        time_scale=20.0,
    )

    job = TrainingJob(job_id="test-job", asset_spec=asset, rl_config=config)
    result = await orchestrator.execute_training_job(job)
    print(result)

asyncio.run(main())
```

## 24/7 Scheduling

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
    scheduler = TrainingScheduler(
        orchestrator,
        max_concurrent_jobs=4,
        webhook_url="https://example.com/training-events",
    )

    schedule = TrainingSchedule(
        schedule_id="nightly",
        cron_expression="0 2 * * *",
        asset_specs=[
            UnityAssetSpec(
                asset_id="agent-1",
                name="PatrolAgent",
                asset_type="behavior",
                description="Patrol waypoints while avoiding collisions.",
            )
        ],
        rl_config=RLTrainingConfig(algorithm="PPO", max_steps=500_000),
    )

    scheduler.add_schedule(schedule)
    await scheduler.run_forever()

asyncio.run(run_forever())
```

## Notes

- The current implementation includes **safe local placeholders** for Unity build and RL training to keep the pipeline runnable in non-Unity environments.
- `TrainingScheduler` prevents duplicate triggers in the same minute for the same schedule.
- `TrainingScheduler` supports concurrent asset jobs and optional webhook notifications for completed runs.
- Replace `build_unity_environment` and `train_rl_agent` with project-specific commands for full production usage.
- Vertex registration writes metadata to `vertex_registration.json` and returns a resource URI-like string for traceability.

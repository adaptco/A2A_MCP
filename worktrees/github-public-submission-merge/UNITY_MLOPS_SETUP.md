# UNITY_MLOPS_SETUP

## Prerequisites

### Unity + ML-Agents
- Unity Editor 2022 LTS or newer.
- Unity project configured with the ML-Agents package.
- ML-Agents Python side tools:
  ```bash
  pip install mlagents==1.0.0 torch pyyaml croniter
  ```
- (Optional for accelerated training) CUDA-enabled GPU and matching PyTorch CUDA build.

### Python runtime
- Python 3.10+.
- Install project dependencies in your active virtual environment.

### GCP / Vertex AI setup
- Create or select a GCP project.
- Enable Vertex AI API.
- Configure authentication (for example via `gcloud auth application-default login`).
- Set environment values as needed:
  ```bash
  export GOOGLE_CLOUD_PROJECT="your-project-id"
  export GOOGLE_CLOUD_REGION="us-central1"
  ```

---

## Quick-start (orchestrator API)

> Canonical import path: `core_orchestrator.mlops_unity_pipeline` (installed package).
>
> Compatibility import path for source checkouts: `mlops_unity_pipeline` (root wrapper).

```python
import asyncio

from core_orchestrator.mlops_unity_pipeline import (
    RLTrainingConfig,
    TrainingJob,
    UnityAssetSpec,
    UnityMLOpsOrchestrator,
)


async def main() -> None:
    orchestrator = UnityMLOpsOrchestrator()

    asset = UnityAssetSpec(
        asset_id="nav-001",
        name="NavigationAgent",
        asset_type="behavior",
        description="Navigate to a goal while avoiding static and dynamic obstacles.",
        observation_space={"raycasts": 16, "velocity": 3, "goal_direction": 3},
        action_space={"type": "continuous", "size": 2},
        reward_signals={"goal": 1.0, "collision": -0.5, "step_penalty": -0.01},
    )

    config = RLTrainingConfig(
        algorithm="PPO",
        max_steps=1_000_000,
        num_envs=16,
        time_scale=20.0,
        vertex_project="your-project-id",
        vertex_region="us-central1",
    )

    job = TrainingJob(job_id="nav-job-001", asset_spec=asset, rl_config=config)
    result = await orchestrator.execute_training_job(job)

    print("status:", result.status)
    print("trained_model_path:", result.trained_model_path)
    print("vertex_model_resource_name:", result.vertex_model_resource_name)


asyncio.run(main())
```

---

## Scheduling examples

### Hourly training

```python
import asyncio

from core_orchestrator.mlops_unity_pipeline import (
    RLTrainingConfig,
    TrainingSchedule,
    TrainingScheduler,
    UnityAssetSpec,
    UnityMLOpsOrchestrator,
)


async def run_hourly() -> None:
    orchestrator = UnityMLOpsOrchestrator()
    scheduler = TrainingScheduler(orchestrator, poll_interval_seconds=15)

    schedule = TrainingSchedule(
        schedule_id="hourly-navigation",
        cron_expression="0 * * * *",  # every hour
        asset_specs=[
            UnityAssetSpec(
                asset_id="nav-001",
                name="NavigationAgent",
                asset_type="behavior",
                description="Refresh navigation policy from latest data.",
            )
        ],
        rl_config=RLTrainingConfig(algorithm="PPO", max_steps=250_000),
        max_concurrent_jobs=1,
    )

    scheduler.add_schedule(schedule)
    await scheduler.run_forever()


asyncio.run(run_hourly())
```

### Nightly training

```python
import asyncio

from core_orchestrator.mlops_unity_pipeline import (
    RLTrainingConfig,
    TrainingSchedule,
    TrainingScheduler,
    UnityAssetSpec,
    UnityMLOpsOrchestrator,
)


async def run_nightly() -> None:
    orchestrator = UnityMLOpsOrchestrator()
    scheduler = TrainingScheduler(orchestrator)

    schedule = TrainingSchedule(
        schedule_id="nightly-batch",
        cron_expression="0 2 * * *",  # 2 AM daily
        asset_specs=[
            UnityAssetSpec(
                asset_id="combat-001",
                name="CombatAgent",
                asset_type="behavior",
                description="Train combat behavior with updated balancing.",
            ),
            UnityAssetSpec(
                asset_id="patrol-001",
                name="PatrolAgent",
                asset_type="behavior",
                description="Train patrol routes with obstacle avoidance.",
            ),
        ],
        rl_config=RLTrainingConfig(
            algorithm="PPO",
            max_steps=5_000_000,
            num_envs=32,
            time_scale=50.0,
        ),
        max_concurrent_jobs=2,
    )

    scheduler.add_schedule(schedule)
    await scheduler.run_forever()


asyncio.run(run_nightly())
```

---

## Deployment and monitoring notes

- **Containerization:** package Unity build scripts + Python training worker in Docker; mount output volume for artifacts.
- **Execution platform:** run scheduled workers in Kubernetes (CronJob/Deployment), VM instances, or managed batch runners.
- **Artifact flow:** persist generated manifests, metrics, and model binaries to durable storage (for example GCS bucket).
- **Model registry:** use Vertex AI model registration metadata from each job output and apply environment labels/tags.
- **Observability:**
  - Emit structured logs from orchestrator and scheduler.
  - Track training metrics in TensorBoard and/or Vertex Experiments.
  - Add webhook callbacks (Slack/Teams/incident tools) for completion/failure alerts.
- **Operational safety:**
  - Use separate projects or model namespaces for dev/staging/prod.
  - Cap concurrency with `max_concurrent_jobs` per schedule.
  - Add retry/backoff around Unity build and training commands for transient failures.

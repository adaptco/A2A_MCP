import pytest

from mlops_unity_pipeline import (
    RLTrainingConfig,
    TrainingJob,
    TrainingSchedule,
    TrainingScheduler,
    UnityAssetSpec,
    UnityMLOpsOrchestrator,
)


@pytest.mark.asyncio
async def test_orchestrator_emits_mcp_bus_events_for_successful_job(tmp_path):
    events = []

    async def sink(event):
        events.append(event)

    orchestrator = UnityMLOpsOrchestrator(mcp_event_sink=sink, dry_run=True)
    job = TrainingJob(
        job_id="job-001",
        asset_spec=UnityAssetSpec(
            asset_id="asset-001",
            name="NavAgent",
            asset_type="behavior",
            description="Navigate to a target while avoiding obstacles.",
        ),
        rl_config=RLTrainingConfig(max_steps=10_000),
        output_dir=str(tmp_path),
        vertex_project="demo-project",
    )

    result = await orchestrator.execute_training_job(job)

    assert result.status == "succeeded"
    assert [e["event_type"] for e in events] == [
        "job_started",
        "code_generated",
        "unity_build_completed",
        "training_completed",
        "vertex_registration_completed",
        "job_succeeded",
    ]
    assert events[-1]["payload"]["result"]["status"] == "succeeded"


@pytest.mark.asyncio
async def test_orchestrator_emits_failed_event_on_sink_exception(tmp_path):
    events = []

    async def sink(event):
        events.append(event)
        if event["event_type"] == "training_completed":
            raise RuntimeError("sink offline")

    orchestrator = UnityMLOpsOrchestrator(mcp_event_sink=sink, dry_run=True)
    job = TrainingJob(
        job_id="job-002",
        asset_spec=UnityAssetSpec(
            asset_id="asset-002",
            name="PatrolAgent",
            asset_type="behavior",
            description="Patrol between waypoints.",
        ),
        rl_config=RLTrainingConfig(max_steps=1_000),
        output_dir=str(tmp_path),
    )

    result = await orchestrator.execute_training_job(job)

    assert result.status == "failed"
    assert result.error == "sink offline"
    assert [e["event_type"] for e in events] == [
        "job_started",
        "code_generated",
        "unity_build_completed",
        "training_completed",
    ]


def test_scheduler_accepts_valid_cron_expression():
    orchestrator = UnityMLOpsOrchestrator(dry_run=True)
    scheduler = TrainingScheduler(orchestrator)

    schedule = TrainingSchedule(
        schedule_id="nightly",
        cron_expression="0 2 * * *",
        asset_specs=[
            UnityAssetSpec(
                asset_id="asset-003",
                name="ScoutAgent",
                asset_type="behavior",
                description="Scout a room.",
            )
        ],
        rl_config=RLTrainingConfig(),
    )

    scheduler.add_schedule(schedule)

    assert "nightly" in scheduler._schedules

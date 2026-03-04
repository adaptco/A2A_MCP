from datetime import datetime, timedelta, timezone

from mlops_unity_pipeline import RLTrainingConfig, TrainingSchedule, TrainingScheduler, UnityAssetSpec, UnityMLOpsOrchestrator


def _schedule() -> TrainingSchedule:
    return TrainingSchedule(
        schedule_id="nightly-training",
        cron_expression="0 2 * * *",
        asset_specs=[
            UnityAssetSpec(
                asset_id="asset-001",
                name="PatrolAgent",
                asset_type="behavior",
                description="Patrol between waypoints",
            )
        ],
        rl_config=RLTrainingConfig(),
    )


def test_is_due_runs_immediately_when_no_checkpoint(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scheduler = TrainingScheduler(UnityMLOpsOrchestrator())
    schedule = _schedule()

    now = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)

    assert scheduler._is_due(schedule, now) is True



def test_is_due_respects_checkpoint_after_first_run(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    scheduler = TrainingScheduler(UnityMLOpsOrchestrator())
    schedule = _schedule()

    now = datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)
    assert scheduler._is_due(schedule, now) is True

    before_next_cron = now + timedelta(hours=1)
    assert scheduler._is_due(schedule, before_next_cron) is False

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import asyncio
from datetime import datetime, timedelta, timezone

from mlops_unity_pipeline import (
    RLTrainingConfig,
    TrainingJob,
    TrainingSchedule,
    TrainingScheduler,
    UnityAssetSpec,
    UnityMLOpsOrchestrator,
)


def test_cron_fallback_supports_steps_and_ranges():
    from mlops_unity_pipeline import _next_cron_time

    base = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    next_run = _next_cron_time("*/15 0-1 * * *", base)
    assert next_run == datetime(2025, 1, 1, 0, 15, tzinfo=timezone.utc)


def test_cron_fallback_supports_stepped_fields_with_explicit_start():
    from mlops_unity_pipeline import _next_cron_time

    base = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    next_run = _next_cron_time("1/5 * * * *", base)
    assert next_run == datetime(2025, 1, 1, 0, 1, tzinfo=timezone.utc)

    following_run = _next_cron_time("1/5 * * * *", next_run)
    assert following_run == datetime(2025, 1, 1, 0, 6, tzinfo=timezone.utc)


def test_orchestrator_executes_training_job(tmp_path):
    orchestrator = UnityMLOpsOrchestrator(workspace_dir=tmp_path)
    job = TrainingJob(
        job_id="job-1",
        asset_spec=UnityAssetSpec(
            asset_id="asset-1",
            name="SimpleAgent",
            asset_type="behavior",
            description="Reach target",
        ),
        rl_config=RLTrainingConfig(max_steps=10),
    )

    result = asyncio.run(orchestrator.execute_training_job(job))

    assert result.status == "completed"
    assert (tmp_path / "job-1" / "SimpleAgent.cs").exists()
    assert result.trained_model_path.endswith(".onnx")


def test_scheduler_dispatches_due_job(tmp_path):
    orchestrator = UnityMLOpsOrchestrator(workspace_dir=tmp_path)
    scheduler = TrainingScheduler(orchestrator)

    schedule = TrainingSchedule(
        schedule_id="sched-1",
        cron_expression="* * * * *",
        asset_specs=[
            UnityAssetSpec(
                asset_id="asset-1",
                name="Bot",
                asset_type="behavior",
                description="Test behavior",
            )
        ],
        rl_config=RLTrainingConfig(max_steps=5),
    )
    scheduler.add_schedule(schedule)

    # Force due state.
    scheduler._next_run[schedule.schedule_id] = datetime.now(timezone.utc) - timedelta(seconds=1)

    asyncio.run(scheduler.run_once())
    asyncio.run(scheduler.shutdown())

    assert any((tmp_path).glob("sched-1-*"))


def test_train_agent_uses_external_command_when_configured(tmp_path):
    script_path = tmp_path / "emit_model.py"
    script_path.write_text(
        """
import os
from pathlib import Path

Path(os.environ['MLAGENTS_OUTPUT_MODEL']).write_bytes(b'external-model')
""".strip(),
        encoding="utf-8",
    )

    orchestrator = UnityMLOpsOrchestrator(
        workspace_dir=tmp_path,
        mlagents_train_command=["python", str(script_path)],
    )
    job = TrainingJob(
        job_id="job-external",
        asset_spec=UnityAssetSpec(
            asset_id="asset-external",
            name="ExternalBot",
            asset_type="behavior",
            description="External command training",
        ),
        rl_config=RLTrainingConfig(max_steps=10),
    )

    result = asyncio.run(orchestrator.execute_training_job(job))
    assert Path(result.trained_model_path).read_bytes() == b"external-model"


def test_unity_build_command_receives_absolute_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    relative_workspace = Path("artifacts") / "mlops"

    script_path = tmp_path / "capture_build_args.py"
    args_file = tmp_path / "build_args.json"
    script_path.write_text(
        f"""
import json
import sys
from pathlib import Path

Path({str(args_file)!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')
""".strip(),
        encoding="utf-8",
    )

    orchestrator = UnityMLOpsOrchestrator(
        workspace_dir=relative_workspace,
        unity_build_command=["python", str(script_path)],
    )
    job = TrainingJob(
        job_id="job-build-abs",
        asset_spec=UnityAssetSpec(
            asset_id="asset-build-abs",
            name="BuildBot",
            asset_type="behavior",
            description="Verify build args",
        ),
        rl_config=RLTrainingConfig(max_steps=1),
    )

    asyncio.run(orchestrator.execute_training_job(job))

    import json

    build_args = json.loads(args_file.read_text(encoding="utf-8"))
    assert Path(build_args[0]).is_absolute()
    assert Path(build_args[1]).is_absolute()


def test_train_agent_external_command_uses_absolute_env_paths(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    relative_workspace = Path("artifacts") / "mlops"

    script_path = tmp_path / "capture_train_env.py"
    env_file = tmp_path / "train_env.json"
    script_path.write_text(
        f"""
import json
import os
from pathlib import Path

payload = {{
    'UNITY_BUILD_PATH': os.environ['UNITY_BUILD_PATH'],
    'MLAGENTS_CONFIG_PATH': os.environ['MLAGENTS_CONFIG_PATH'],
    'MLAGENTS_OUTPUT_MODEL': os.environ['MLAGENTS_OUTPUT_MODEL'],
}}
Path({str(env_file)!r}).write_text(json.dumps(payload), encoding='utf-8')
Path(os.environ['MLAGENTS_OUTPUT_MODEL']).write_bytes(b'external-model')
""".strip(),
        encoding="utf-8",
    )

    orchestrator = UnityMLOpsOrchestrator(
        workspace_dir=relative_workspace,
        mlagents_train_command=["python", str(script_path)],
    )
    job = TrainingJob(
        job_id="job-train-abs",
        asset_spec=UnityAssetSpec(
            asset_id="asset-train-abs",
            name="TrainBot",
            asset_type="behavior",
            description="Verify training env",
        ),
        rl_config=RLTrainingConfig(max_steps=1),
    )

    asyncio.run(orchestrator.execute_training_job(job))

    import json

    train_env = json.loads(env_file.read_text(encoding="utf-8"))
    assert Path(train_env["UNITY_BUILD_PATH"]).is_absolute()
    assert Path(train_env["MLAGENTS_CONFIG_PATH"]).is_absolute()
    assert Path(train_env["MLAGENTS_OUTPUT_MODEL"]).is_absolute()

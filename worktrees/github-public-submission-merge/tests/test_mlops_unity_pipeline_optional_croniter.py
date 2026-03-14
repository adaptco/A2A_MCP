import asyncio
import builtins
import importlib.util
import sys
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[1] / "mlops_unity_pipeline.py"


def _load_module_without_croniter(monkeypatch: pytest.MonkeyPatch, module_name: str):
    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "croniter" or name.startswith("croniter."):
            raise ImportError("No module named 'croniter'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    spec = importlib.util.spec_from_file_location(module_name, MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules.pop(module_name, None)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def test_orchestrator_runs_without_croniter(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _load_module_without_croniter(monkeypatch, "mlops_unity_pipeline_no_croniter_run")

    orchestrator = module.UnityMLOpsOrchestrator(workspace_root=tmp_path)
    job = module.TrainingJob(
        job_id="job-no-croniter",
        asset_spec=module.UnityAssetSpec(
            asset_id="asset-1",
            name="SimpleAgent",
            asset_type="behavior",
            description="Reach target",
        ),
        rl_config=module.RLTrainingConfig(max_steps=10),
    )

    result = asyncio.run(orchestrator.execute_training_job(job))

    assert result.status == "completed"
    assert Path(result.trained_model_path).exists()


def test_scheduler_raises_when_croniter_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _load_module_without_croniter(monkeypatch, "mlops_unity_pipeline_no_croniter_schedule")

    scheduler = module.TrainingScheduler(module.UnityMLOpsOrchestrator())
    schedule = module.TrainingSchedule(
        schedule_id="nightly-training",
        cron_expression="0 2 * * *",
        asset_specs=[
            module.UnityAssetSpec(
                asset_id="asset-001",
                name="PatrolAgent",
                asset_type="behavior",
                description="Patrol between waypoints",
            )
        ],
        rl_config=module.RLTrainingConfig(),
    )

    with pytest.raises(RuntimeError, match="croniter"):
        scheduler.add_schedule(schedule)

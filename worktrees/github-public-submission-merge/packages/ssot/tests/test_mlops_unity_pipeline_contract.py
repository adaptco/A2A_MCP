import importlib


def test_root_module_contract_entrypoints():
    module = importlib.import_module("mlops_unity_pipeline")

    assert hasattr(module, "UnityMLOpsOrchestrator")
    assert hasattr(module, "TrainingScheduler")
    assert hasattr(module, "TrainingSchedule")
    assert hasattr(module, "TrainingJob")
    assert hasattr(module, "UnityAssetSpec")
    assert hasattr(module, "RLTrainingConfig")
    assert hasattr(module, "_next_cron_time")

    orchestrator = module.UnityMLOpsOrchestrator(workspace_dir="artifacts/mlops")
    scheduler = module.TrainingScheduler(orchestrator)
    assert callable(scheduler.run_once)
    assert callable(scheduler.shutdown)

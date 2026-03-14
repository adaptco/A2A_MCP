import asyncio
import importlib.util
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

module_path = Path(__file__).resolve().parents[1] / 'mlops_unity_pipeline.py'
spec = importlib.util.spec_from_file_location('mlops_unity_pipeline', module_path)
mlops = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules['mlops_unity_pipeline'] = mlops
spec.loader.exec_module(mlops)

RLTrainingConfig = mlops.RLTrainingConfig
TrainingJob = mlops.TrainingJob
UnityAssetSpec = mlops.UnityAssetSpec
UnityMLOpsOrchestrator = mlops.UnityMLOpsOrchestrator


def test_offline_training_writes_dataset_path() -> None:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        dataset = tmp_path / "demo.jsonl"
        dataset.write_text("{}\n", encoding="utf-8")

        orchestrator = UnityMLOpsOrchestrator()
        job = TrainingJob(
            job_id="offline-job",
            asset_spec=UnityAssetSpec(
                asset_id="a1",
                name="OfflineAgent",
                asset_type="behavior",
                description="Train from demonstrations",
            ),
            rl_config=RLTrainingConfig(
                training_mode="offline",
                offline_dataset_path=str(dataset),
            ),
            output_dir=str(tmp_path / "out"),
            register_to_vertex=False,
        )

        result = asyncio.run(orchestrator.execute_training_job(job))

        assert result.status == "completed"
        summary_path = Path(result.trained_model_path) / "training_summary.json"
        summary_text = summary_path.read_text(encoding="utf-8")
        assert '"training_mode": "offline"' in summary_text
<<<<<<< HEAD
        assert str(dataset.resolve()) in summary_text
=======
        assert dataset.resolve().as_posix() in summary_text

        assert '"merkle_seed": "0x1984_Q9"' in summary_text
        assert '"nested_alignment_report"' in summary_text
>>>>>>> origin/main


def test_offline_training_requires_dataset() -> None:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        orchestrator = UnityMLOpsOrchestrator()
        job = TrainingJob(
            job_id="missing-dataset-job",
            asset_spec=UnityAssetSpec(
                asset_id="a2",
                name="MissingDatasetAgent",
                asset_type="behavior",
                description="Should fail without dataset",
            ),
            rl_config=RLTrainingConfig(training_mode="offline"),
            output_dir=str(tmp_path / "out"),
            register_to_vertex=False,
        )

        result = asyncio.run(orchestrator.execute_training_job(job))

        assert result.status == "failed"
        assert "offline_dataset_path is required" in (result.error or "")
<<<<<<< HEAD
=======


def test_merkle_hash_is_deterministic_for_same_inputs() -> None:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        dataset = tmp_path / "demo.jsonl"
        dataset.write_text("{}\n", encoding="utf-8")

        orchestrator = UnityMLOpsOrchestrator()
        asset = UnityAssetSpec(
            asset_id="a3",
            name="DeterministicAgent",
            asset_type="behavior",
            description="Ensure stable hash",
        )
        config = RLTrainingConfig(
            training_mode="offline",
            offline_dataset_path=str(dataset),
            run_id_prefix="fixed",
        )

        report_a = orchestrator._run_nested_alignment_drill(
            TrainingJob(job_id="j1", asset_spec=asset, rl_config=config)
        )
        report_b = orchestrator._run_nested_alignment_drill(
            TrainingJob(job_id="j2", asset_spec=asset, rl_config=config)
        )

        hash_a = orchestrator._compute_merkle_hash(
            TrainingJob(job_id="j1", asset_spec=asset, rl_config=config), report_a
        )
        hash_b = orchestrator._compute_merkle_hash(
            TrainingJob(job_id="j2", asset_spec=asset, rl_config=config), report_b
        )

        assert report_a == report_b
        assert hash_a == hash_b


def test_invalid_alignment_slice_count_fails() -> None:
    with TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        orchestrator = UnityMLOpsOrchestrator()
        job = TrainingJob(
            job_id="bad-slices-job",
            asset_spec=UnityAssetSpec(
                asset_id="a4",
                name="BadSliceAgent",
                asset_type="behavior",
                description="Should fail with invalid slices",
            ),
            rl_config=RLTrainingConfig(token_alignment_slices=0),
            output_dir=str(tmp_path / "out"),
            register_to_vertex=False,
        )

        result = asyncio.run(orchestrator.execute_training_job(job))

        assert result.status == "failed"
        assert "token_alignment_slices must be >= 1" in (result.error or "")
>>>>>>> origin/main

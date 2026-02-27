"""Autonomous Unity MLOps pipeline orchestration.

This module provides a production-oriented skeleton for an end-to-end workflow:
1. Generate Unity C# assets from natural language.
2. Build Unity environments in headless mode.
3. Train ML-Agents policies (supports offline-first workflows).
4. Register trained artifacts in Vertex AI.
5. Schedule recurring training jobs via cron expressions.
"""

from __future__ import annotations

import asyncio
import json
import logging
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, Dict, List, Optional
from uuid import uuid4

from croniter import croniter
import yaml

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class UnityAssetSpec:
    """Declarative specification for a Unity asset/behavior to generate."""

    asset_id: str
    name: str
    asset_type: str
    description: str
    observation_space: Dict[str, Any] = field(default_factory=dict)
    action_space: Dict[str, Any] = field(default_factory=dict)
    generation_context: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RLTrainingConfig:
    """ML-Agents training configuration."""

    algorithm: str = "PPO"
    max_steps: int = 1_000_000
    num_envs: int = 16
    time_scale: float = 20.0
    batch_size: int = 1024
    buffer_size: int = 10240
    learning_rate: float = 3e-4
    beta: float = 5e-3
    epsilon: float = 0.2
    lambd: float = 0.95
    num_epoch: int = 3
    hidden_units: int = 256
    num_layers: int = 2
    use_offline_demonstrations: bool = False
    demonstration_path: Optional[str] = None
    additional_hyperparameters: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TrainingJob:
    """One complete pipeline execution for a single asset spec."""

    job_id: str
    asset_spec: UnityAssetSpec
    rl_config: RLTrainingConfig
    unity_project_path: str = "."
    output_dir: str = "artifacts"
    vertex_project: Optional[str] = None
    vertex_region: str = "us-central1"
    vertex_model_display_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class TrainingResult:
    """Execution result for a TrainingJob."""

    job_id: str
    status: str
    started_at: str
    completed_at: str
    generated_script_path: Optional[str] = None
    build_path: Optional[str] = None
    trained_model_path: Optional[str] = None
    vertex_model_resource: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass(slots=True)
class TrainingSchedule:
    """Cron-based recurring schedule."""

    schedule_id: str
    cron_expression: str
    asset_specs: List[UnityAssetSpec]
    rl_config: RLTrainingConfig
    unity_project_path: str = "."
    output_dir: str = "artifacts"
    vertex_project: Optional[str] = None
    vertex_region: str = "us-central1"
    webhook_url: Optional[str] = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class UnityMLOpsOrchestrator:
    """Coordinates Unity code generation, build, training, and registration."""

    def __init__(
        self,
        *,
        llm_generate_fn: Optional[Callable[[UnityAssetSpec], Awaitable[str]]] = None,
        dry_run: bool = True,
        unity_executable: str = "Unity",
        mlagents_learn_cmd: str = "mlagents-learn",
    ) -> None:
        self._llm_generate_fn = llm_generate_fn
        self._dry_run = dry_run
        self._unity_executable = unity_executable
        self._mlagents_learn_cmd = mlagents_learn_cmd

    async def execute_training_job(self, job: TrainingJob) -> TrainingResult:
        started_at = _utc_now_iso()
        output_root = Path(job.output_dir) / job.job_id
        output_root.mkdir(parents=True, exist_ok=True)

        try:
            script_path = await self.generate_unity_code(job.asset_spec, output_root)
            build_path = await self.build_unity_environment(job, output_root)
            trained_model_path = await self.train_with_mlagents(job, build_path, output_root)
            vertex_resource = await self.register_in_vertex_ai(job, trained_model_path)

            return TrainingResult(
                job_id=job.job_id,
                status="succeeded",
                started_at=started_at,
                completed_at=_utc_now_iso(),
                generated_script_path=str(script_path),
                build_path=str(build_path),
                trained_model_path=str(trained_model_path),
                vertex_model_resource=vertex_resource,
            )
        except Exception as exc:  # pragma: no cover
            LOGGER.exception("Training job failed: %s", job.job_id)
            return TrainingResult(
                job_id=job.job_id,
                status="failed",
                started_at=started_at,
                completed_at=_utc_now_iso(),
                error=str(exc),
            )

    async def generate_unity_code(self, asset_spec: UnityAssetSpec, output_root: Path) -> Path:
        script_dir = output_root / "generated"
        script_dir.mkdir(parents=True, exist_ok=True)
        script_path = script_dir / f"{asset_spec.name}.cs"

        if self._llm_generate_fn:
            csharp = await self._llm_generate_fn(asset_spec)
        else:
            csharp = self._fallback_csharp_template(asset_spec)

        script_path.write_text(csharp, encoding="utf-8")
        LOGGER.info("Generated Unity script: %s", script_path)
        return script_path

    async def build_unity_environment(self, job: TrainingJob, output_root: Path) -> Path:
        build_dir = output_root / "build"
        build_dir.mkdir(parents=True, exist_ok=True)
        build_path = build_dir / f"{job.asset_spec.name}.x86_64"

        if self._dry_run:
            build_path.write_text("dry-run build placeholder", encoding="utf-8")
            return build_path

        cmd = [
            self._unity_executable,
            "-batchmode",
            "-nographics",
            "-quit",
            "-projectPath",
            job.unity_project_path,
            "-executeMethod",
            "BuildScript.PerformBuild",
            "-buildOutput",
            str(build_path),
        ]
        await self._run_async_subprocess(cmd)
        return build_path

    async def train_with_mlagents(self, job: TrainingJob, build_path: Path, output_root: Path) -> Path:
        runs_dir = output_root / "runs"
        runs_dir.mkdir(parents=True, exist_ok=True)
        config_path = output_root / "mlagents_config.yaml"

        behavior_name = job.asset_spec.name
        config = self._render_mlagents_config(job.rl_config, behavior_name)
        config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

        model_output = runs_dir / job.job_id

        if self._dry_run:
            model_output.mkdir(parents=True, exist_ok=True)
            weights = model_output / "policy.onnx"
            weights.write_text("dry-run model placeholder", encoding="utf-8")
            return weights

        cmd = [
            self._mlagents_learn_cmd,
            str(config_path),
            "--run-id",
            job.job_id,
            "--env",
            str(build_path),
            "--time-scale",
            str(job.rl_config.time_scale),
            "--num-envs",
            str(job.rl_config.num_envs),
            "--force",
        ]

        if job.rl_config.use_offline_demonstrations and job.rl_config.demonstration_path:
            cmd.extend(["--initialize-from", job.rl_config.demonstration_path])

        await self._run_async_subprocess(cmd, cwd=str(output_root))
        return model_output / "policy.onnx"

    async def register_in_vertex_ai(self, job: TrainingJob, trained_model_path: Path) -> Optional[str]:
        if not job.vertex_project:
            LOGGER.info("Vertex project not configured for job %s; skipping model registration.", job.job_id)
            return None

        if self._dry_run:
            return f"projects/{job.vertex_project}/locations/{job.vertex_region}/models/dry-run-{job.job_id}"

        try:
            from google.cloud import aiplatform
        except ImportError as exc:
            raise RuntimeError("google-cloud-aiplatform is required for Vertex registration") from exc

        aiplatform.init(project=job.vertex_project, location=job.vertex_region)
        display_name = job.vertex_model_display_name or f"{job.asset_spec.name}-{job.job_id}"
        model = aiplatform.Model.upload(
            display_name=display_name,
            artifact_uri=str(trained_model_path.parent),
            serving_container_image_uri="us-docker.pkg.dev/vertex-ai/prediction/pytorch-cpu.2-3:latest",
        )
        return model.resource_name

    async def _run_async_subprocess(self, cmd: List[str], cwd: Optional[str] = None) -> None:
        LOGGER.info("Executing command: %s", " ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise RuntimeError(
                f"Command failed ({proc.returncode}): {' '.join(cmd)}\n"
                f"stdout:\n{stdout.decode(errors='ignore')}\n"
                f"stderr:\n{stderr.decode(errors='ignore')}"
            )

    def _fallback_csharp_template(self, asset_spec: UnityAssetSpec) -> str:
        description = asset_spec.description.replace("\n", " ")
        return textwrap.dedent(
            f"""
            using UnityEngine;

            /// <summary>
            /// Auto-generated behavior for {asset_spec.name}.
            /// {description}
            /// </summary>
            public class {asset_spec.name} : MonoBehaviour
            {{
                private void Start()
                {{
                    Debug.Log("{asset_spec.name} initialized. Asset ID: {asset_spec.asset_id}");
                }}

                private void Update()
                {{
                    // TODO: Replace with ML-Agents observations/actions.
                }}
            }}
            """
        ).strip() + "\n"

    def _render_mlagents_config(self, cfg: RLTrainingConfig, behavior_name: str) -> Dict[str, Any]:
        trainer_block: Dict[str, Any] = {
            "trainer_type": cfg.algorithm.lower(),
            "hyperparameters": {
                "batch_size": cfg.batch_size,
                "buffer_size": cfg.buffer_size,
                "learning_rate": cfg.learning_rate,
                "beta": cfg.beta,
                "epsilon": cfg.epsilon,
                "lambd": cfg.lambd,
                "num_epoch": cfg.num_epoch,
            },
            "network_settings": {
                "normalize": True,
                "hidden_units": cfg.hidden_units,
                "num_layers": cfg.num_layers,
            },
            "max_steps": cfg.max_steps,
            "time_horizon": 64,
            "summary_freq": 50_000,
        }
        trainer_block.update(cfg.additional_hyperparameters)

        return {
            "behaviors": {
                behavior_name: trainer_block,
            }
        }


class TrainingScheduler:
    """Cron scheduler for recurring training jobs."""

    def __init__(self, orchestrator: UnityMLOpsOrchestrator, max_concurrency: int = 2) -> None:
        self._orchestrator = orchestrator
        self._max_concurrency = max_concurrency
        self._schedules: Dict[str, TrainingSchedule] = {}

    def add_schedule(self, schedule: TrainingSchedule) -> None:
        croniter(schedule.cron_expression, datetime.now(timezone.utc))
        self._schedules[schedule.schedule_id] = schedule

    def remove_schedule(self, schedule_id: str) -> None:
        self._schedules.pop(schedule_id, None)

    async def run_forever(self, poll_interval_seconds: int = 30) -> None:
        sem = asyncio.Semaphore(self._max_concurrency)
        while True:
            now = datetime.now(timezone.utc)
            tasks = []
            for schedule in self._schedules.values():
                if self._is_due(schedule, now):
                    tasks.extend(await self._spawn_schedule_jobs(schedule, sem))
            if tasks:
                await asyncio.gather(*tasks)
            await asyncio.sleep(poll_interval_seconds)

    async def _spawn_schedule_jobs(
        self,
        schedule: TrainingSchedule,
        sem: asyncio.Semaphore,
    ) -> List[asyncio.Task[None]]:
        async def _run_one(asset_spec: UnityAssetSpec) -> None:
            async with sem:
                job_id = f"{schedule.schedule_id}-{asset_spec.asset_id}-{uuid4().hex[:8]}"
                job = TrainingJob(
                    job_id=job_id,
                    asset_spec=asset_spec,
                    rl_config=schedule.rl_config,
                    unity_project_path=schedule.unity_project_path,
                    output_dir=schedule.output_dir,
                    vertex_project=schedule.vertex_project,
                    vertex_region=schedule.vertex_region,
                )
                result = await self._orchestrator.execute_training_job(job)
                await self._notify(schedule, result)

        return [asyncio.create_task(_run_one(spec)) for spec in schedule.asset_specs]

    def _is_due(self, schedule: TrainingSchedule, now: datetime) -> bool:
        checkpoint_file = Path(".scheduler") / f"{schedule.schedule_id}.json"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

        last_run_ts: Optional[str] = None
        if checkpoint_file.exists():
            last_run_ts = json.loads(checkpoint_file.read_text(encoding="utf-8")).get("last_run_ts")

        if not last_run_ts:
            checkpoint_file.write_text(json.dumps({"last_run_ts": now.isoformat()}), encoding="utf-8")
            return True

        base = datetime.fromisoformat(last_run_ts)
        next_due = croniter(schedule.cron_expression, base).get_next(datetime)

        if next_due <= now:
            checkpoint_file.write_text(json.dumps({"last_run_ts": next_due.isoformat()}), encoding="utf-8")
            return True
        return False

    async def _notify(self, schedule: TrainingSchedule, result: TrainingResult) -> None:
        if not schedule.webhook_url:
            return

        payload = {
            "schedule_id": schedule.schedule_id,
            "job_id": result.job_id,
            "status": result.status,
            "trained_model_path": result.trained_model_path,
            "vertex_model_resource": result.vertex_model_resource,
            "error": result.error,
        }

        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(schedule.webhook_url, json=payload, timeout=10) as response:
                    response.raise_for_status()
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Failed to send webhook notification for %s: %s", result.job_id, exc)

"""Canonical Unity MLOps orchestration module.

Import path expectations:
- Preferred/canonical: ``from core_orchestrator.mlops_unity_pipeline import ...``
- Compatibility: root ``mlops_unity_pipeline.py`` re-exports this module.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class UnityAssetSpec:
    asset_id: str
    name: str
    asset_type: str
    description: str
    observation_space: dict[str, Any] = field(default_factory=dict)
    action_space: dict[str, Any] = field(default_factory=dict)
    reward_signals: dict[str, Any] = field(default_factory=dict)
    extra_context: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class RLTrainingConfig:
    algorithm: str = "PPO"
    max_steps: int = 1_000_000
    num_envs: int = 8
    time_scale: float = 20.0
    learning_rate: float = 3e-4
    batch_size: int = 1024
    checkpoint_interval: int = 100_000
    offline_dataset_path: str | None = None
    mlagents_config_path: str | None = None
    vertex_project: str | None = None
    vertex_region: str = "us-central1"
    vertex_model_display_name: str | None = None
    tags: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class TrainingJob:
    job_id: str
    asset_spec: UnityAssetSpec
    rl_config: RLTrainingConfig
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "pending"
    unity_project_path: str | None = None
    output_dir: str = "artifacts/mlops"
    trained_model_path: str | None = None
    vertex_model_resource_name: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


@dataclass(slots=True)
class TrainingSchedule:
    schedule_id: str
    cron_expression: str
    asset_specs: list[UnityAssetSpec]
    rl_config: RLTrainingConfig
    enabled: bool = True
    max_concurrent_jobs: int = 1
    webhook_url: str | None = None
    last_run_at: datetime | None = None
    next_run_at: datetime | None = None


class UnityMLOpsOrchestrator:
    """End-to-end orchestrator for Unity build/train/register workflow."""

    def __init__(
        self,
        workspace_root: str | Path = "artifacts/mlops",
        *,
        workspace_dir: str | Path | None = None,
        unity_build_command: list[str] | None = None,
        mlagents_train_command: list[str] | None = None,
    ) -> None:
        selected_workspace = workspace_dir if workspace_dir is not None else workspace_root
        self.workspace_root = Path(selected_workspace).resolve()
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.unity_build_command = unity_build_command
        self.mlagents_train_command = mlagents_train_command

    async def execute_training_job(self, job: TrainingJob) -> TrainingJob:
        job.status = "running"
        job_dir = (self.workspace_root / job.job_id).resolve()
        job_dir.mkdir(parents=True, exist_ok=True)

        try:
            generated_code = await self._generate_unity_asset(job, job_dir)
            build_artifact = await self._build_unity_environment(job, generated_code, job_dir)
            model_path, metrics = await self._train_policy(job, build_artifact, job_dir)

            job.trained_model_path = str(model_path)
            job.metrics = metrics
            job.status = "completed"
            return job
        except Exception as exc:  # pragma: no cover
            job.status = "failed"
            job.error_message = str(exc)
            return job

    async def _generate_unity_asset(self, job: TrainingJob, job_dir: Path) -> Path:
        code_path = (job_dir / f"{job.asset_spec.name}.cs").resolve()
        code_path.write_text(
            "\n".join(
                [
                    "using UnityEngine;",
                    f"public class {job.asset_spec.name} : MonoBehaviour",
                    "{",
                    f"    // {job.asset_spec.description}",
                    "}",
                ]
            ),
            encoding="utf-8",
        )
        await asyncio.sleep(0)
        return code_path

    async def _build_unity_environment(self, job: TrainingJob, generated_code: Path, job_dir: Path) -> Path:
        build_artifact = (job_dir / f"{job.asset_spec.name}.x86_64").resolve()
        build_artifact.write_bytes(b"unity-build-placeholder")

        if self.unity_build_command:
            subprocess.run(
                [*self.unity_build_command, str(generated_code.resolve()), str(build_artifact.resolve())],
                check=True,
                capture_output=True,
                text=True,
            )

        await asyncio.sleep(0)
        return build_artifact

    async def _train_policy(
        self,
        job: TrainingJob,
        unity_build_path: Path,
        job_dir: Path,
    ) -> tuple[Path, dict[str, Any]]:
        config_path = (job_dir / "mlagents_config.json").resolve()
        config_path.write_text(
            json.dumps(
                {
                    "algorithm": job.rl_config.algorithm,
                    "max_steps": job.rl_config.max_steps,
                    "num_envs": job.rl_config.num_envs,
                    "time_scale": job.rl_config.time_scale,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

        model_path = (job_dir / f"{job.asset_spec.name}-{job.job_id}.onnx").resolve()
        if self.mlagents_train_command:
            env = os.environ.copy()
            env["UNITY_BUILD_PATH"] = str(unity_build_path.resolve())
            env["MLAGENTS_CONFIG_PATH"] = str(config_path.resolve())
            env["MLAGENTS_OUTPUT_MODEL"] = str(model_path.resolve())
            subprocess.run(
                self.mlagents_train_command,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            if not model_path.exists():
                raise RuntimeError("External training command did not produce MLAGENTS_OUTPUT_MODEL")
        else:
            model_path.write_bytes(b"placeholder-onnx-model")

        metrics = {
            "algorithm": job.rl_config.algorithm,
            "max_steps": job.rl_config.max_steps,
            "num_envs": job.rl_config.num_envs,
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        await asyncio.sleep(0)
        return model_path, metrics


class TrainingScheduler:
    """Cron-driven scheduler that can run one cycle or continuously."""

    def __init__(
        self,
        orchestrator: UnityMLOpsOrchestrator,
        poll_interval_seconds: int = 30,
    ) -> None:
        self.orchestrator = orchestrator
        self.poll_interval_seconds = poll_interval_seconds
        self._schedules: dict[str, TrainingSchedule] = {}
        self._next_run: dict[str, datetime] = {}
        self._active_runs: set[asyncio.Task[None]] = set()

    def add_schedule(self, schedule: TrainingSchedule) -> None:
        if not schedule.asset_specs:
            raise ValueError("TrainingSchedule.asset_specs cannot be empty")
        self._schedules[schedule.schedule_id] = schedule
        schedule.next_run_at = _next_cron_time(schedule.cron_expression, datetime.now(timezone.utc))
        self._next_run[schedule.schedule_id] = schedule.next_run_at

    def _is_due(self, schedule: TrainingSchedule, now: datetime) -> bool:
        checkpoint_dir = (self.orchestrator.workspace_root / ".scheduler").resolve()
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = checkpoint_dir / f"{schedule.schedule_id}.json"

        if not checkpoint_path.exists():
            checkpoint_path.write_text(
                json.dumps({"last_run_ts": now.astimezone(timezone.utc).isoformat()}),
                encoding="utf-8",
            )
            return True

        try:
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            checkpoint = {}

        last_run_ts = checkpoint.get("last_run_ts")
        if not last_run_ts:
            checkpoint_path.write_text(
                json.dumps({"last_run_ts": now.astimezone(timezone.utc).isoformat()}),
                encoding="utf-8",
            )
            return True

        last_run_at = datetime.fromisoformat(last_run_ts)
        if last_run_at.tzinfo is None:
            last_run_at = last_run_at.replace(tzinfo=timezone.utc)

        next_due = _next_cron_time(schedule.cron_expression, last_run_at.astimezone(timezone.utc))
        if next_due <= now.astimezone(timezone.utc):
            checkpoint_path.write_text(
                json.dumps({"last_run_ts": next_due.isoformat()}),
                encoding="utf-8",
            )
            return True

        return False

    async def run_once(self) -> None:
        now = datetime.now(timezone.utc)
        for schedule in self._schedules.values():
            if not schedule.enabled:
                continue
            due = self._next_run.get(schedule.schedule_id)
            if due is None or now < due:
                continue

            schedule.last_run_at = now
            schedule.next_run_at = _next_cron_time(schedule.cron_expression, due)
            self._next_run[schedule.schedule_id] = schedule.next_run_at

            tasks = [
                asyncio.create_task(self._run_scheduled_job(schedule, asset_spec))
                for asset_spec in schedule.asset_specs
            ]
            self._active_runs.update(tasks)
            for task in tasks:
                task.add_done_callback(self._active_runs.discard)
            await asyncio.gather(*tasks)

    async def run_forever(self) -> None:
        while True:
            await self.run_once()
            await asyncio.sleep(self.poll_interval_seconds)

    async def shutdown(self) -> None:
        if self._active_runs:
            await asyncio.gather(*self._active_runs, return_exceptions=True)

    async def _run_scheduled_job(self, schedule: TrainingSchedule, asset_spec: UnityAssetSpec) -> None:
        job = TrainingJob(
            job_id=f"{schedule.schedule_id}-{asset_spec.asset_id}-{int(datetime.now(timezone.utc).timestamp())}",
            asset_spec=asset_spec,
            rl_config=schedule.rl_config,
        )
        await self.orchestrator.execute_training_job(job)


def _parse_cron_field(field: str, min_value: int, max_value: int) -> set[int]:
    allowed: set[int] = set()
    for part in field.split(","):
        token = part.strip()
        if not token:
            continue

        if token == "*":
            allowed.update(range(min_value, max_value + 1))
            continue

        if "/" in token:
            base_token, step_token = token.split("/", 1)
            step = int(step_token)
            if base_token in {"", "*"}:
                start, end = min_value, max_value
            elif "-" in base_token:
                start_s, end_s = base_token.split("-", 1)
                start, end = int(start_s), int(end_s)
            else:
                start, end = int(base_token), max_value
            allowed.update(v for v in range(start, end + 1) if (v - start) % step == 0)
            continue

        if "-" in token:
            start_s, end_s = token.split("-", 1)
            allowed.update(range(int(start_s), int(end_s) + 1))
            continue

        allowed.add(int(token))

    return {v for v in allowed if min_value <= v <= max_value}


def _next_cron_time(cron_expression: str, base: datetime) -> datetime:
    """Compute next UTC run time after ``base`` for 5-field cron expressions."""

    fields = cron_expression.split()
    if len(fields) != 5:
        raise ValueError("Expected 5-field cron expression: minute hour day month weekday")

    minute_field, hour_field, day_field, month_field, weekday_field = fields
    allowed_minutes = _parse_cron_field(minute_field, 0, 59)
    allowed_hours = _parse_cron_field(hour_field, 0, 23)
    allowed_days = _parse_cron_field(day_field, 1, 31)
    allowed_months = _parse_cron_field(month_field, 1, 12)
    allowed_weekdays = _parse_cron_field(weekday_field, 0, 6)

    candidate = base.astimezone(timezone.utc).replace(second=0, microsecond=0) + timedelta(minutes=1)
    for _ in range(60 * 24 * 366):
        cron_weekday = (candidate.weekday() + 1) % 7
        if (
            candidate.minute in allowed_minutes
            and candidate.hour in allowed_hours
            and candidate.day in allowed_days
            and candidate.month in allowed_months
            and cron_weekday in allowed_weekdays
        ):
            return candidate
        candidate += timedelta(minutes=1)

    raise RuntimeError(f"Unable to find next run time for cron expression: {cron_expression}")


__all__ = [
    "RLTrainingConfig",
    "TrainingJob",
    "TrainingSchedule",
    "TrainingScheduler",
    "UnityAssetSpec",
    "UnityMLOpsOrchestrator",
    "_next_cron_time",
]

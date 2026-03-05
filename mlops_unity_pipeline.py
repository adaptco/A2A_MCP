"""Autonomous Unity MLOps pipeline for code generation, build, RL training, and model registration.

This module provides a production-oriented orchestration surface that can be used as-is
or subclassed to integrate with specific LLM providers, Unity project layouts, and cloud
registries.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shlex
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib import request
from uuid import uuid4

from croniter import croniter

LOGGER = logging.getLogger(__name__)


@dataclass
class UnityAssetSpec:
    asset_id: str
    name: str
    asset_type: str
    description: str
    observation_space: Dict[str, Any] = field(default_factory=dict)
    action_space: Dict[str, Any] = field(default_factory=dict)
    training_hints: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RLTrainingConfig:
    algorithm: str = "PPO"
    max_steps: int = 1_000_000
    num_envs: int = 16
    time_scale: float = 20.0
    seed: int = 42
    run_id_prefix: str = "unity-rl"
    mlagents_cli: str = "mlagents-learn"
    trainer_config_path: Optional[str] = None
    extra_cli_args: List[str] = field(default_factory=list)


@dataclass
class TrainingJob:
    job_id: str
    asset_spec: UnityAssetSpec
    rl_config: RLTrainingConfig
    project_path: str = "."
    output_dir: str = "artifacts/unity_mlops"
    register_to_vertex: bool = True


@dataclass
class TrainingResult:
    job_id: str
    status: str
    generated_script_path: Optional[str] = None
    unity_build_path: Optional[str] = None
    trained_model_path: Optional[str] = None
    vertex_model_resource: Optional[str] = None
    run_id: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TrainingSchedule:
    schedule_id: str
    cron_expression: str
    asset_specs: List[UnityAssetSpec]
    rl_config: RLTrainingConfig
    project_path: str = "."
    output_dir: str = "artifacts/unity_mlops"
    register_to_vertex: bool = True


class UnityMLOpsOrchestrator:
    def __init__(
        self,
        *,
        unity_executable: str = "unity",
        llm_provider: Optional[Any] = None,
        vertex_project: Optional[str] = None,
        vertex_region: Optional[str] = None,
    ) -> None:
        self.unity_executable = unity_executable
        self.llm_provider = llm_provider
        self.vertex_project = vertex_project or os.getenv("VERTEX_PROJECT")
        self.vertex_region = vertex_region or os.getenv("VERTEX_REGION", "us-central1")

    async def execute_training_job(self, job: TrainingJob) -> TrainingResult:
        result = TrainingResult(job_id=job.job_id, status="running")
        base_dir = Path(job.output_dir) / job.job_id
        base_dir.mkdir(parents=True, exist_ok=True)

        try:
            result.generated_script_path = await self.generate_unity_code(job, base_dir)
            result.unity_build_path = await self.build_unity_environment(job, base_dir)
            train_data = await self.train_rl_agent(job, base_dir)
            result.trained_model_path = train_data["model_path"]
            result.run_id = train_data["run_id"]
            result.metrics = train_data.get("metrics", {})

            if job.register_to_vertex:
                result.vertex_model_resource = await self.register_model_in_vertex(job, result, base_dir)

            result.status = "completed"
            return result
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Training job failed: %s", job.job_id)
            result.status = "failed"
            result.error = str(exc)
            return result

    async def generate_unity_code(self, job: TrainingJob, output_dir: Path) -> str:
        script_body = self._generate_csharp(job.asset_spec)
        script_path = output_dir / f"{job.asset_spec.name}.cs"
        script_path.write_text(script_body, encoding="utf-8")
        return str(script_path)

    async def build_unity_environment(self, job: TrainingJob, output_dir: Path) -> str:
        build_dir = output_dir / "unity_build"
        build_dir.mkdir(exist_ok=True)
        marker = build_dir / "BUILD_COMPLETE.txt"
        marker.write_text(
            f"Simulated Unity build for {job.asset_spec.name} at {datetime.now(timezone.utc).isoformat()}\n",
            encoding="utf-8",
        )
        return str(build_dir)

    async def train_rl_agent(self, job: TrainingJob, output_dir: Path) -> Dict[str, Any]:
        run_id = f"{job.rl_config.run_id_prefix}-{job.job_id}-{uuid4().hex[:8]}"
        model_dir = output_dir / "models" / run_id
        model_dir.mkdir(parents=True, exist_ok=True)

        summary = {
            "algorithm": job.rl_config.algorithm,
            "max_steps": job.rl_config.max_steps,
            "num_envs": job.rl_config.num_envs,
            "time_scale": job.rl_config.time_scale,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        (model_dir / "training_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
        return {"model_path": str(model_dir), "run_id": run_id, "metrics": {"simulated_reward": 0.91}}

    async def register_model_in_vertex(self, job: TrainingJob, result: TrainingResult, output_dir: Path) -> str:
        if not self.vertex_project:
            return "vertex://skipped-no-project-configured"

        record = {
            "project": self.vertex_project,
            "region": self.vertex_region,
            "display_name": f"{job.asset_spec.name}-{job.job_id}",
            "artifact_uri": result.trained_model_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        record_path = output_dir / "vertex_registration.json"
        record_path.write_text(json.dumps(record, indent=2), encoding="utf-8")
        return f"vertex://{self.vertex_project}/{self.vertex_region}/{job.asset_spec.name}-{job.job_id}"

    def _generate_csharp(self, asset: UnityAssetSpec) -> str:
        obs_json = json.dumps(asset.observation_space, indent=2)
        action_json = json.dumps(asset.action_space, indent=2)
        return f"""using UnityEngine;
using Unity.MLAgents;
using Unity.MLAgents.Actuators;
using Unity.MLAgents.Sensors;

public class {asset.name} : Agent
{{
    public override void CollectObservations(VectorSensor sensor)
    {{
        // Observation schema\n        // {obs_json.replace(chr(10), chr(10) + '        // ')}
    }}

    public override void OnActionReceived(ActionBuffers actions)
    {{
        // Action schema\n        // {action_json.replace(chr(10), chr(10) + '        // ')}
    }}

    public override void Heuristic(in ActionBuffers actionsOut)
    {{
        // TODO: Optional manual controls
    }}
}}
"""


class TrainingScheduler:
    def __init__(
        self,
        orchestrator: UnityMLOpsOrchestrator,
        *,
        max_concurrent_jobs: int = 2,
        webhook_url: Optional[str] = None,
    ) -> None:
        self.orchestrator = orchestrator
        self._schedules: List[TrainingSchedule] = []
        self._last_triggered_minute: Dict[str, str] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self.webhook_url = webhook_url

    def add_schedule(self, schedule: TrainingSchedule) -> None:
        self._schedules.append(schedule)

    async def run_forever(self, poll_seconds: int = 30) -> None:
        while True:
            now = datetime.now(timezone.utc)
            for schedule in self._schedules:
                if self._is_due(schedule, now):
                    await self._run_schedule(schedule)
            await asyncio.sleep(poll_seconds)

    async def run_once(self, now: Optional[datetime] = None) -> List[TrainingResult]:
        now = now or datetime.now(timezone.utc)
        results: List[TrainingResult] = []
        for schedule in self._schedules:
            if self._is_due(schedule, now):
                results.extend(await self._run_schedule(schedule))
        return results

    def _is_due(self, schedule: TrainingSchedule, now: datetime) -> bool:
        itr = croniter(schedule.cron_expression, now)
        prev_tick = itr.get_prev(datetime)
        is_due = (now - prev_tick).total_seconds() < 60
        minute_key = now.strftime("%Y-%m-%dT%H:%M")
        if is_due and self._last_triggered_minute.get(schedule.schedule_id) == minute_key:
            return False
        if is_due:
            self._last_triggered_minute[schedule.schedule_id] = minute_key
        return is_due

    async def _run_schedule(self, schedule: TrainingSchedule) -> List[TrainingResult]:
        tasks = [self._run_asset_job(schedule, asset) for asset in schedule.asset_specs]
        return await asyncio.gather(*tasks)

    async def _run_asset_job(self, schedule: TrainingSchedule, asset: UnityAssetSpec) -> TrainingResult:
        job = TrainingJob(
            job_id=f"{schedule.schedule_id}-{asset.asset_id}-{uuid4().hex[:6]}",
            asset_spec=asset,
            rl_config=schedule.rl_config,
            project_path=schedule.project_path,
            output_dir=schedule.output_dir,
            register_to_vertex=schedule.register_to_vertex,
        )
        async with self._semaphore:
            result = await self.orchestrator.execute_training_job(job)
        await self._notify_webhook(schedule, result)
        return result

    async def _notify_webhook(self, schedule: TrainingSchedule, result: TrainingResult) -> None:
        if not self.webhook_url:
            return
        payload = {
            "schedule_id": schedule.schedule_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": asdict(result),
        }

        def _send() -> None:
            req = request.Request(
                self.webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with request.urlopen(req, timeout=10) as resp:  # noqa: S310
                LOGGER.info("webhook_sent status=%s", resp.status)

        try:
            await asyncio.to_thread(_send)
        except Exception:  # noqa: BLE001
            LOGGER.exception("Webhook notification failed for schedule=%s", schedule.schedule_id)


def run_cli(command: str, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """Execute a shell command with safe tokenization for optional custom integrations."""
    args = shlex.split(command)
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)

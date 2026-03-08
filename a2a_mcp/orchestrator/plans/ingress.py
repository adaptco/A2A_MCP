"""Plan-ingress scheduler helpers.

This module intentionally lives outside `.github/workflows/` so workflow linting
only processes workflow YAML files.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any


async def run_daily_ingest_job(
    plan_ingress: Callable[[str, Any], Awaitable[Any]],
    background_tasks_factory: Callable[[], Any],
    *,
    plan_id: str = "daily-game-design-run",
) -> Any:
    """Invoke plan ingress for the daily plan id."""
    return await plan_ingress(plan_id, background_tasks_factory())


def register_daily_ingress_scheduler(
    scheduler: Any,
    plan_ingress: Callable[[str, Any], Awaitable[Any]],
    background_tasks_factory: Callable[[], Any],
    *,
    interval_seconds: int = 86400,
    schedule_name: str = "daily_plan",
    plan_id: str = "daily-game-design-run",
) -> None:
    """Register and start a recurring plan ingress task on application startup."""

    async def daily_ingest_job() -> None:
        await run_daily_ingest_job(
            plan_ingress,
            background_tasks_factory,
            plan_id=plan_id,
        )

    scheduler.schedule_every(schedule_name, daily_ingest_job, interval_seconds=interval_seconds)
    asyncio.create_task(scheduler.run_forever())

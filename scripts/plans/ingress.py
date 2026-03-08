from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Protocol

from fastapi import BackgroundTasks, FastAPI


class SchedulerProtocol(Protocol):
    def schedule_every(
        self,
        name: str,
        callback: Callable[[], Awaitable[None]],
        interval_seconds: int,
    ) -> None:
        ...

    async def run_forever(self) -> None:
        ...


def wire_daily_plan_ingress(
    app: FastAPI,
    scheduler: SchedulerProtocol,
    plan_ingress: Callable[[str, BackgroundTasks], Awaitable[None]],
    plan_id: str = "daily-game-design-run",
) -> None:
    """Attach a startup hook that schedules recurring plan ingress."""

    @app.on_event("startup")
    async def startup_event() -> None:
        async def daily_ingest_job() -> None:
            await plan_ingress(plan_id, BackgroundTasks())

        scheduler.schedule_every("daily_plan", daily_ingest_job, interval_seconds=86400)
        asyncio.create_task(scheduler.run_forever())

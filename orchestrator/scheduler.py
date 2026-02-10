# simple scheduler for local MCP (async, no external dependency)
import asyncio
from typing import Callable, Dict
from datetime import datetime, timedelta

class SimpleScheduler:
    def __init__(self):
        self._jobs = {}  # job_id -> (next_run, coro_fn, interval_seconds)

    def schedule_every(self, job_id: str, coro_fn: Callable[[], None], interval_seconds: int):
        next_run = datetime.utcnow() + timedelta(seconds=interval_seconds)
        self._jobs[job_id] = {"next_run": next_run, "fn": coro_fn, "interval": interval_seconds}

    async def run_forever(self):
        while True:
            now = datetime.utcnow()
            for job_id, meta in list(self._jobs.items()):
                if meta["next_run"] <= now:
                    # dispatch without awaiting to avoid blocking
                    asyncio.create_task(meta["fn"]())
                    meta["next_run"] = now + timedelta(seconds=meta["interval"])
            await asyncio.sleep(1)

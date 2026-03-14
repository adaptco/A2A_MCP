@app.on_event("startup")
async def startup_event():
    async def daily_ingest_job():
        # choose one or more plans to run daily
        plan_id = "daily-game-design-run"
        # call local ingress endpoint handler directly to avoid extra HTTP call
        await plan_ingress(plan_id, BackgroundTasks())

    # schedule every 24h (86400s)
    SCHED.schedule_every("daily_plan", daily_ingest_job, interval_seconds=86400)
    # start scheduler loop
    import asyncio
    asyncio.create_task(SCHED.run_forever())

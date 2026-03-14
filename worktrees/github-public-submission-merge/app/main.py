from fastapi import FastAPI

from .routes import agent, health, webhooks

app = FastAPI(title="Task Middleware")
app.include_router(health.router)
app.include_router(webhooks.router)
app.include_router(agent.router)

"""HTTP MCP gateway exposing native MCP transport and `/tools/call` compatibility."""

from __future__ import annotations

import os
import uuid
from typing import Any

from bootstrap import bootstrap_paths

bootstrap_paths()

from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from mcp.server.fastmcp import FastMCP
from app.mcp_tooling import register_tools, call_tool_by_name
from app.security.oidc import validate_startup_oidc_requirements
from orchestrator.logging import setup_logging

setup_logging()
validate_startup_oidc_requirements()

class ToolCallRequest(BaseModel):
    """Compatibility payload for legacy `/tools/call` clients."""

    tool_name: str = Field(..., min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


mcp = FastMCP("A2A_Orchestrator_HTTP")
register_tools(mcp)

# Attempt to get ASGI app from FastMCP (API varies across versions)
if hasattr(mcp, "http_app"):
    mcp_http_app = mcp.http_app(transport="streamable-http", path="/")
elif hasattr(mcp, "app"):
    mcp_http_app = mcp.app
else:
    # Fallback to the object itself if it is ASGI-compatible
    mcp_http_app = mcp

app = FastAPI(
    title="A2A MCP Gateway",
    version="1.0.0",
    lifespan=getattr(mcp_http_app, "lifespan", None),
)

# Path `/mcp` is preserved externally while FastMCP handles root path internally.
app.mount("/mcp", mcp_http_app)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> dict[str, str]:
    return {"status": "ready"}


@app.post("/tools/call")
async def tools_call(
    request: Request,
    payload: ToolCallRequest,
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    try:
        result = call_tool_by_name(
            tool_name=payload.tool_name,
            arguments=payload.arguments,
            authorization_header=authorization,
            request_id=request_id
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=404, 
            detail={"error": "tool_not_found", "message": str(exc), "request_id": request_id}
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=400, 
            detail={"error": "execution_failed", "message": str(exc), "request_id": request_id}
        ) from exc

    ok = True
    if isinstance(result, dict) and result.get("ok") is False:
        ok = False

    return {
        "tool_name": payload.tool_name,
        "ok": ok,
        "result": result,
        "request_id": request_id
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.mcp_gateway:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=False,
    )

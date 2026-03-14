"""
mcp_servers/gemini_control.py — Gemini OS MCP HTTP Control Layer
=================================================================
FastAPI server that:
  1. Serves indexed artifacts from data/vector_lake/ as MCP resources
  2. Accepts Gemini API calls as the AI control plane for agent routing
  3. Routes to the galaxy of UI frontends (ui/, apps/, frontend/)

Run:
    uvicorn mcp_servers.gemini_control:app --port 9090 --reload

Environment variables:
    GEMINI_API_KEY   — Gemini API key (required for /api/generate)
    GEMINI_MODEL     — Model override (default: gemini-2.0-flash)
    VECTOR_LAKE_DIR  — Vector lake path (default: data/vector_lake)
    MCP_PORT         — Port (default: 9090)
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import time
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Gemini OS — MCP Control Layer",
    description=(
        "HTTP MCP endpoint for the A2A_MCP monorepo. "
        "Serves indexed artifacts as MCP resources and routes Gemini API calls "
        "to the agent pipeline — the galaxy of UI sites."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

VECTOR_LAKE_DIR = pathlib.Path(os.environ.get("VECTOR_LAKE_DIR", "data/vector_lake"))
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Galaxy of UI sites in the monorepo
UI_SITES: dict[str, str] = {
    "cockpit":  "ui/cockpit",
    "frontend": "frontend",
    "app":      "app",
    "apps":     "apps",
    "chatgpt":  "chatgpt-app",
    "base44":   "base44",
    "web-pet":  "web-pet-kernel",
    "office":   "OfficeDocker",
}


def _load_snapshot(path: pathlib.Path) -> dict[str, Any]:
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return {}


def _snapshot_items(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    artifacts = snapshot.get("artifacts")
    if isinstance(artifacts, list) and artifacts:
        return [item for item in artifacts if isinstance(item, dict)]

    vectors = snapshot.get("vectors")
    if isinstance(vectors, list):
        return [item for item in vectors if isinstance(item, dict)]

    return [item for item in artifacts or [] if isinstance(item, dict)]


# ─── MCP Resource endpoints ──────────────────────────────────────────────────

@app.get("/mcp/resources", summary="List MCP artifact resources from the data lake")
async def list_mcp_resources() -> dict:
    snap = _load_snapshot(VECTOR_LAKE_DIR / "snapshot.json")
    items = _snapshot_items(snap)
    resources = []
    for a in items:
        path = a.get("path", "")
        resources.append({
            "uri": f"mcp://a2a/{path.replace(os.sep, '/')}",
            "name": pathlib.Path(path).name if path else "unknown",
            "fingerprint": a.get("fingerprint"),
            "mimeType": "text/plain",
        })
    return {
        "resources": resources,
        "count": len(resources),
        "snapshot_timestamp": snap.get("timestamp"),
        "commit": snap.get("commit"),
    }


@app.get("/mcp/resources/{resource_id:path}", summary="Get a specific MCP resource")
async def get_mcp_resource(resource_id: str) -> dict:
    snap = _load_snapshot(VECTOR_LAKE_DIR / "snapshot.json")
    normalized_resource_id = resource_id.replace("\\", "/")
    for a in _snapshot_items(snap):
        path = a.get("path", "")
        normalized_path = path.replace("\\", "/")
        if normalized_resource_id == normalized_path:
            p = pathlib.Path(path)
            content = None
            if p.exists() and p.stat().st_size < 100_000:
                try:
                    content = p.read_text(errors="replace")
                except Exception:
                    content = "<binary>"
            return {"uri": f"mcp://a2a/{resource_id}", "content": content, "fingerprint": a.get("fingerprint")}
    raise HTTPException(status_code=404, detail=f"Resource not found: {resource_id}")


@app.get("/mcp/telemetry", summary="Latest geodesic telemetry snapshot")
async def get_telemetry() -> dict:
    tel = _load_snapshot(pathlib.Path("output/telemetry_snapshot.json"))
    if not tel:
        raise HTTPException(status_code=404, detail="No telemetry snapshot — run embed + telemetry phases first")
    return tel


# ─── Gemini API control layer ─────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    model: str = GEMINI_MODEL
    system_instruction: str = (
        "You are the Gemini OS control layer for the A2A_MCP monorepo. "
        "Route agent tasks, summarize artifacts, and drive the CI pipeline. "
        "You are the AI control plane for the galaxy of UI sites."
    )
    temperature: float = 0.4


@app.post("/api/generate", summary="Invoke Gemini API as the control plane")
async def generate(req: GenerateRequest) -> dict:
    if not GEMINI_API_KEY:
        raise HTTPException(status_code=503, detail="GEMINI_API_KEY not configured")
    try:
        import google.generativeai as genai  # type: ignore
        genai.configure(api_key=GEMINI_API_KEY)
        model = genai.GenerativeModel(
            model_name=req.model,
            system_instruction=req.system_instruction,
        )
        t0 = time.perf_counter()
        response = model.generate_content(
            req.prompt,
            generation_config={"temperature": req.temperature},
        )
        return {"model": req.model, "text": response.text, "latency_ms": int((time.perf_counter() - t0) * 1000)}
    except ImportError:
        raise HTTPException(status_code=503, detail="Install: pip install google-generativeai")
    except Exception as exc:
        log.error("Gemini API error: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc))


# ─── UI galaxy routing ────────────────────────────────────────────────────────

@app.get("/ui", summary="List available UI sites (galaxy of UIs)")
async def list_ui_sites() -> dict:
    sites = [
        {"name": name, "path": path, "exists": pathlib.Path(path).exists()}
        for name, path in UI_SITES.items()
    ]
    return {"ui_sites": sites, "count": len(sites)}


# ─── Health & Index ───────────────────────────────────────────────────────────

@app.get("/", summary="MCP control layer index")
async def index() -> dict:
    snap = _load_snapshot(VECTOR_LAKE_DIR / "snapshot.json")
    items = _snapshot_items(snap)
    return {
        "service": "Gemini OS MCP Control Layer",
        "version": "1.0.0",
        "model": GEMINI_MODEL,
        "vector_lake": str(VECTOR_LAKE_DIR),
        "snapshot_timestamp": snap.get("timestamp", "none"),
        "artifact_count": len(items),
        "endpoints": {
            "resources": "/mcp/resources",
            "telemetry": "/mcp/telemetry",
            "generate":  "/api/generate",
            "ui_galaxy": "/ui",
            "docs":      "/docs",
        },
    }


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "timestamp": time.time()}


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("MCP_PORT", "9090"))
    uvicorn.run("mcp_servers.gemini_control:app", host="0.0.0.0", port=port, reload=True)

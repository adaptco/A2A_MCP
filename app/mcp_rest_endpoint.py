"""FastAPI REST HTTP endpoint for MCP tools.

Exposes the core MCP embedding control plane, world model, agent shell,
and avatar completion as REST HTTP endpoints. This is the production
entry point for the MCP REST API.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

def _load_repo_dotenv(dotenv_path: Optional[Path] = None) -> Path:
    """Load the repo-root .env so local uvicorn startup is deterministic."""
    env_path = dotenv_path or Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=False)
    return env_path


_load_repo_dotenv()

from app.agent_shell import build_agent_shell
from app.world_model_skill import (
    CodestralClient,
    CodestralConfig,
    complete_avatar_tokens,
    program_world_model,
)
from embed_control_plane import (
    ControlPlaneError,
    embed_dispatch_batch,
    embed_lookup,
    embed_status,
    embed_submit,
    route_a2a_intent,
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ── Pydantic request/response models ───────────────────────────

class EmbedSubmitRequest(BaseModel):
    doc_ref: Any
    canonicalizer_id: str = "docling.c14n.v1"
    model_id: str = "mini-embed-v1"
    shard_key: str = ""


class EmbedStatusRequest(BaseModel):
    job_id: str


class EmbedLookupRequest(BaseModel):
    chunk_hash: str
    model_id: str = "mini-embed-v1"


class ChunkItem(BaseModel):
    chunk_hash: str
    text: str = ""
    job_id: str = ""


class EmbedDispatchRequest(BaseModel):
    batch_id: str
    chunks: List[ChunkItem]
    model_id: str = "mini-embed-v1"
    seed_ref: str = ""
    guard_token: str = ""


class IntentRequest(BaseModel):
    intent: str
    payload: Dict[str, Any] = Field(default_factory=dict)


class WorldlineRequest(BaseModel):
    prompt: str
    repository: str = "A2A_MCP"
    commit_sha: str = "HEAD"
    actor: str = "github-actions"
    risk_profile: str = "medium"


class AvatarPrompt(BaseModel):
    avatar_name: str
    system_prompt: str


class AvatarCompleteRequest(BaseModel):
    avatars: List[AvatarPrompt]
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.3


class FimCompleteRequest(BaseModel):
    prompt: str
    suffix: str = ""
    max_tokens: Optional[int] = 256
    temperature: Optional[float] = 0.2
    stop: Optional[List[str]] = None


# ── FastAPI app ─────────────────────────────────────────────────

app = FastAPI(
    title="A2A MCP REST Endpoint",
    description=(
        "REST HTTP interface for MCP embedding tools, world model generation, "
        "agent shell context, and Codestral-powered avatar completion."
    ),
    version="1.0.0",
)


# ── Health probes ───────────────────────────────────────────────

@app.get("/healthz")
async def healthz() -> Dict[str, str]:
    """Liveness probe."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz() -> Dict[str, str]:
    """Readiness probe."""
    codestral = CodestralConfig.from_env()
    return {
        "status": "ready",
        "codestral_configured": str(codestral.is_configured).lower(),
        "llm_model": codestral.model,
    }


# ── Embed control plane endpoints ──────────────────────────────

@app.post("/v1/mcp/embed/submit")
async def api_embed_submit(req: EmbedSubmitRequest) -> Dict[str, Any]:
    """Submit a document for embedding via MCP control plane."""
    try:
        result = embed_submit(
            doc_ref=req.doc_ref,
            canonicalizer_id=req.canonicalizer_id,
            model_id=req.model_id,
            shard_key=req.shard_key,
        )
        return {"ok": True, "result": result}
    except ControlPlaneError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})


@app.post("/v1/mcp/embed/status")
async def api_embed_status(req: EmbedStatusRequest) -> Dict[str, Any]:
    """Check the status of an embedding job."""
    result = embed_status(req.job_id)
    return {"ok": True, "result": result}


@app.post("/v1/mcp/embed/lookup")
async def api_embed_lookup(req: EmbedLookupRequest) -> Dict[str, Any]:
    """Look up an embedded chunk artifact."""
    result = embed_lookup(chunk_hash=req.chunk_hash, model_id=req.model_id)
    return {"ok": True, "result": result}


@app.post("/v1/mcp/embed/dispatch")
async def api_embed_dispatch(req: EmbedDispatchRequest) -> Dict[str, Any]:
    """Dispatch a batch of chunks for embedding."""
    try:
        chunks = [c.model_dump() for c in req.chunks]
        result = embed_dispatch_batch(
            batch_id=req.batch_id,
            chunks=chunks,
            model_id=req.model_id,
            seed_ref=req.seed_ref,
            guard_token=req.guard_token,
        )
        return {"ok": True, "result": result}
    except ControlPlaneError as exc:
        raise HTTPException(status_code=403, detail={"code": exc.code, "message": exc.message})


# ── A2A intent routing ─────────────────────────────────────────

@app.post("/v1/mcp/intent")
async def api_route_intent(req: IntentRequest) -> Dict[str, Any]:
    """Route an A2A intent through the MCP control plane."""
    try:
        result = route_a2a_intent({"intent": req.intent, "payload": req.payload})
        return {"ok": True, "result": result}
    except ControlPlaneError as exc:
        raise HTTPException(status_code=400, detail={"code": exc.code, "message": exc.message})


# ── World model ────────────────────────────────────────────────

@app.post("/v1/mcp/worldline")
async def api_build_worldline(req: WorldlineRequest) -> Dict[str, Any]:
    """Build a worldline block via the five-phase MCP skill lifecycle."""
    try:
        result = program_world_model(
            prompt=req.prompt,
            repository=req.repository,
            commit_sha=req.commit_sha,
            actor=req.actor,
            risk_profile=req.risk_profile,
        )
        return {"ok": True, "result": result}
    except Exception as exc:
        logger.exception("Worldline build failed")
        raise HTTPException(status_code=500, detail={"error": "worldline_build_failed", "message": str(exc)})


# ── Agent shell ────────────────────────────────────────────────

@app.get("/v1/mcp/shell")
async def api_agent_shell() -> Dict[str, Any]:
    """Return the agent shell context (AGENTS.md + Skills.md)."""
    shell = build_agent_shell()
    return {"ok": True, "shell": shell.to_dict()}


# ── Avatar completion ──────────────────────────────────────────

@app.post("/v1/mcp/avatar/complete")
async def api_avatar_complete(req: AvatarCompleteRequest) -> Dict[str, Any]:
    """Generate completion tokens for avatar prompts via Codestral API."""
    config = CodestralConfig.from_env()

    if not config.is_configured:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "codestral_not_configured",
                "message": "LLM_API_KEY or LLM_ENDPOINT environment variables are not set",
            },
        )

    avatar_dicts = [{"avatar_name": a.avatar_name, "system_prompt": a.system_prompt} for a in req.avatars]
    result = await complete_avatar_tokens(avatar_dicts, config)
    return {"ok": True, "result": result}


# ── FIM code completion ────────────────────────────────────────

@app.post("/v1/mcp/fim/complete")
async def api_fim_complete(req: FimCompleteRequest) -> Dict[str, Any]:
    """Fill-in-the-Middle code completion via Codestral FIM API.

    Provide a code prefix (prompt) and optional suffix; the model generates
    the code that fills the gap between them.
    """
    config = CodestralConfig.from_env()

    if not config.is_configured:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "codestral_not_configured",
                "message": "LLM_API_KEY or CODESTRAL_FIM_ENDPOINT not set",
            },
        )

    client = CodestralClient(config)
    result = await client.fim_complete(
        prompt=req.prompt,
        suffix=req.suffix,
        max_tokens=req.max_tokens,
        temperature=req.temperature,
        stop=req.stop,
    )

    if "error" in result:
        raise HTTPException(
            status_code=502,
            detail={"error": result["error"], "message": result.get("message", "")},
        )

    return {"ok": True, "result": result}


# ── Entry point ────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.mcp_rest_endpoint:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=False,
    )

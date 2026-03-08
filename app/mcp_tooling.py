"""Protected MCP ingestion tooling with deterministic token shaping."""

from __future__ import annotations

import os
import hashlib
import json
from typing import Any, Callable

import jwt

from world_foundation_model import (
    build_coding_agent_avatar_cast,
    build_world_foundation_model,
)
from app.security.avatar_token_shape import AvatarTokenShapeError, shape_avatar_token_stream
from orchestrator.telemetry_service import TelemetryService


MAX_AVATAR_TOKENS = 4096

# Initialize telemetry service (placeholder if not fully configured)
try:
    from orchestrator.telemetry_service import get_telemetry_service
    TELEMETRY = get_telemetry_service()
except (ImportError, RuntimeError):
    TELEMETRY = TelemetryService()

def verify_github_oidc_token(token: str) -> dict[str, Any]:
    if not token:
        raise ValueError("Invalid OIDC token")

    audience = os.getenv("OIDC_AUDIENCE", "").strip()
    if not audience:
        if os.getenv("ENV") == "production":
            raise ValueError("OIDC audience is not configured")
        audience = "https://github.com/adaptco-main"

    issuer = os.getenv("OIDC_ISSUER", "https://token.actions.githubusercontent.com").strip()
    jwks_url = os.getenv(
        "OIDC_JWKS_URL", "https://token.actions.githubusercontent.com/.well-known/jwks"
    ).strip()

    jwks_client = jwt.PyJWKClient(jwks_url)
    signing_key = jwks_client.get_signing_key_from_jwt(token).key
    claims = jwt.decode(
        token,
        signing_key,
        algorithms=["RS256"],
        audience=audience,
        issuer=issuer,
    )

    repository = str(claims.get("repository", "")).strip()
    if not repository:
        raise ValueError("OIDC token missing repository claim")

    return claims


def ingest_repository_data(
    snapshot: dict[str, Any],
    authorization: str,
    verifier: Any | None = None,
) -> dict[str, Any]:
    """Protected ingestion path for repository snapshots."""
    auth_res = _extract_bearer_token(authorization)
    if not auth_res["ok"]:
        return auth_res

    verifier_fn = verifier or verify_github_oidc_token
    try:
        claims = verifier_fn(auth_res["token"])
    except Exception as e:
        return {"ok": False, "error": {"code": "AUTH_INVALID", "message": str(e)}}

    repository = str(claims.get("repository", "")).strip()
    snapshot_repository = str(snapshot.get("repository", "")).strip()

    if snapshot_repository and snapshot_repository != repository:
        return {
            "ok": False,
            "error": {
                "code": "REPOSITORY_CLAIM_MISMATCH",
                "message": "Snapshot repository does not match verified token claim",
                "details": {"snapshot_repository": snapshot_repository, "token_repository": repository},
            },
        }

    return {
        "ok": True,
        "data": {
            "repository": repository,
            "execution_hash": _repository_execution_hash(repository, snapshot),
        },
    }


def ingest_avatar_token_stream(
    payload: dict[str, Any],
    authorization: str,
    verifier: Any | None = None,
) -> dict[str, Any]:
    """Protected ingestion path for avatar token payloads before model execution."""
    auth_res = _extract_bearer_token(authorization)
    if not auth_res["ok"]:
        return auth_res

    verifier_fn = verifier or verify_github_oidc_token
    try:
        claims = verifier_fn(auth_res["token"])
    except Exception as e:
        return {"ok": False, "error": {"code": "AUTH_INVALID", "message": str(e)}}

    repository = str(claims.get("repository", "")).strip()

    namespace = str(payload.get("namespace") or f"avatar::{repository}").strip()
    max_tokens = int(payload.get("max_tokens", MAX_AVATAR_TOKENS))
    raw_tokens = payload.get("tokens", [])

    try:
        shaped = shape_avatar_token_stream(
            raw_tokens=raw_tokens,
            namespace=namespace,
            max_tokens=max_tokens,
            fingerprint_seed=repository,
        )
    except AvatarTokenShapeError as exc:
        return {"ok": False, "error": exc.to_dict()}

    return {"ok": True, "data": shaped.to_dict()}


def build_local_world_foundation_model(
    prompt: str,
    repository: str,
    commit_sha: str,
    actor: str = "api_user",
    cluster_count: int = 4,
    risk_profile: str = "medium",
) -> dict[str, Any]:
    """Build world foundation model payloads for root-repo MCP ingestion."""
    block = build_world_foundation_model(
        prompt=prompt,
        repository=repository,
        commit_sha=commit_sha,
        actor=actor,
        cluster_count=cluster_count,
        risk_profile=risk_profile,
    )
    return {"ok": True, "data": block}


def get_coding_agent_avatar_cast() -> dict[str, Any]:
    """Expose embodied avatar bindings for coding agents."""
    return {"ok": True, "data": build_coding_agent_avatar_cast()}


def _extract_bearer_token(authorization: str | None) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        return {
            "ok": False,
            "error": {
                "code": "AUTH_BEARER_MISSING",
                "message": "Missing or malformed bearer token",
                "details": {},
            },
            "token": None,
        }

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        return {
            "ok": False,
            "error": {
                "code": "AUTH_BEARER_EMPTY",
                "message": "Bearer token is empty",
                "details": {},
            },
            "token": None,
        }

    return {"ok": True, "error": None, "token": token}


def _repository_execution_hash(repository: str, snapshot: dict[str, Any]) -> str:
    digest = hashlib.sha256()
    digest.update(repository.encode("utf-8"))
    digest.update(json.dumps(snapshot, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    return digest.hexdigest()


# --- Registry and Dispatch Logic ---

_TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "ingest_repository_data": {
        "func": ingest_repository_data,
        "protected": True
    },
    "ingest_avatar_token_stream": {
        "func": ingest_avatar_token_stream,
        "protected": True
    },
    "build_local_world_foundation_model": {
        "func": build_local_world_foundation_model,
        "protected": False,
    },
    "get_coding_agent_avatar_cast": {
        "func": get_coding_agent_avatar_cast,
        "protected": False,
    },
}

def register_tools(mcp: Any) -> None:
    """Register all tools in the registry with the FastMCP instance."""
    for name, spec in _TOOL_REGISTRY.items():
        mcp.tool(name=name)(spec["func"])

def call_tool_by_name(
    tool_name: str, 
    arguments: dict[str, Any], 
    authorization_header: str | None = None,
    request_id: str | None = None
) -> dict[str, Any] | str:
    """Dispatches a tool call by name with security enforcement."""
    spec = _TOOL_REGISTRY.get(tool_name)
    if spec is None:
        raise KeyError(f"unknown tool: {tool_name}")

    payload = dict(arguments or {})
    
    # Inject authorization if required
    if spec["protected"]:
        if "authorization" not in payload and authorization_header:
            payload["authorization"] = authorization_header
        
        if not payload.get("authorization"):
            return {
                "ok": False, 
                "error": {
                    "code": "UNAUTHORIZED", 
                    "message": "Missing authorization for protected tool",
                    "request_id": request_id
                }
            }

    # Optional request_id injection if tool supports it
    import inspect
    sig = inspect.signature(spec["func"])
    if "request_id" in sig.parameters:
        payload["request_id"] = request_id

    try:
        return spec["func"](**payload)
    except Exception as e:
        return {
            "ok": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": str(e),
                "request_id": request_id
            }
        }

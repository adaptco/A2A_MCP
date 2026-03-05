from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

import jwt

LOGGER = logging.getLogger(__name__)


class OIDCAuthError(Exception):
    """Authentication failure that is safe to return to clients."""


class OIDCClaimError(OIDCAuthError):
    """Claim validation failure that is safe to return to clients."""


class RejectionReason(str, Enum):
    CLAIM_MISMATCH = "claim_mismatch"
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_VECTOR = "invalid_vector"


@dataclass(frozen=True)
class IngestionValidationResult:
    accepted: bool
    reason: RejectionReason | None = None


def validate_ingestion_claims(
    client_id: str,
    avatar_id: str,
    claims: Mapping[str, Any],
    token_vector: list[float],
    projected_token_total: int,
    quota: int,
) -> IngestionValidationResult:
    """
    Validates ingestion claims against the verified OIDC token and quotas.
    """
    # 1. Claim Mismatch (Identity Verification)
    # Using 'repository' as client_id and 'actor' as avatar_id for GitHub OIDC
    if claims.get("repository") != client_id or claims.get("actor") != avatar_id:
        return IngestionValidationResult(False, RejectionReason.CLAIM_MISMATCH)

    # 2. Invalid Vector (Structural Integrity)
    if not token_vector or any(not isinstance(v, (int, float)) for v in token_vector):
        return IngestionValidationResult(False, RejectionReason.INVALID_VECTOR)

    # 3. Quota Exceeded (Resource Management)
    if projected_token_total > quota:
        return IngestionValidationResult(False, RejectionReason.QUOTA_EXCEEDED)

    return IngestionValidationResult(True)


@dataclass(frozen=True)
class OIDCConfig:
    enforce: bool
    issuer: str
    audience: str
    jwks_url: str
    avatar_repo_allowlist: set[str]
    avatar_actor_allowlist: set[str]


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _split_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {item.strip() for item in value.split(",") if item.strip()}


def get_request_correlation_id(headers: Mapping[str, str] | None = None) -> str:
    headers = headers or {}
    for key in ("x-request-id", "x-correlation-id", "X-Request-ID", "X-Correlation-ID"):
        value = headers.get(key)
        if value and str(value).strip():
            return str(value).strip()
    return str(uuid.uuid4())


def load_oidc_config() -> OIDCConfig:
    return OIDCConfig(
        enforce=_is_truthy(os.getenv("OIDC_ENFORCE")),
        issuer=str(os.getenv("OIDC_ISSUER", "")).strip(),
        audience=str(os.getenv("OIDC_AUDIENCE", "")).strip(),
        jwks_url=str(os.getenv("OIDC_JWKS_URL", "")).strip(),
        avatar_repo_allowlist=_split_csv(os.getenv("OIDC_AVATAR_REPOSITORY_ALLOWLIST")),
        avatar_actor_allowlist=_split_csv(os.getenv("OIDC_AVATAR_ACTOR_ALLOWLIST")),
    )


def validate_startup_oidc_requirements(environment: str | None = None) -> None:
    env_name = str(environment or os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "").strip().lower()
    is_production = env_name in {"prod", "production"}
    if not is_production:
        return

    config = load_oidc_config()
    missing: list[str] = []
    if not config.enforce:
        missing.append("OIDC_ENFORCE=true")
    if not config.issuer:
        missing.append("OIDC_ISSUER")
    if not config.audience:
        missing.append("OIDC_AUDIENCE")
    if not config.jwks_url:
        missing.append("OIDC_JWKS_URL")

    if missing:
        raise RuntimeError(f"Missing required production OIDC configuration: {', '.join(missing)}")


def extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise OIDCAuthError("unauthorized")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise OIDCAuthError("unauthorized")
    return token.strip()


def verify_bearer_token(token: str, request_id: str) -> dict[str, Any]:
    config = load_oidc_config()
    if not config.issuer or not config.audience or not config.jwks_url:
        LOGGER.error("OIDC misconfiguration; request_id=%s", request_id)
        raise OIDCAuthError("unauthorized")

    try:
        jwks_client = jwt.PyJWKClient(config.jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience=config.audience,
            issuer=config.issuer,
        )
    except Exception:
        LOGGER.warning("OIDC token verification failed; request_id=%s", request_id)
        raise OIDCAuthError("unauthorized")

    repository = str(claims.get("repository", "")).strip()
    actor = str(claims.get("actor", "")).strip()
    if not repository or not actor:
        LOGGER.warning("OIDC claims missing required repository/actor; request_id=%s", request_id)
        raise OIDCClaimError("forbidden")
    return claims


def enforce_avatar_ingest_allowlists(claims: Mapping[str, Any], request_id: str) -> None:
    config = load_oidc_config()
    repository = str(claims.get("repository", "")).strip()
    actor = str(claims.get("actor", "")).strip()

    if config.avatar_repo_allowlist and repository not in config.avatar_repo_allowlist:
        LOGGER.warning(
            "OIDC avatar-ingest repository rejected; request_id=%s repository=%s",
            request_id,
            repository,
        )
        raise OIDCClaimError("forbidden")

    if config.avatar_actor_allowlist and actor not in config.avatar_actor_allowlist:
        LOGGER.warning(
            "OIDC avatar-ingest actor rejected; request_id=%s actor=%s",
            request_id,
            actor,
        )
        raise OIDCClaimError("forbidden")

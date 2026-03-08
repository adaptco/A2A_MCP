"""JWT issuance and verification helpers for RBAC access tokens."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
import uuid
from typing import Any, Mapping

import jwt


class TokenServiceError(RuntimeError):
    """Typed failure for token issue/verification operations."""


def token_fingerprint(token: str) -> str:
    """Return a stable short fingerprint for a token without exposing it."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


class RBACJWTIssuer:
    """Mint and verify RBAC JWT access tokens."""

    def __init__(
        self,
        *,
        secret: str | None = None,
        issuer: str | None = None,
        audience: str | None = None,
        algorithm: str = "HS256",
        default_ttl_seconds: int = 900,
    ) -> None:
        self.secret = (secret or os.getenv("RBAC_SECRET", "dev-secret-change-me")).strip()
        self.issuer = (issuer or os.getenv("RBAC_JWT_ISSUER", "a2a-rbac-gateway")).strip()
        self.audience = (audience or os.getenv("RBAC_JWT_AUDIENCE", "a2a-mcp-clients")).strip()
        self.algorithm = algorithm
        self.default_ttl_seconds = int(default_ttl_seconds)
        if not self.secret:
            raise TokenServiceError("RBAC signing secret is required")

    def issue_access_token(
        self,
        claims: Mapping[str, Any],
        *,
        ttl_seconds: int | None = None,
        now: int | None = None,
    ) -> tuple[str, dict[str, Any]]:
        """Issue signed JWT and return `(token, expanded_claims)`."""

        iat = int(now if now is not None else datetime.now(timezone.utc).timestamp())
        ttl = int(ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds)
        if ttl <= 0:
            raise TokenServiceError("ttl_seconds must be positive")

        payload: dict[str, Any] = dict(claims)
        payload.setdefault("iss", self.issuer)
        payload.setdefault("aud", self.audience)
        payload.setdefault("jti", f"jti-{uuid.uuid4().hex}")
        payload["iat"] = iat
        payload["exp"] = iat + ttl

        token = jwt.encode(payload, self.secret, algorithm=self.algorithm)
        return token, payload

    def verify_access_token(self, token: str, *, leeway_seconds: int = 0) -> dict[str, Any]:
        """Verify signed JWT and return decoded claims."""

        try:
            decoded = jwt.decode(
                token,
                self.secret,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                leeway=leeway_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            raise TokenServiceError(f"RBAC token verification failed: {exc}") from exc
        return dict(decoded)


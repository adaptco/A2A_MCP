from __future__ import annotations

import os
from typing import Any

from fastapi import Header, HTTPException, status, Depends
from app.security.oidc import extract_bearer_token, verify_bearer_token, get_request_correlation_id


async def authenticate_user(
    authorization: str | None = Header(default=None, alias="Authorization"),
) -> dict[str, Any]:
    """
    Dependency to authenticate requests using OIDC bearer tokens.
    """
    if os.getenv("AUTH_DISABLED") == "true" and os.getenv("ENV") != "production":
        return {"repository": "dev-repo", "actor": "dev-user"}

    request_id = get_request_correlation_id()
    try:
        token = extract_bearer_token(authorization)
        claims = verify_bearer_token(token, request_id=request_id)
        return claims
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )

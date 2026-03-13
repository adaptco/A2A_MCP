import os
import logging
from collections.abc import Mapping
from functools import wraps
from typing import Any, Optional

from app.security.oidc import (
    extract_bearer_token,
    get_request_correlation_id,
    verify_bearer_token,
)

logger = logging.getLogger("AuthMiddleware")


class AuthMiddleware:
    """
    Middleware for handling authentication and secret management.
    Supports JWT (OIDC) and API Key validation.
    """

    def validate_token(self, authorization: str | None, request_id: str | None = None) -> dict[str, Any]:
        """Validates a bearer token and returns verified claims."""
        token = extract_bearer_token(authorization)
        correlation_id = request_id or get_request_correlation_id()
        return verify_bearer_token(token, request_id=correlation_id)

    def get_secret(self, key: str) -> Optional[str]:
        """Retrieves a secret from environment variables."""
        return os.environ.get(key)


def _extract_request(kwargs: dict[str, Any]) -> Any:
    return kwargs.get("request") or kwargs.get("req")


def _extract_authorization(kwargs: dict[str, Any]) -> tuple[str | None, dict[str, str]]:
    headers: dict[str, str] = {}

    header_value = kwargs.get("authorization")
    if isinstance(header_value, str):
        return header_value, headers

    header_map = kwargs.get("headers")
    if isinstance(header_map, Mapping):
        headers = {str(k): str(v) for k, v in header_map.items()}
        authorization = headers.get("Authorization") or headers.get("authorization")
        if authorization:
            return authorization, headers

    request = _extract_request(kwargs)
    request_headers = getattr(request, "headers", None)
    if isinstance(request_headers, Mapping):
        headers = {str(k): str(v) for k, v in request_headers.items()}
        authorization = headers.get("Authorization") or headers.get("authorization")
        if authorization:
            return authorization, headers

    context = kwargs.get("context")
    if isinstance(context, Mapping):
        maybe_headers = context.get("headers")
        if isinstance(maybe_headers, Mapping):
            headers = {str(k): str(v) for k, v in maybe_headers.items()}
            authorization = headers.get("Authorization") or headers.get("authorization")
            if authorization:
                return authorization, headers

    return None, headers


def _attach_auth_claims(kwargs: dict[str, Any], claims: dict[str, Any]) -> None:
    request = _extract_request(kwargs)
    if request is not None:
        state = getattr(request, "state", None)
        if state is None:
            class _State:
                pass

            state = _State()
            setattr(request, "state", state)
        setattr(state, "auth_claims", claims)

    context = kwargs.get("context")
    if isinstance(context, dict):
        context["auth_claims"] = claims


def require_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        authorization, headers = _extract_authorization(kwargs)
        request_id = get_request_correlation_id(headers=headers)
        auth = AuthMiddleware()
        try:
            claims = auth.validate_token(authorization, request_id=request_id)
        except Exception as exc:
            logger.error("Authentication failed: Invalid or missing token")
            raise PermissionError("Unauthorized access to agentic tools") from exc

        _attach_auth_claims(kwargs, claims)
        return await f(*args, **kwargs)

    return decorated

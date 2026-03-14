import pytest
import os
from fastapi.middleware.cors import CORSMiddleware
from rbac.rbac_service import app

def test_cors_config_is_not_wildcard():
    """
    Verify that the CORS configuration does not use a wildcard for allow_origins
    when allow_credentials is True.
    """
    try:
        import fastapi
        import pydantic
    except ImportError:
        pytest.skip("Skipping test due to missing dependencies (fastapi/pydantic)")

    # Find the CORSMiddleware in the app's middleware list
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls == CORSMiddleware:
            cors_middleware = middleware
            break

    assert cors_middleware is not None, "CORSMiddleware not found in app."

    # Fix: Use .kwargs instead of .options for Starlette Middleware objects
    if hasattr(cors_middleware, 'kwargs'):
        allow_origins = cors_middleware.kwargs.get("allow_origins", [])
    else:
        allow_origins = cors_middleware.options.get("allow_origins", [])

    # Ensure allow_origins is NOT ["*"]
    assert allow_origins != ["*"], "CORS allow_origins should not be wildcard when allow_credentials is True"

    # Verify it matches expected default or env
    expected_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8000").split(",")
    assert allow_origins == expected_origins

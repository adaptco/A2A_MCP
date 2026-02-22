import pytest


def test_cors_config_is_not_wildcard():
    """
    Verify that the CORS configuration does not use a wildcard for allow_origins
    when allow_credentials is True.
    """
    try:
        import fastapi  # noqa: F401
        import pydantic  # noqa: F401
    except ImportError:
        pytest.skip("Skipping test due to missing dependencies (fastapi/pydantic)")

    from rbac.rbac_service import app
    from fastapi.middleware.cors import CORSMiddleware

    # Find the CORSMiddleware in the app's middleware list
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls == CORSMiddleware:
            cors_middleware = middleware
            break

    assert cors_middleware is not None, "CORSMiddleware not found in app."

    # Recent versions of Starlette (>= 0.34) changed how options are stored in Middleware objects.
    # We check for both .kwargs and .options for compatibility.
    allow_origins = []
    if hasattr(cors_middleware, 'kwargs'):
        allow_origins = cors_middleware.kwargs.get("allow_origins", [])
    elif hasattr(cors_middleware, 'options'):
        allow_origins = cors_middleware.options.get("allow_origins", [])

    assert "*" not in allow_origins, "CORS allow_origins must not be a wildcard when allow_credentials is True"

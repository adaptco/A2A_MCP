import os
import pytest
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
    cors_options = {}

    for middleware in app.user_middleware:
        if middleware.cls == CORSMiddleware:
            cors_middleware = middleware
            # Starlette Middleware object has kwargs or options depending on version/definition
            # Inspect both
            if hasattr(middleware, "options"):
                cors_options.update(middleware.options)
            if hasattr(middleware, "kwargs"):
                cors_options.update(middleware.kwargs)
            break

    assert cors_middleware is not None, "CORSMiddleware not found in app."

    allow_origins = cors_options.get("allow_origins", [])
    allow_credentials = cors_options.get("allow_credentials", False)

    # Debug print
    print(f"DEBUG: allow_origins={allow_origins}, allow_credentials={allow_credentials}")

    if allow_credentials:
        assert "*" not in allow_origins, "Security Risk: allow_origins=['*'] with allow_credentials=True"

if __name__ == "__main__":
    # Allow running directly for manual verification
    try:
        from rbac.rbac_service import app
        from fastapi.middleware.cors import CORSMiddleware

        cors_middleware = None
        cors_options = {}
        for middleware in app.user_middleware:
            if middleware.cls == CORSMiddleware:
                cors_middleware = middleware
                if hasattr(middleware, "options"):
                    cors_options.update(middleware.options)
                if hasattr(middleware, "kwargs"):
                    cors_options.update(middleware.kwargs)
                break

        if cors_middleware:
            allow_origins = cors_options.get("allow_origins", [])
            print(f"Current allow_origins: {allow_origins}")
            if "*" in allow_origins:
                print("VULNERABLE")
            else:
                print("SECURE")
    except ImportError as e:
        print(f"ImportError: {e}")

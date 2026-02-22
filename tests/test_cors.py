
import os
import sys
import pytest

# Add the current directory to sys.path so we can import rbac
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

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

    from rbac.rbac_service import app
    from fastapi.middleware.cors import CORSMiddleware

    # Find the CORSMiddleware in the app's middleware list
    cors_middleware = None
    for middleware in app.user_middleware:
        if middleware.cls == CORSMiddleware:
            cors_middleware = middleware
            break

    assert cors_middleware is not None, "CORSMiddleware not found in app."

    allow_origins = cors_middleware.options.get("allow_origins", [])
    allow_credentials = cors_middleware.options.get("allow_credentials", False)

    if allow_credentials:
        assert "*" not in allow_origins, "Security Risk: allow_origins=['*'] with allow_credentials=True"

if __name__ == "__main__":
    # Allow running directly for manual verification
    try:
        from rbac.rbac_service import app
        from fastapi.middleware.cors import CORSMiddleware

        cors_middleware = next((m for m in app.user_middleware if m.cls == CORSMiddleware), None)

        if cors_middleware:
            allow_origins = cors_middleware.options.get("allow_origins", [])
            print(f"Current allow_origins: {allow_origins}")
            if "*" in allow_origins:
                print("VULNERABLE")
            else:
                print("SECURE")
    except ImportError as e:
        print(f"ImportError: {e}")

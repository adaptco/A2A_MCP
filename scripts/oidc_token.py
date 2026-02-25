"""Compatibility wrapper for shared OIDC token verification."""

from app.oidc_token import verify_github_oidc_token

__all__ = ["verify_github_oidc_token"]

"""Script wrapper for GitHub OIDC token verification.

This script imports the verification logic from the app package.
"""

from app.oidc_token import verify_github_oidc_token

# Export for use in other scripts
__all__ = ["verify_github_oidc_token"]

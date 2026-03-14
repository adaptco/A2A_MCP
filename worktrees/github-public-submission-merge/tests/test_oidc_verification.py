import unittest
from unittest.mock import patch, MagicMock

# We try to import, but it might fail in the current environment
try:
    import jwt  # noqa: F401
    from app.oidc_token import verify_github_oidc_token
    HAS_DEPENDENCIES = True
except ImportError:
    HAS_DEPENDENCIES = False


@unittest.skipUnless(HAS_DEPENDENCIES, "PyJWT not installed")
class TestOIDCVerification(unittest.TestCase):
    @patch("app.oidc_token._jwks_client")
    @patch("jwt.decode")
    def test_verify_github_oidc_token_success(self, mock_decode, mock_jwks_client):
        # Setup mocks
        mock_token = "mock.jwt.token"
        mock_claims = {
            "sub": "repo:org/repo:ref:refs/heads/main",
            "repository": "org/repo",
            "jti": "mock-jti"
        }
        mock_decode.return_value = mock_claims

        mock_signing_key = MagicMock()
        mock_signing_key.key = "mock-key"
        mock_jwks_client.get_signing_key_from_jwt.return_value = mock_signing_key

        # Call function
        result = verify_github_oidc_token(mock_token)

        # Assertions
        self.assertEqual(result, mock_claims)
        mock_jwks_client.get_signing_key_from_jwt.assert_called_once_with(mock_token)
        mock_decode.assert_called_once()
        args, kwargs = mock_decode.call_args
        self.assertEqual(args[0], mock_token)
        self.assertEqual(args[1], "mock-key")
        self.assertEqual(kwargs["issuer"], "https://token.actions.githubusercontent.com")

    def test_verify_github_oidc_token_empty(self):
        with self.assertRaises(ValueError) as cm:
            verify_github_oidc_token("")
        self.assertEqual(str(cm.exception), "Empty OIDC token")

    @patch("app.oidc_token._jwks_client")
    def test_verify_github_oidc_token_failure(self, mock_jwks_client):
        mock_jwks_client.get_signing_key_from_jwt.side_effect = Exception("Failed to fetch key")

        with self.assertRaises(ValueError) as cm:
            verify_github_oidc_token("some.token")
        self.assertIn("Unexpected error during OIDC verification", str(cm.exception))


if __name__ == "__main__":
    unittest.main()

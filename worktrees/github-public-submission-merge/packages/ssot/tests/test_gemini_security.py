import os
import unittest
from unittest.mock import patch, MagicMock
from gemini_client import generate_content_with_gemini, GEMINI_API_URL_BASE, DEFAULT_MODEL, GEMINI_API_KEY

class TestGeminiSecurityRepro(unittest.TestCase):
    @patch('gemini_client.requests.post')
    def test_api_key_security_fix(self, mock_post):
        """
        This test verifies that the API key is NO LONGER passed in the URL,
        and is instead passed securely via the 'x-goog-api-key' header.
        """
        # Patch the module-level variable to ensure we have a known key
        TEST_KEY = 'TEST_API_KEY'
        with patch('gemini_client.GEMINI_API_KEY', TEST_KEY):
            prompt = "Test prompt"
            generate_content_with_gemini(prompt)

            # Assert that requests.post was called
            self.assertTrue(mock_post.called)

            # Get the arguments passed to requests.post
            args, kwargs = mock_post.call_args
            url = args[0]
            headers = kwargs.get('headers', {})

            # 1. Verify API Key is NOT in the URL
            self.assertNotIn(f"key={TEST_KEY}", url)
            self.assertNotIn("key=", url) # Should not be there at all
            print(f"\n[VERIFIED] API Key NOT found in URL: {url}")

            # 2. Verify API Key IS in the Headers
            self.assertIn('x-goog-api-key', headers)
            self.assertEqual(headers['x-goog-api-key'], TEST_KEY)
            print(f"[VERIFIED] API Key found in Headers: x-goog-api-key=***")

if __name__ == '__main__':
    unittest.main()

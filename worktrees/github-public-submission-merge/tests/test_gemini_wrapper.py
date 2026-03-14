import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add the parent directory to sys.path to import the module
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from codex_qernel import generate_content_with_gemini

class TestGeminiWrapper(unittest.TestCase):

    @patch('codex_qernel.gemini_wrapper.genai')
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'fake_key'})
    def test_generate_content_success(self, mock_genai):
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated content"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Call function
        result = generate_content_with_gemini("Test prompt")

        # Verify
        mock_genai.configure.assert_called_with(api_key='fake_key')
        mock_genai.GenerativeModel.assert_called_with('models/gemini-flash-latest')
        mock_model.generate_content.assert_called_with("Test prompt")
        self.assertEqual(result, "Generated content")

    @patch('codex_qernel.gemini_wrapper.genai')
    @patch.dict(os.environ, {'GOOGLE_API_KEY': 'fake_key'})
    def test_generate_content_custom_model(self, mock_genai):
        # Setup mock
        mock_model = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Generated content"
        mock_model.generate_content.return_value = mock_response
        mock_genai.GenerativeModel.return_value = mock_model

        # Call function
        result = generate_content_with_gemini("Test prompt", model_name='custom-model')

        # Verify
        mock_genai.GenerativeModel.assert_called_with('custom-model')
        self.assertEqual(result, "Generated content")

    @patch.dict(os.environ, {}, clear=True)
    def test_generate_content_no_api_key(self):
        with self.assertRaisesRegex(ValueError, "GOOGLE_API_KEY environment variable is not set"):
            generate_content_with_gemini("Test prompt")

if __name__ == '__main__':
    unittest.main()

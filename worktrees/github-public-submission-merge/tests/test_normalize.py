"""
Tests for text and embedding normalization utilities.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys

# Import the module to be tested
from pipeline.lib.normalize import normalize_text, l2_normalize

class TestNormalizeText(unittest.TestCase):
    """Test cases for normalize_text function."""

    def test_nfkc_normalization(self):
        """Test NFKC Unicode normalization."""
        # \u210c is 'H' (Hilbert space), should normalize to 'H'
        # \u00bd is '½', should normalize to '1\u20442' (with fraction slash)
        # Note: 1/2 (ASCII) uses U+002F, but NFKC produces U+2044 (⁄) for fractions
        text = "Hello \u210c \u00bd"
        expected = "Hello H 1\u20442"
        self.assertEqual(normalize_text(text), expected)

    def test_whitespace_collapsing(self):
        """Test collapsing multiple spaces and tabs."""
        text = "Hello    world\t\tfrom   python"
        expected = "Hello world from python"
        self.assertEqual(normalize_text(text), expected)

    def test_line_ending_normalization(self):
        """Test normalization of line endings to LF."""
        text = "Line1\r\nLine2\rLine3\nLine4"
        # Note: newlines are preserved as single \n, but messy ones are fixed
        expected = "Line1\nLine2\nLine3\nLine4"
        self.assertEqual(normalize_text(text), expected)

    def test_paragraph_preservation(self):
        """Test that 3+ newlines are collapsed to 2 newlines."""
        text = "Para1\n\n\n\nPara2\n\n\nPara3"
        expected = "Para1\n\nPara2\n\nPara3"
        self.assertEqual(normalize_text(text), expected)

    def test_trimming(self):
        """Test stripping of leading/trailing whitespace."""
        text = "   Hello World   \n"
        expected = "Hello World"
        self.assertEqual(normalize_text(text), expected)

    def test_complex_normalization(self):
        """Test a combination of normalization steps."""
        # 'ﬁ' is \ufb01 (compatibility), expands to 'fi'
        text = "  The   ﬁnal\r\n\r\n\r\ncountdown   "
        expected = "The final\n\ncountdown"
        self.assertEqual(normalize_text(text), expected)


class TestL2Normalize(unittest.TestCase):
    """Test cases for l2_normalize function."""

    def test_l2_normalize_calls_torch(self):
        """Test that l2_normalize calls torch.nn.functional.normalize correctly."""
        # Mock torch
        mock_torch = MagicMock()
        mock_tensor = MagicMock()

        # Patch the 'pipeline.lib.normalize.torch' attribute
        # Since we are testing the logic inside the function, we need to patch the imported module
        with patch('pipeline.lib.normalize.torch', mock_torch):
            l2_normalize(mock_tensor)

            # Verify the call
            mock_torch.nn.functional.normalize.assert_called_once_with(
                mock_tensor, p=2, dim=-1
            )

    def test_l2_normalize_missing_torch(self):
        """Test that l2_normalize raises ImportError if torch is missing."""
        # Patch torch to be None to simulate missing dependency
        with patch('pipeline.lib.normalize.torch', None):
            # We mock sys.modules because unittest.mock.patch might not be enough if the module is already imported
            # But in this file, we patched the variable inside 'pipeline.lib.normalize'
            with self.assertRaises(ImportError):
                l2_normalize(MagicMock())

if __name__ == '__main__':
    unittest.main()

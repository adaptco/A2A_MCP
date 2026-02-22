import pytest
from unittest.mock import MagicMock
from pipeline.lib.normalize import normalize_text, l2_normalize

def test_normalize_text_unicode():
    """Verify NFKC normalization (e.g., combining characters, ligatures)."""
    # 'u\u0308' is 'u' + 'combining diaeresis' -> 'ü' (\u00fc)
    assert normalize_text('u\u0308') == '\u00fc'

    # Ligatures: 'ﬁ' (\ufb01) -> 'fi'
    assert normalize_text('ﬁ') == 'fi'

def test_normalize_text_line_endings():
    """Verify CRLF and CR are converted to LF."""
    # CRLF to LF
    assert normalize_text('line1\r\nline2') == 'line1\nline2'
    # CR to LF
    assert normalize_text('line1\rline2') == 'line1\nline2'
    # Mixed
    assert normalize_text('line1\r\nline2\rline3\nline4') == 'line1\nline2\nline3\nline4'

def test_normalize_text_whitespace():
    """Verify multiple spaces and tabs are collapsed."""
    # Multiple spaces
    assert normalize_text('a   b') == 'a b'
    # Tabs
    assert normalize_text('a\tb') == 'a b'
    # Mixed spaces and tabs
    assert normalize_text('a  \t  b') == 'a b'

def test_normalize_text_newlines():
    """Verify 3+ newlines are collapsed to 2."""
    # 3+ newlines to 2
    assert normalize_text('line1\n\n\nline2') == 'line1\n\nline2'
    assert normalize_text('line1\n\n\n\n\nline2') == 'line1\n\nline2'
    # Exactly 2 newlines preserved
    assert normalize_text('line1\n\nline2') == 'line1\n\nline2'

def test_normalize_text_strip():
    """Verify leading/trailing whitespace is removed."""
    # Leading/trailing whitespace
    assert normalize_text('  hello  ') == 'hello'
    assert normalize_text('\n\nhello\n\n') == 'hello'
    assert normalize_text('\t hello \r\n') == 'hello'

def test_normalize_text_combined():
    """Complex case combining multiple normalization steps."""
    input_text = "  Hello   World!\r\n\n\nThis is a\ttest.\n\n\nLigature: ﬁ  "
    expected = "Hello World!\n\nThis is a test.\n\nLigature: fi"
    assert normalize_text(input_text) == expected

def test_l2_normalize_calls_torch():
    """Verify l2_normalize calls the underlying torch function when available."""
    # Mock torch
    mock_torch = MagicMock()

    # Temporarily inject mock torch into the module
    import pipeline.lib.normalize as normalize_mod
    original_torch = normalize_mod.torch
    normalize_mod.torch = mock_torch

    try:
        dummy_tensor = MagicMock()
        l2_normalize(dummy_tensor)

        # Verify torch.nn.functional.normalize was called
        mock_torch.nn.functional.normalize.assert_called_once_with(
            dummy_tensor, p=2, dim=-1
        )
    finally:
        # Restore original torch
        normalize_mod.torch = original_torch

def test_l2_normalize_raises_if_no_torch():
    """Verify l2_normalize raises ImportError when torch is not available."""
    # Ensure torch is None
    import pipeline.lib.normalize as normalize_mod
    original_torch = normalize_mod.torch
    normalize_mod.torch = None

    try:
        with pytest.raises(ImportError) as excinfo:
            l2_normalize(MagicMock())
        assert "torch is required" in str(excinfo.value)
    finally:
        normalize_mod.torch = original_torch

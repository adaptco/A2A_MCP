"""
Text and embedding normalization utilities.
"""

import unicodedata
import re

try:
    import torch
except ImportError:
    torch = None


def normalize_text(text: str) -> str:
    """
    Normalize text for deterministic processing.
    
    Steps:
    1. NFKC Unicode normalization
    2. Collapse whitespace
    3. Normalize line endings to LF
    
    Args:
        text: Input text
    
    Returns:
        Normalized text
    """
    # NFKC normalization
    text = unicodedata.normalize('NFKC', text)
    
    # Normalize line endings to LF
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Collapse multiple spaces/tabs to single space
    text = re.sub(r'[ \t]+', ' ', text)
    
    # Collapse multiple newlines to double newline (preserve paragraph breaks)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def l2_normalize(tensor: "torch.Tensor") -> "torch.Tensor":
    """
    L2 normalization for embedding vectors.
    
    Args:
        tensor: Input tensor (can be 1D or 2D batch)
    
    Returns:
        L2-normalized tensor
    """
    if torch is None:
        raise ImportError("torch is required for l2_normalize. Install with 'pip install torch'.")
    return torch.nn.functional.normalize(tensor, p=2, dim=-1)

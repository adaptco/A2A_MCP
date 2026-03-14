"""
Document normalization utilities.
Ensures deterministic text processing for reproducible hashing.
"""
import re
import unicodedata
from typing import List


def normalize_unicode(text: str) -> str:
    """Apply NFKC Unicode normalization."""
    return unicodedata.normalize("NFKC", text)


def collapse_whitespace(text: str) -> str:
    """Collapse runs of whitespace to single spaces, preserve paragraph breaks."""
    # Normalize line endings to LF
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    
    # Preserve double newlines (paragraph breaks)
    paragraphs = re.split(r"\n\n+", text)
    
    # Collapse whitespace within paragraphs
    normalized_paragraphs = []
    for para in paragraphs:
        # Replace all whitespace (including single newlines) with single space
        para = re.sub(r"[ \t\n]+", " ", para)
        para = para.strip()
        if para:
            normalized_paragraphs.append(para)
    
    return "\n\n".join(normalized_paragraphs)


def normalize_line_endings(text: str) -> str:
    """Convert all line endings to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def normalize_text(text: str) -> str:
    """
    Full text normalization pipeline.
    - NFKC Unicode normalization
    - Whitespace collapse
    - LF line endings
    """
    text = normalize_unicode(text)
    text = collapse_whitespace(text)
    text = normalize_line_endings(text)
    return text


def stable_block_sort_key(block: dict) -> tuple:
    """
    Generate a stable sort key for document blocks.
    Orders by (page_index, block_index).
    """
    return (
        block.get("page_index", 0),
        block.get("block_index", 0)
    )


def serialize_table_row_major(cells: List[List[str]]) -> str:
    """
    Serialize a table deterministically in row-major order.
    Each cell is normalized and joined with delimiters.
    """
    rows = []
    for row in cells:
        normalized_cells = [normalize_text(cell) for cell in row]
        rows.append("|".join(normalized_cells))
    return "\n".join(rows)

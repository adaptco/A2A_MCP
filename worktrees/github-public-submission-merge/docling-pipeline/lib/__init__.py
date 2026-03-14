"""Library package for Docling pipeline utilities."""
from .canonical import (
    jcs_canonical_bytes,
    sha256_hex,
    hash_canonical,
    hash_canonical_without_integrity,
    compute_doc_id,
    compute_chunk_id
)
from .ledger import Ledger, get_ledger
from .normalize import (
    normalize_unicode,
    collapse_whitespace,
    normalize_line_endings,
    normalize_text,
    stable_block_sort_key,
    serialize_table_row_major
)

__all__ = [
    # Canonical
    "jcs_canonical_bytes",
    "sha256_hex",
    "hash_canonical",
    "hash_canonical_without_integrity",
    "compute_doc_id",
    "compute_chunk_id",
    # Ledger
    "Ledger",
    "get_ledger",
    # Normalize
    "normalize_unicode",
    "collapse_whitespace",
    "normalize_line_endings",
    "normalize_text",
    "stable_block_sort_key",
    "serialize_table_row_major",
]

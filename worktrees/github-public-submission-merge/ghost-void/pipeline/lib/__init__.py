"""Core library for Docling pipeline."""

from .canonical import (
    jcs_canonical_bytes,
    sha256_hex,
    hash_canonical_without_integrity,
    append_to_ledger
)
from .normalize import normalize_text, l2_normalize

__all__ = [
    'jcs_canonical_bytes',
    'sha256_hex',
    'hash_canonical_without_integrity',
    'append_to_ledger',
    'normalize_text',
    'l2_normalize'
]

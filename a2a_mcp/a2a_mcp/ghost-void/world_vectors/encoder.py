"""Pluggable embedding encoder for world vectorization."""

from dataclasses import dataclass
from typing import List, Optional, Any
import hashlib


@dataclass
class Embedding:
    """Vector representation of world content."""
    text: str
    vector: List[float]
    metadata: dict = None
    embedding_id: str = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.embedding_id is None:
            # Deterministic ID from content hash
            self.embedding_id = hashlib.sha256(self.text.encode()).hexdigest()[:16]


class EmbeddingEncoder:
    """
    Pluggable encoder for text → vectors.
    Default: mock cosine-friendly representation.
    Override: with sentence-transformers, OpenAI, etc.
    """

    DEFAULT_DIM = 768

    def __init__(self, dim: int = DEFAULT_DIM):
        self.dim = dim

    def encode(self, text: str, metadata: Optional[dict] = None) -> Embedding:
        """
        Encode text into a vector.

        Args:
            text: Content to embed
            metadata: Optional contextual data

        Returns:
            Embedding object with vector and metadata
        """
        # Placeholder: normalized hash-based vector
        # In production: call sentence-transformers or LLM embedding API
        hash_val = int(hashlib.md5(text.encode()).hexdigest(), 16)
        vector = [((hash_val >> i) % 256) / 256.0 for i in range(self.dim)]

        # Normalize to unit norm (for cosine similarity)
        norm = sum(x ** 2 for x in vector) ** 0.5
        if norm > 0:
            vector = [x / norm for x in vector]

        return Embedding(text=text, vector=vector, metadata=metadata or {})

    def encode_batch(self, texts: List[str], metadata: Optional[List[dict]] = None) -> List[Embedding]:
        """Encode multiple texts efficiently."""
        if metadata is None:
            metadata = [{}] * len(texts)
        return [self.encode(text, meta) for text, meta in zip(texts, metadata)]

    def __repr__(self) -> str:
        return f"<EmbeddingEncoder dim={self.dim}>"

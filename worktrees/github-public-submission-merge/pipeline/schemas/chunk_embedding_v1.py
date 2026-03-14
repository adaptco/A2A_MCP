"""
Pydantic schema for chunk.embedding.v1
Represents a document chunk with its embedding vector.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class ChunkerParams(BaseModel):
    """Chunking parameters."""
    max_tokens: int = 400
    overlap: int = 60


class Chunker(BaseModel):
    """Chunker metadata."""
    version: str = "chunk.v1"
    method: str = "block+window"
    params: ChunkerParams = Field(default_factory=ChunkerParams)


class Embedding(BaseModel):
    """Embedding metadata and vector."""
    framework: Literal["pytorch"] = "pytorch"
    model_id: str
    weights_hash: str
    dim: int = 768
    normalization: Literal["l2", "none"] = "l2"
    vector: List[float]


class Provenance(BaseModel):
    """Source block references for traceability."""
    source_block_refs: List[str] = Field(default_factory=list)


class Integrity(BaseModel):
    """Hash-chain integrity block."""
    sha256_canonical: str
    prev_ledger_hash: Optional[str] = None


class ChunkEmbeddingV1(BaseModel):
    """
    chunk.embedding.v1 schema.
    Represents a document chunk with its embedding vector.
    """
    schema_: str = Field("chunk.embedding.v1", alias="schema")
    doc_id: str
    chunk_id: str
    chunk_text: str
    chunker: Chunker = Field(default_factory=Chunker)
    embedding: Embedding
    provenance: Provenance = Field(default_factory=Provenance)
    integrity: Optional[Integrity] = None

    class Config:
        populate_by_name = True

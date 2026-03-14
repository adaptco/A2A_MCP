"""
Pydantic schema for doc.normalized.v1
Represents a Docling-parsed and canonicalized document.
"""
from datetime import datetime
from typing import List, Literal, Optional, Union

from pydantic import BaseModel, Field


class TextBlock(BaseModel):
    """A text block within a page."""
    type: Literal["text"] = "text"
    text: str
    block_index: int = 0


class TableBlock(BaseModel):
    """A table block within a page."""
    type: Literal["table"] = "table"
    cells: List[List[str]]
    block_index: int = 0


Block = Union[TextBlock, TableBlock]


class Page(BaseModel):
    """A single page of the document."""
    page_index: int
    blocks: List[Block] = Field(default_factory=list)


class Source(BaseModel):
    """Source metadata for the document."""
    uri: str
    content_type: str
    received_at: datetime


class Parser(BaseModel):
    """Parser metadata."""
    name: str = "ibm-docling"
    version: str
    config_hash: str


class TextPolicy(BaseModel):
    """Text normalization policy."""
    unicode: str = "NFKC"
    whitespace: str = "collapse"
    line_endings: str = "LF"


class Normalization(BaseModel):
    """Normalization metadata."""
    normalizer_version: str = "norm.v1"
    canonicalization: str = "JCS-RFC8785"
    text_policy: TextPolicy = Field(default_factory=TextPolicy)


class Content(BaseModel):
    """Document content."""
    title: Optional[str] = None
    pages: List[Page] = Field(default_factory=list)


class Integrity(BaseModel):
    """Hash-chain integrity block."""
    sha256_canonical: str
    prev_ledger_hash: Optional[str] = None


class DocNormalizedV1(BaseModel):
    """
    doc.normalized.v1 schema.
    Represents a Docling-parsed document with canonical normalization.
    """
    schema_: str = Field("doc.normalized.v1", alias="schema")
    doc_id: str
    source: Source
    parser: Parser
    normalization: Normalization = Field(default_factory=Normalization)
    content: Content
    integrity: Optional[Integrity] = None

    class Config:
        populate_by_name = True

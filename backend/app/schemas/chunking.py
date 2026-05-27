"""Schemas for PDF parsing and semantic chunking."""

from pydantic import BaseModel, Field

from backend.app.schemas.extraction import SectionType


class TextBlock(BaseModel):
    text: str
    page_number: int
    block_type: str = "paragraph"  # paragraph, heading, list_item, code, table
    font_size: float | None = None
    is_bold: bool = False
    bbox: tuple[float, float, float, float] | None = None


class TableBlock(BaseModel):
    page_number: int
    headers: list[str] = Field(default_factory=list)
    rows: list[list[str]] = Field(default_factory=list)
    markdown: str = ""


class ParsedPage(BaseModel):
    page_number: int
    blocks: list[TextBlock] = Field(default_factory=list)
    tables: list[TableBlock] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    filename: str
    page_count: int
    pages: list[ParsedPage] = Field(default_factory=list)
    full_text: str = ""
    content_hash: str = ""
    text_density: float = 0.0


class DocumentSection(BaseModel):
    section_id: str
    section_type: SectionType
    title: str
    content: str
    page_start: int
    page_end: int
    parent_section_id: str | None = None
    hierarchy_level: int = 0
    child_section_ids: list[str] = Field(default_factory=list)


class SemanticChunk(BaseModel):
    chunk_id: str
    document_id: str
    section_id: str
    section_type: SectionType
    section_title: str
    content: str
    page_start: int
    page_end: int
    parent_section_id: str | None = None
    hierarchy_level: int = 0
    metadata: dict[str, str] = Field(default_factory=dict)
    token_estimate: int = 0

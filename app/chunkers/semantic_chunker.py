"""Semantic chunking based on document structure, not fixed token windows."""

from __future__ import annotations

import re

from app.core.config import get_settings
from app.core.logging import get_logger
from app.prompts.extraction import SECTION_CLASSIFICATION_KEYWORDS
from app.schemas.chunking import DocumentSection, ParsedDocument, SemanticChunk
from app.schemas.extraction import SectionType
from app.utils.ids import generate_chunk_id, generate_section_id
from app.utils.text import normalize_whitespace

logger = get_logger(__name__)


class SemanticChunker:
    """Builds hierarchical sections and semantic chunks from parsed PDFs."""

    def __init__(self) -> None:
        settings = get_settings()
        self.max_chunk_chars = settings.max_chunk_chars
        self.overlap_chars = settings.chunk_overlap_chars

    def chunk_document(self, parsed: ParsedDocument, document_id: str) -> list[SemanticChunk]:
        sections = self._build_sections(parsed, document_id)
        chunks: list[SemanticChunk] = []
        for section in sections:
            section_chunks = self._section_to_chunks(section, document_id)
            chunks.extend(section_chunks)
        logger.info(
            "document_chunked",
            document_id=document_id,
            sections=len(sections),
            chunks=len(chunks),
        )
        return chunks

    def _build_sections(
        self, parsed: ParsedDocument, document_id: str
    ) -> list[DocumentSection]:
        sections: list[DocumentSection] = []
        current_title = "Document Start"
        current_type = SectionType.GENERAL
        current_lines: list[str] = []
        page_start = 1
        page_end = 1
        parent_id: str | None = None
        hierarchy = 0

        def flush() -> None:
            nonlocal current_lines, page_start, page_end
            if not current_lines:
                return
            content = normalize_whitespace("\n".join(current_lines))
            if len(content) < 20:
                current_lines = []
                return
            sid = generate_section_id(document_id, current_title, page_start)
            sections.append(
                DocumentSection(
                    section_id=sid,
                    section_type=current_type,
                    title=current_title,
                    content=content,
                    page_start=page_start,
                    page_end=page_end,
                    parent_section_id=parent_id,
                    hierarchy_level=hierarchy,
                )
            )
            current_lines = []

        for page in parsed.pages:
            page_end = page.page_number
            for table in page.tables:
                flush()
                table_content = table.markdown or self._format_table(table.headers, table.rows)
                sid = generate_section_id(document_id, f"Table p{page.page_number}", page.page_number)
                sections.append(
                    DocumentSection(
                        section_id=sid,
                        section_type=SectionType.TABLE,
                        title=f"Table (page {page.page_number})",
                        content=table_content,
                        page_start=page.page_number,
                        page_end=page.page_number,
                    )
                )

            for block in page.blocks:
                if block.block_type == "heading":
                    flush()
                    current_title = block.text
                    current_type = self._classify_section(block.text, "")
                    page_start = block.page_number
                    hierarchy = 1 if current_type != SectionType.GENERAL else 0
                    parent_id = None
                else:
                    if not current_lines:
                        page_start = block.page_number
                    current_lines.append(block.text)

        flush()
        if not sections and parsed.full_text:
            sections.append(
                DocumentSection(
                    section_id=generate_section_id(document_id, "Full Document", 1),
                    section_type=SectionType.GENERAL,
                    title=parsed.filename,
                    content=parsed.full_text[:50000],
                    page_start=1,
                    page_end=parsed.page_count,
                )
            )
        return sections

    def _section_to_chunks(
        self, section: DocumentSection, document_id: str
    ) -> list[SemanticChunk]:
        content = section.content
        if len(content) <= self.max_chunk_chars:
            return [
                self._make_chunk(
                    document_id=document_id,
                    section=section,
                    content=content,
                    index=0,
                    page_start=section.page_start,
                    page_end=section.page_end,
                )
            ]

        paragraphs = re.split(r"\n\n+", content)
        chunks: list[SemanticChunk] = []
        buffer: list[str] = []
        buffer_len = 0
        idx = 0
        p_start = section.page_start

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if buffer_len + len(para) + 2 > self.max_chunk_chars and buffer:
                chunk_content = normalize_whitespace("\n\n".join(buffer))
                chunks.append(
                    self._make_chunk(
                        document_id, section, chunk_content, idx, p_start, section.page_end
                    )
                )
                idx += 1
                overlap = chunk_content[-self.overlap_chars :] if self.overlap_chars else ""
                buffer = [overlap, para] if overlap else [para]
                buffer_len = sum(len(x) for x in buffer)
            else:
                buffer.append(para)
                buffer_len += len(para) + 2

        if buffer:
            chunk_content = normalize_whitespace("\n\n".join(buffer))
            chunks.append(
                self._make_chunk(
                    document_id, section, chunk_content, idx, p_start, section.page_end
                )
            )
        return chunks

    def _make_chunk(
        self,
        document_id: str,
        section: DocumentSection,
        content: str,
        index: int,
        page_start: int,
        page_end: int,
    ) -> SemanticChunk:
        chunk_id = generate_chunk_id(document_id, section.section_id, index)
        return SemanticChunk(
            chunk_id=chunk_id,
            document_id=document_id,
            section_id=section.section_id,
            section_type=section.section_type,
            section_title=section.title,
            content=content,
            page_start=page_start,
            page_end=page_end,
            parent_section_id=section.parent_section_id,
            hierarchy_level=section.hierarchy_level,
            metadata={
                "filename": document_id,
                "section_type": section.section_type.value,
            },
            token_estimate=len(content) // 4,
        )

    def _classify_section(self, title: str, content_preview: str) -> SectionType:
        text = f"{title} {content_preview}".lower()
        scores: dict[str, int] = {}
        for section_key, keywords in SECTION_CLASSIFICATION_KEYWORDS.items():
            scores[section_key] = sum(1 for kw in keywords if kw in text)
        if not scores or max(scores.values()) == 0:
            return SectionType.GENERAL
        best = max(scores, key=scores.get)
        mapping = {
            "agent": SectionType.AGENT,
            "architecture": SectionType.ARCHITECTURE,
            "workflow": SectionType.WORKFLOW,
            "tech_stack": SectionType.TECH_STACK,
            "deployment": SectionType.DEPLOYMENT,
            "use_case": SectionType.USE_CASE,
            "constraints": SectionType.CONSTRAINTS,
            "integration": SectionType.INTEGRATION,
            "project_overview": SectionType.PROJECT_OVERVIEW,
        }
        return mapping.get(best, SectionType.GENERAL)

    @staticmethod
    def _format_table(headers: list[str], rows: list[list[str]]) -> str:
        lines = [" | ".join(headers)]
        for row in rows:
            lines.append(" | ".join(row))
        return "\n".join(lines)

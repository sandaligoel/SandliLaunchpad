"""Split document sections into project-level chunks for LLM extraction."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from pipeline.pdf_reader import Section, whole_document_text

logger = logging.getLogger(__name__)

MAX_WORDS = int(6000 * 0.75)  # ~4500 words proxy for 6000 tokens
WARN_TOKEN_THRESHOLD = 5000

PROJECT_BOUNDARY_KEYWORDS = re.compile(
    r"\b(project|engagement|case study|solution|client)\b",
    re.IGNORECASE,
)
CLIENT_LINE = re.compile(
    r"^(client|customer|for)\s*:\s*(.+)$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class ProjectChunk:
    """A text chunk describing one client project, ready for extraction."""

    raw_text: str
    estimated_start_page: int
    estimated_end_page: int
    title: str = ""


def estimate_token_count(text: str) -> int:
    """
    Estimate token count from word count.

    Uses heuristic: word_count * 1.33.
    """
    return int(len(text.split()) * 1.33)


def _split_at_paragraphs(text: str, max_words: int) -> list[str]:
    """Split text at paragraph boundaries when it exceeds max_words."""
    paragraphs = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0

    for para in paragraphs:
        para_words = len(para.split())
        if current_words + para_words > max_words and current:
            chunks.append("\n\n".join(current))
            current = [para]
            current_words = para_words
        else:
            current.append(para)
            current_words += para_words

    if current:
        chunks.append("\n\n".join(current))

    return chunks if chunks else [text]


def _is_project_boundary(section: Section) -> bool:
    """Return True if a section likely starts a new project."""
    title_match = PROJECT_BOUNDARY_KEYWORDS.search(section.title)
    text_intro = section.combined_text[:500]
    has_client = bool(CLIENT_LINE.search(text_intro))
    use_case = bool(
        re.search(
            r"\b(use case|challenge|business problem|objective)\b",
            text_intro,
            re.IGNORECASE,
        )
    )
    return bool(title_match or has_client or use_case)


def chunk_into_projects(sections: list[Section]) -> list[ProjectChunk]:
    """
    Group sections into project-level chunks suitable for LLM extraction.

    Args:
        sections: Document sections from detect_section_boundaries.

    Returns:
        List of ProjectChunk instances, each within the max token budget.

    Side effects:
        Logs WARNING for chunks exceeding WARN_TOKEN_THRESHOLD estimated tokens.
    """
    if not sections:
        return []

    chunks: list[ProjectChunk] = []
    buffer_text: list[str] = []
    buffer_start = sections[0].start_page
    buffer_end = sections[0].end_page
    buffer_title = sections[0].title

    def flush_buffer() -> None:
        nonlocal buffer_text, buffer_start, buffer_end, buffer_title
        if not buffer_text:
            return
        combined = "\n\n".join(buffer_text)
        for part in _split_at_paragraphs(combined, MAX_WORDS):
            est_tokens = estimate_token_count(part)
            if est_tokens > WARN_TOKEN_THRESHOLD:
                logger.warning(
                    "Chunk '%s' (pages %d-%d) estimated at %d tokens",
                    buffer_title,
                    buffer_start,
                    buffer_end,
                    est_tokens,
                )
            chunks.append(
                ProjectChunk(
                    raw_text=part,
                    estimated_start_page=buffer_start,
                    estimated_end_page=buffer_end,
                    title=buffer_title,
                )
            )
        buffer_text = []

    for i, section in enumerate(sections):
        if i > 0 and _is_project_boundary(section) and buffer_text:
            flush_buffer()
            buffer_start = section.start_page
            buffer_title = section.title

        buffer_text.append(section.combined_text)
        buffer_end = section.end_page

    flush_buffer()

    logger.info(
        "Created %d project chunks from %d sections",
        len(chunks),
        len(sections),
    )
    return chunks


def chunk_whole_document(pages: list) -> list[ProjectChunk]:
    """
    Treat the entire PDF as a single extraction unit (no section splitting).

    Use when you want one LLM pass over the full document.
    """
    if not pages:
        return []
    text = whole_document_text(pages)
    chunk = ProjectChunk(
        raw_text=text,
        estimated_start_page=pages[0].page_number,
        estimated_end_page=pages[-1].page_number,
        title="Full document",
    )
    logger.info(
        "Whole-document mode: 1 chunk, pages %d-%d, ~%d words",
        chunk.estimated_start_page,
        chunk.estimated_end_page,
        len(text.split()),
    )
    return [chunk]

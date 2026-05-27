"""PDF text extraction and section boundary detection using PyMuPDF."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

import fitz

logger = logging.getLogger(__name__)

SECTION_KEYWORDS = re.compile(
    r"\b(project|engagement|case study|solution)\b", re.IGNORECASE
)
NUMBERED_HEADER = re.compile(r"^(\d+\.|\d+\))\s+\S", re.IGNORECASE)
PROJECT_PREFIX = re.compile(r"^(project|case study|engagement):\s*", re.IGNORECASE)


@dataclass
class PageContent:
    """Text and metadata extracted from a single PDF page."""

    page_number: int
    raw_text: str
    block_text: list[tuple]
    has_tables: bool
    word_count: int


@dataclass
class Section:
    """A contiguous range of pages grouped under a section header."""

    title: str
    start_page: int
    end_page: int
    combined_text: str
    pages: list[PageContent] = field(default_factory=list)


def _detect_tables(text: str) -> bool:
    """
    Heuristic: page has tables if ≥3 lines look like numeric data rows.

    A row matches if it has multiple whitespace-separated number groups.
    """
    numeric_rows = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        number_groups = sum(1 for p in parts if re.match(r"^[\d,.$%-]+$", p))
        if number_groups >= 3:
            numeric_rows += 1
            if numeric_rows >= 3:
                return True
    return False


def extract_pages(pdf_path: str) -> list[PageContent]:
    """
    Extract raw text and metadata from each page of a PDF.

    Args:
        pdf_path: Filesystem path to the PDF file.

    Returns:
        List of PageContent instances, one per page (1-indexed page numbers).

    Side effects:
        Opens and closes the PDF via PyMuPDF; logs page count at INFO.
    """
    doc = fitz.open(pdf_path)
    pages: list[PageContent] = []

    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            raw_text = page.get_text("text") or ""
            blocks = page.get_text("blocks") or []
            block_text = [
                (b[0], b[1], b[2], b[3], b[4])
                for b in blocks
                if len(b) >= 5 and isinstance(b[4], str) and b[4].strip()
            ]
            word_count = len(raw_text.split())
            has_tables = _detect_tables(raw_text)

            pages.append(
                PageContent(
                    page_number=page_idx + 1,
                    raw_text=raw_text,
                    block_text=block_text,
                    has_tables=has_tables,
                    word_count=word_count,
                )
            )
    finally:
        doc.close()

    logger.info("Extracted %d pages from %s", len(pages), pdf_path)
    return pages


def _is_section_header(line: str, next_line: str | None) -> bool:
    """Return True if a line looks like a section header."""
    stripped = line.strip()
    if not stripped or len(stripped) >= 60:
        return False

    if NUMBERED_HEADER.match(stripped) or PROJECT_PREFIX.match(stripped):
        return True

    if SECTION_KEYWORDS.search(stripped) and len(stripped.split()) <= 8:
        return True

    is_caps = stripped == stripped.upper() and any(c.isalpha() for c in stripped)
    is_title = stripped == stripped.title() and len(stripped.split()) <= 8

    if not (is_caps or is_title):
        return False

    if next_line is None:
        return True

    next_stripped = next_line.strip()
    if not next_stripped:
        return True

    if next_stripped.startswith(("  ", "\t")) or len(next_stripped) > len(stripped) + 20:
        return True

    return is_caps and len(stripped.split()) <= 6


def _combine_page_text(page: PageContent) -> str:
    """Prefer block-ordered text when blocks are available, else raw text."""
    if page.block_text:
        sorted_blocks = sorted(page.block_text, key=lambda b: (b[1], b[0]))
        parts = [b[4].strip() for b in sorted_blocks if b[4].strip()]
        if parts:
            return "\n".join(parts)
    return page.raw_text


def detect_section_boundaries(pages: list[PageContent]) -> list[Section]:
    """
    Group pages into sections based on detected headers.

    Args:
        pages: PageContent list from extract_pages.

    Returns:
        List of Section objects. Falls back to 3-page windows if no headers found.

    Side effects:
        Logs WARNING when falling back to fixed windows.
    """
    if not pages:
        return []

    headers_found = 0
    sections: list[Section] = []
    current_title = "Introduction"
    current_pages: list[PageContent] = []

    for page in pages:
        lines = [ln for ln in page.raw_text.splitlines() if ln.strip()]
        header_on_page: str | None = None

        for i, line in enumerate(lines):
            next_line = lines[i + 1] if i + 1 < len(lines) else None
            if _is_section_header(line, next_line):
                header_on_page = line.strip()
                headers_found += 1
                break

        if header_on_page and current_pages:
            combined = "\n\n".join(_combine_page_text(p) for p in current_pages)
            sections.append(
                Section(
                    title=current_title,
                    start_page=current_pages[0].page_number,
                    end_page=current_pages[-1].page_number,
                    combined_text=combined,
                    pages=list(current_pages),
                )
            )
            current_pages = []
            current_title = header_on_page

        current_pages.append(page)

    if current_pages:
        combined = "\n\n".join(_combine_page_text(p) for p in current_pages)
        sections.append(
            Section(
                title=current_title,
                start_page=current_pages[0].page_number,
                end_page=current_pages[-1].page_number,
                combined_text=combined,
                pages=list(current_pages),
            )
        )

    if headers_found < 2:
        logger.warning(
            "Few section headers detected (%d); falling back to 3-page windows",
            headers_found,
        )
        return _fallback_page_windows(pages, window_size=3)

    logger.info("Detected %d sections across %d pages", len(sections), len(pages))
    return sections


def _fallback_page_windows(pages: list[PageContent], window_size: int = 3) -> list[Section]:
    """Split pages into fixed-size windows when section detection fails."""
    sections: list[Section] = []
    for i in range(0, len(pages), window_size):
        chunk = pages[i : i + window_size]
        combined = "\n\n".join(_combine_page_text(p) for p in chunk)
        sections.append(
            Section(
                title=f"Pages {chunk[0].page_number}-{chunk[-1].page_number}",
                start_page=chunk[0].page_number,
                end_page=chunk[-1].page_number,
                combined_text=combined,
                pages=list(chunk),
            )
        )
    return sections


def whole_document_text(pages: list[PageContent]) -> str:
    """Concatenate all pages into one text blob (no chunking)."""
    parts = []
    for page in pages:
        parts.append(f"--- Page {page.page_number} ---\n{_combine_page_text(page)}")
    return "\n\n".join(parts)

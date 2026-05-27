"""Hybrid PDF parser: PyMuPDF for layout/text, pdfplumber for tables."""

from __future__ import annotations

import asyncio
import io
from pathlib import Path

import fitz  # PyMuPDF
import pdfplumber

from backend.app.core.exceptions import PDFParseError
from backend.app.core.logging import get_logger
from backend.app.schemas.chunking import ParsedDocument, ParsedPage, TableBlock, TextBlock
from backend.app.utils.ids import content_hash
from backend.app.utils.text import normalize_whitespace

logger = get_logger(__name__)

MIN_TEXT_DENSITY = 0.02  # chars per point² — below suggests scanned PDF


class PDFParser:
    """Production PDF parser preserving semantic structure."""

    def __init__(self, page_batch_size: int = 50) -> None:
        self.page_batch_size = page_batch_size

    async def parse(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        return await asyncio.to_thread(self._parse_sync, file_bytes, filename)

    def _parse_sync(self, file_bytes: bytes, filename: str) -> ParsedDocument:
        file_hash = content_hash(file_bytes)
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise PDFParseError(f"Cannot open PDF: {filename}", {"error": str(e)}) from e

        page_count = len(doc)
        if page_count == 0:
            raise PDFParseError(f"PDF has no pages: {filename}")

        pages: list[ParsedPage] = []
        all_text_parts: list[str] = []
        total_chars = 0
        total_area = 0.0

        for page_num in range(page_count):
            page = doc[page_num]
            page_number = page_num + 1
            blocks = self._extract_blocks_pymupdf(page, page_number)
            tables = self._extract_tables_pdfplumber(file_bytes, page_number)
            pages.append(ParsedPage(page_number=page_number, blocks=blocks, tables=tables))

            page_text = "\n".join(b.text for b in blocks if b.text)
            if tables:
                page_text += "\n" + "\n".join(t.markdown for t in tables if t.markdown)
            all_text_parts.append(page_text)
            total_chars += len(page_text)
            rect = page.rect
            total_area += rect.width * rect.height

        doc.close()
        full_text = normalize_whitespace("\n\n".join(all_text_parts))
        text_density = total_chars / total_area if total_area > 0 else 0.0

        if text_density < MIN_TEXT_DENSITY and total_chars < 200:
            raise PDFParseError(
                f"PDF appears scanned or text-empty: {filename}",
                {
                    "text_density": text_density,
                    "char_count": total_chars,
                    "hint": "OCR support planned for Phase 2",
                },
            )

        logger.info(
            "pdf_parsed",
            filename=filename,
            pages=page_count,
            chars=total_chars,
            tables=sum(len(p.tables) for p in pages),
        )

        return ParsedDocument(
            filename=filename,
            page_count=page_count,
            pages=pages,
            full_text=full_text,
            content_hash=file_hash,
            text_density=text_density,
        )

    def _extract_blocks_pymupdf(self, page: fitz.Page, page_number: int) -> list[TextBlock]:
        blocks: list[TextBlock] = []
        dict_blocks = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]

        for block in dict_blocks:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(s.get("text", "") for s in spans).strip()
                if not text:
                    continue
                max_size = max(s.get("size", 12) for s in spans)
                is_bold = any("bold" in s.get("font", "").lower() for s in spans)
                block_type = self._infer_block_type(text, max_size, is_bold)
                bbox = tuple(line.get("bbox", (0, 0, 0, 0)))
                blocks.append(
                    TextBlock(
                        text=text,
                        page_number=page_number,
                        block_type=block_type,
                        font_size=max_size,
                        is_bold=is_bold,
                        bbox=bbox,
                    )
                )
        return blocks

    def _infer_block_type(self, text: str, font_size: float, is_bold: bool) -> str:
        stripped = text.strip()
        if len(stripped) < 120 and (font_size >= 14 or is_bold):
            if not stripped.endswith(".") or len(stripped.split()) <= 12:
                return "heading"
        if stripped.startswith(("•", "-", "*", "1.", "2.", "3.")):
            return "list_item"
        if stripped.startswith(("```", "def ", "class ", "import ", "const ")):
            return "code"
        return "paragraph"

    def _extract_tables_pdfplumber(
        self, file_bytes: bytes, page_number: int
    ) -> list[TableBlock]:
        tables: list[TableBlock] = []
        try:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                if page_number > len(pdf.pages):
                    return tables
                page = pdf.pages[page_number - 1]
                for table in page.extract_tables() or []:
                    if not table:
                        continue
                    headers = [str(c or "") for c in table[0]]
                    rows = [[str(c or "") for c in row] for row in table[1:]]
                    md = self._table_to_markdown(headers, rows)
                    tables.append(
                        TableBlock(
                            page_number=page_number,
                            headers=headers,
                            rows=rows,
                            markdown=md,
                        )
                    )
        except Exception as e:
            logger.warning("table_extraction_partial", page=page_number, error=str(e))
        return tables

    @staticmethod
    def _table_to_markdown(headers: list[str], rows: list[list[str]]) -> str:
        if not headers:
            return ""
        lines = [
            "| " + " | ".join(headers) + " |",
            "| " + " | ".join("---" for _ in headers) + " |",
        ]
        for row in rows:
            padded = row + [""] * (len(headers) - len(row))
            lines.append("| " + " | ".join(padded[: len(headers)]) + " |")
        return "\n".join(lines)

    @staticmethod
    def read_file_path(path: Path) -> tuple[bytes, str]:
        return path.read_bytes(), path.name

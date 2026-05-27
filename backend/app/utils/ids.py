"""Deterministic ID generation for incremental indexing."""

import hashlib
import re
import uuid
from pathlib import Path


def slugify(text: str, max_length: int = 80) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text[:max_length].strip("-") or "unknown"


def azure_safe_document_id(raw_id: str) -> str:
    """Azure AI Search keys: letters, digits, _, -, = only (no colons)."""
    safe = re.sub(r"[^a-zA-Z0-9_\-=]", "_", raw_id)
    return safe[:1024]


def content_hash(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()[:16]


def generate_document_id(filename: str, file_hash: str) -> str:
    base = slugify(Path(filename).stem)
    return f"doc-{base}-{file_hash[:8]}"


def generate_project_id(filename: str, file_hash: str, project_name: str = "") -> str:
    seed = f"{filename}:{file_hash}:{project_name}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


def generate_chunk_id(document_id: str, section_id: str, index: int) -> str:
    raw = f"{document_id}_chunk_{slugify(section_id)}_{index}"
    return azure_safe_document_id(raw)


def generate_section_id(document_id: str, title: str, page_start: int) -> str:
    raw = f"{document_id}_section_{slugify(title)}_p{page_start}"
    return azure_safe_document_id(raw)


def generate_entity_index_id(
    project_id: str,
    entity_type: str,
    entity_key: str,
) -> str:
    raw = f"{project_id}_{entity_type}_{slugify(entity_key)}"
    return azure_safe_document_id(raw)

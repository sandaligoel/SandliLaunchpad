#!/usr/bin/env python3
"""Merge backend modules into a single server.py file."""

from __future__ import annotations

import ast
import re
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = BACKEND_ROOT / "server.py"

INTERNAL_ROOTS = frozenset({"config", "schemas", "services", "api", "pipeline"})

BUNDLE_ORDER = [
    "config.py",
    "schemas/architecture_plan.py",
    "schemas/agent_workflow.py",
    "schemas/discovery.py",
    "schemas/agent_record.py",
    "schemas/extraction_output.py",
    "schemas/architecture_spec.py",
    "services/answer_utils.py",
    "services/agent_kind.py",
    "services/spec_validators.py",
    "services/llm.py",
    "pipeline/spec_loader.py",
    "services/data_storage.py",
    "services/graph_sanitizer.py",
    "services/chip_quality.py",
    "services/catalog_hints.py",
    "services/catalog_interview_context.py",
    "services/catalog_chip_suggestions.py",
    "services/cascading_options.py",
    "services/question_planner.py",
    "services/interview_intents.py",
    "services/interview_turn_intent.py",
    "services/interview_conversation.py",
    "services/clarifying_questions.py",
    "services/discovery_engine.py",
    "services/agent_input_chips.py",
    "services/agent_workflow_interview.py",
    "services/chat_assistant.py",
    "services/architecture_validator.py",
    "pipeline/chunker.py",
    "pipeline/embedder.py",
    "pipeline/pdf_reader.py",
    "pipeline/extractor.py",
    "pipeline/indexer.py",
    "services/architecture_planner.py",
    "services/architecture_remediation.py",
    "services/builder_sync.py",
    "services/dashboard_service.py",
    "services/interview.py",
    "api/session_store.py",
    "api/builder_store.py",
    "api/routes.py",
]


class _ImportStripper(ast.NodeTransformer):
    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.AST | None:
        if node.level and node.level > 0:
            return None
        if node.module and node.module.split(".")[0] in INTERNAL_ROOTS:
            return None
        return node

    def visit_Import(self, node: ast.Import) -> ast.AST | None:
        if all(alias.name.split(".")[0] in INTERNAL_ROOTS for alias in node.names):
            return None
        return node


class _FixEmptyBlocks(ast.NodeTransformer):
    def visit_If(self, node: ast.If) -> ast.If:
        node = self.generic_visit(node)
        if not node.body:
            node.body = [ast.Pass()]
        if not node.orelse and node.orelse is not None:
            pass
        return node

    def visit_Try(self, node: ast.Try) -> ast.Try:
        node = self.generic_visit(node)
        if not node.body:
            node.body = [ast.Pass()]
        return node


def strip_internal_imports(source: str) -> str:
    """Remove all imports from bundled backend packages (including lazy imports)."""
    tree = ast.parse(source)
    tree = _ImportStripper().visit(tree)
    tree = _FixEmptyBlocks().visit(tree)
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)


def patch_paths(source: str) -> str:
    source = source.replace(
        'Path(__file__).resolve().parent.parent / "prompts"',
        'BACKEND_ROOT / "prompts"',
    )
    source = source.replace(
        'Path(__file__).resolve().parent.parent / "data"',
        'BACKEND_ROOT / "data"',
    )
    source = source.replace(
        'Path(__file__).resolve().parent.parent / "data" / "spec.json"',
        'BACKEND_ROOT / "data" / "spec.json"',
    )
    source = source.replace(
        'Path(__file__).resolve().parent / "data"',
        'BACKEND_ROOT / "data"',
    )
    source = source.replace(
        'Path(__file__).resolve().parent.parent / "data" / "templates.json"',
        'BACKEND_ROOT / "data" / "templates.json"',
    )
    source = re.sub(
        r'Path\(__file__\)\.resolve\(\)\.parent\.parent',
        "BACKEND_ROOT",
        source,
    )
    source = re.sub(
        r'Path\(__file__\)\.resolve\(\)\.parent / "static"',
        'BACKEND_ROOT / "api" / "static"',
        source,
    )
    source = source.replace(
        "PROMPTS_DIR = Path(__file__).resolve().parent.parent / \"prompts\"",
        'PROMPTS_DIR = BACKEND_ROOT / "prompts"',
    )
    return source


def main() -> None:
    parts: list[str] = [
        '"""Agent Launchpad backend — single-file bundle. Regenerate: python scripts/bundle_server.py"""',
        "",
        "from __future__ import annotations",
        "",
        "import logging",
        "import os",
        "from pathlib import Path",
        "",
        "BACKEND_ROOT = Path(__file__).resolve().parent",
        "PROMPTS_DIR = BACKEND_ROOT / \"prompts\"",
        "DATA_DIR = BACKEND_ROOT / \"data\"",
        "SESSIONS_DIR = DATA_DIR / \"sessions\"",
        "",
    ]

    seen_future = True
    for rel in BUNDLE_ORDER:
        path = BACKEND_ROOT / rel
        if not path.is_file():
            raise SystemExit(f"Missing bundle file: {rel}")
        raw = path.read_text(encoding="utf-8")
        raw = strip_internal_imports(raw)
        raw = patch_paths(raw)
        lines = raw.splitlines()
        cleaned: list[str] = []
        for line in lines:
            if line.strip() == "from __future__ import annotations":
                if seen_future:
                    continue
            cleaned.append(line)
        body = "\n".join(cleaned).strip()
        parts.append(f"\n\n# {'=' * 72}\n# {rel}\n# {'=' * 72}\n\n")
        parts.append(body)

    parts.append(


        """

# ======================================================================
# FastAPI application
# ======================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

settings = get_settings()
configure_logging(settings.log_level)
get_data_storage()

app = FastAPI(
    title="Affine Agent Launchpad",
    description="Agent Launchpad — requirements interview and architecture planning",
    version="0.3.0",
)

_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def _on_startup() -> None:
    try:
        storage = get_data_storage()
        index_raw = storage.read_json(WORKFLOW_INDEX_KEY)
        if index_raw and index_raw.get("entries"):
            count = len(index_raw["entries"])
        else:
            count = rebuild_workflow_index()
        st = get_storage_status()
        logger.info(
            "Launchpad storage=%s sessions=%s workflows=%s",
            st.get("backend", "unknown"),
            st.get("session_blob_count", "?"),
            count,
        )
    except Exception as exc:
        logger.warning("Startup storage check failed: %s", exc)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui/")


@app.get("/health")
def health() -> dict:
    storage = get_storage_status()
    ok = storage.get("backend") == "local" or storage.get("reachable") is True
    return {
        "status": "ok" if ok else "degraded",
        "phase": 3,
        "features": ["interview", "architecture_plan"],
        "storage": storage,
    }


STATIC_DIR = BACKEND_ROOT / "api" / "static"
app.mount(
    "/ui",
    StaticFiles(directory=str(STATIC_DIR), html=True),
    name="launchpad-ui",
)
"""
    )

    merged = "\n".join(parts).strip() + "\n"
    merged = merged.replace("builder_store.", "")
    merged = merged.replace("session_store.", "")
    OUTPUT.write_text(merged, encoding="utf-8")
    print(f"Wrote {OUTPUT} ({OUTPUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()

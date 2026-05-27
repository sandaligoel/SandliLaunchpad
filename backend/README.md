# Affine Agent Catalog Builder

Offline pipeline that reads Affine Analytics' solutions PDF, extracts structured **AgentRecord** and **ProjectRecord** entries via Azure OpenAI, embeds agents with `text-embedding-3-large`, and indexes them into **Azure AI Search** for hybrid (keyword + vector + semantic) retrieval.

This catalog powers Phase 2+ of the Agent Launchpad (smart interview and architecture generation).

**Phase 2 (requirements interview)** is documented in [README_PHASE2.md](./README_PHASE2.md). Run the API with `uvicorn api.main:app --reload` and the UI from `../launchpad-ui`.

## Prerequisites

- Python 3.11+
- Azure OpenAI resource with:
  - Chat deployment (e.g. GPT-4.1) → `AZURE_OPENAI_CHAT_DEPLOYMENT`
  - Embedding deployment `text-embedding-3-large` (3072 dimensions)
- Azure AI Search service (Basic tier or higher recommended for semantic search)
- Catalog source: `./data/spec.json` (whole file, no PDF chunking). Set `PDF_PATH` in `.env` to that path (name is historical).

### `spec.json` format

Multi-project catalog (current):

```json
[
  { "project": { "name": "...", "client": "...", "vertical": "...", ... }, "agents": [ ... ] },
  { "project": { ... }, "agents": [ ... ] }
]
```

Legacy single-project shape is still supported:

```json
{ "project": { ... }, "agents": [ ... ] }
```

Vertical values like `Finance` or `Retail / CPG` are normalized to canonical enums (`Finance`, `Retail`, etc.). Duplicate agent names across projects get disambiguated ids (e.g. `roboflow-shelf-row-detector-affine-analytics-vto-platform`).

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Azure endpoints, keys, and deployment names
```

## Run order

Run these **in order** the first time:

```bash
# 1. Create the search index (once)
python scripts/create_index.py

# 2. Load whole spec.json and index all agents (no chunking, no LLM extract)
python -m pipeline.run --source ./data/spec.json

# 3. List what was indexed (no search scores)
python scripts/validate_catalog.py
```

Re-running step 2 is **idempotent**: documents are merged by `id`, so existing agents are updated rather than duplicated.

## Project layout

```
backend/
├── config.py                 # Settings from .env
├── pipeline/
│   ├── pdf_reader.py         # PyMuPDF page + section extraction
│   ├── chunker.py            # Project-level chunks
│   ├── extractor.py          # LLM → structured JSON
│   ├── embedder.py           # Azure OpenAI embeddings
│   ├── indexer.py            # Azure AI Search upload + search helper
│   └── run.py                # Full pipeline CLI
├── schemas/
│   ├── agent_record.py       # AgentRecord, ProjectRecord, slugify
│   └── extraction_output.py
├── prompts/                  # LLM system prompts
└── scripts/
    ├── create_index.py
    └── validate_catalog.py
```

## Output fields

### AgentRecord

| Field | Description |
|-------|-------------|
| `id` | Slugified unique key (e.g. `invoice-extraction-agent`) |
| `name` | Display name |
| `version` | Semantic version string (default `1.0`) |
| `category` | One of six Affine categories (Finance, Document, etc.) |
| `function_summary` | 1–2 sentence capability description |
| `inputs` / `outputs` | What the agent consumes and produces |
| `model_used` | LLM or ML model name |
| `tech_stack` | Frameworks and services |
| `integrations` | External systems (SAP, Outlook, etc.) |
| `origin_project` / `origin_client` | Source engagement |
| `vertical` | CPG, Retail, Healthcare, Manufacturing, Other |
| `status` | `live`, `available`, or `deprecated` |
| `typical_accuracy` | Optional metric string |
| `notes` | Caveats or config requirements |
| `source_page` | PDF page for traceability |
| `embedding` | 3072-dim vector (set by embedder, stored in index) |

### ProjectRecord

Extracted per chunk for context; used during agent extraction (`origin_project`, `origin_client`) but not indexed in Phase 1.

| Field | Description |
|-------|-------------|
| `name` / `client` / `vertical` | Engagement metadata |
| `business_problem` | Manual process before automation |
| `solution_summary` | What was built |
| `agents_used` | Agent names mentioned in text |
| `tech_stack` / `outcomes` | Stack and results if stated |

## Tuning tips

- **Noisy PDF text**: Prefer tuning `chunker.py` boundaries before changing LLM prompts.
- **PowerPoint exports**: `get_text("blocks")` ordering is used when blocks are present.
- **Few section headers**: Pipeline falls back to 3-page windows (see logs).
- **Rate limits**: Embedding batches are size 16 with 1s pause; extraction retries with 2s/4s/8s backoff.

## Environment variables

See `.env.example` for all required variables. `config.py` validates required vars on startup and logs a masked summary (keys show last 4 characters only).

## License

Internal Affine Analytics tooling.

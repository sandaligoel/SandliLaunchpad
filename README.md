# Agent Knowledge Retrieval System

Enterprise **AI architecture memory platform** — ingests solution PDFs, extracts structured knowledge (agents, workflows, architectures, tech stacks), generates embeddings, and indexes into **Azure AI Search** for hybrid semantic retrieval.

> This is not document storage or a chatbot. It is a **three-problem platform**: queryable PDF catalog, smart spec interview, and architecture graph generation.

## The three problems (all implemented)

| # | Problem | What Launchpad does |
|---|---------|---------------------|
| 1 | **Make the PDF queryable** | `solution_agents.pdf` → structured agents/projects in Azure AI Search |
| 2 | **Smart interview** | Problem statement → fill 14 spec slots with targeted questions only |
| 3 | **Generate & render architecture** | Complete spec → catalog match → reuse/build → graph → Studio UI + **Cursor canvas** |

**Full workflow:** Ingest catalog → Interview → Plan → View graph at `/` or paste JSON into `architecture-graph.canvas.tsx` in Cursor Canvases.

Sessions and plans persist under `data/sessions/` (survive server restart).

## Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for the full design: data flow, chunking, extraction, embedding, search schema, and Phase 2 hooks.

## Prerequisites

- Python 3.11+
- Azure OpenAI resource with:
  - Chat deployment: `gpt-5.4` (or your deployment name)
  - Embedding deployment: `text-embedding-3-large` (3072 dims recommended)
- Azure AI Search service (Basic tier or higher; vector search enabled)

## Quick Start

```bash
cd /Users/sandligoyal/Launchpad
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your Azure credentials
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

OpenAPI docs: http://localhost:8000/docs

**Architecture Studio UI:** http://localhost:8000/ — Interview → Architecture graph → Catalog search

### Architecture flow UI (React + XYFlow)

The Phase 3 graph is a **node-based DAG** (zoom, pan, minimap, parallel groups, run simulation). Build after changing `frontend/`:

```bash
cd frontend && npm install && npm run build
```

Output: `app/static/architecture/assets/index.js` (served at `/static/architecture/`).

### Smart interview (Problem 2)

```bash
curl -X POST http://localhost:8000/api/v1/interview/start \
  -H "Content-Type: application/json" \
  -d '{"problem_statement": "We need a KYC pre-screening system for corporate onboarding with UBO extraction, policy validation, risk scoring, and analyst review. Must run on Azure with GraphRAG for document Q&A."}'

# Use session_id and question from response, then:
curl -X POST http://localhost:8000/api/v1/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"session_id": "<SESSION_ID>", "answer": "Finance / KYC. Azure only. Human review for emails."}'
```

### Architecture graph (Problem 3)

```bash
# Replace YOUR-UUID with session_id from interview/start (not the literal string SESSION_ID)
curl -X POST http://localhost:8000/api/v1/interview/YOUR-UUID/plan

# Reload saved plan without regenerating
curl http://localhost:8000/api/v1/interview/YOUR-UUID/plan
```

**Cursor canvas:** Open `architecture-graph.canvas.tsx` from Cursor Canvases → paste plan JSON → **Load graph** (DAG layout with reuse/build colors).

## Environment Variables

Copy `.env.example` to `.env`. Required variables:

| Variable | Description |
|----------|-------------|
| `AZURE_OPENAI_ENDPOINT` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | API key |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | GPT deployment name (e.g. `gpt-5.4`) |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding deployment |
| `AZURE_OPENAI_EMBEDDING_DIMENSIONS` | Must match index (default `3072`) |
| `AZURE_SEARCH_ENDPOINT` | Search service URL |
| `AZURE_SEARCH_API_KEY` | Search admin key |
| `AZURE_SEARCH_INDEX_NAME` | Index name (default `ai-architecture-knowledge`) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/ingest/pdf` | PDF ingest (auto-detects solution catalog) |
| `POST` | `/api/v1/interview/start` | Start smart interview (Problem 2) |
| `POST` | `/api/v1/interview/answer` | Answer interview question |
| `GET` | `/api/v1/interview/sessions` | List persisted interview session IDs |
| `POST` | `/api/v1/interview/{id}/plan` | Generate architecture graph (Problem 3) |
| `GET` | `/api/v1/interview/{id}/plan` | Load last saved plan for session |
| `POST` | `/api/v1/architecture/plan` | Generate graph from session or spec |
| `POST` | `/api/v1/ingest/catalog` | Solution catalog PDF (`solution_agents.pdf`) |
| `POST` | `/api/v1/ingest/spec` | Ingest structured spec JSON (bundled or upload) |
| `POST` | `/api/v1/ingest/spec/body` | Ingest spec from JSON request body |
| `POST` | `/api/v1/search` | General hybrid search |
| `POST` | `/api/v1/search/agents` | Agent-centric search |
| `POST` | `/api/v1/search/architectures` | Architecture pattern search |

## Example Requests

### Ingest solution catalog PDF (main document)

Bundled at `data/documents/solution_agents.pdf` — **6 solutions**, **43+ agents** (JPMC KYC, VTO, Aira, Merchandising, Mars Sales Genie, etc.):

```bash
# Dedicated catalog endpoint (rule-based parser, no LLM extraction — fast)
curl -X POST "http://localhost:8001/api/v1/ingest/catalog"

# Or upload the PDF
curl -X POST "http://localhost:8001/api/v1/ingest/catalog" \
  -F "file=@data/documents/solution_agents.pdf"

# Generic PDF endpoint auto-detects catalog format too
curl -X POST "http://localhost:8001/api/v1/ingest/pdf" \
  -F "file=@data/documents/solution_agents.pdf"
```

### Ingest bundled spec (JPMC KYC example)

The repo includes `data/specs/spec.json` — 10 agents from the JPMC KYC UBO GraphRAG project:

```bash
# Index bundled spec without uploading a file
curl -X POST "http://localhost:8000/api/v1/ingest/spec"

# Or upload your own spec.json
curl -X POST "http://localhost:8000/api/v1/ingest/spec" \
  -F "file=@data/specs/spec.json"
```

### Ingest PDF

```bash
curl -X POST "http://localhost:8000/api/v1/ingest/pdf" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@/path/to/ai-solution-architecture.pdf"
```

### General Search (hybrid)

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Find projects using GPT-4 with RAG",
    "top_k": 10,
    "mode": "hybrid",
    "filters": {
      "retrieval_used": true,
      "models_used": ["GPT-4"]
    }
  }'
```

### Agent Search

```bash
curl -X POST "http://localhost:8000/api/v1/search/agents" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "recommendation agents used in retail systems",
    "top_k": 10,
    "mode": "hybrid",
    "filters": {
      "industry": "retail"
    }
  }'
```

### Architecture Search

```bash
curl -X POST "http://localhost:8000/api/v1/search/architectures" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "multi-agent orchestration supervisor pattern",
    "top_k": 10,
    "mode": "hybrid",
    "filters": {
      "cloud_provider": "Azure"
    }
  }'
```

### Voice / Escalation Queries

```bash
# Voice-enabled support systems
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "voice-enabled customer support AI systems", "mode": "semantic", "top_k": 10}'

# Human escalation agents
curl -X POST "http://localhost:8000/api/v1/search/agents" \
  -H "Content-Type: application/json" \
  -d '{"query": "agents handling human escalation to live agents", "mode": "hybrid", "top_k": 10}'
```

## Project Structure

```
app/
  api/           # FastAPI routes
  core/          # Config, logging, exceptions, retry
  schemas/       # Pydantic domain + API models
  parsers/       # Hybrid PDF parser (PyMuPDF + pdfplumber)
  chunkers/      # Semantic section-based chunking
  extractors/    # GPT structured extraction (2-pass)
  embeddings/    # Azure OpenAI embeddings
  search/        # Index manager + query builder
  services/      # Ingestion, indexing, search orchestration
  prompts/       # Versioned extraction prompts
  utils/         # IDs, text normalization
```

## Pipeline Overview

1. **Parse** — PyMuPDF blocks + pdfplumber tables; scanned PDF detection
2. **Chunk** — Section-type classification; hierarchy; size guardrails
3. **Extract** — Per-chunk grounded JSON → merge into `ProjectKnowledge`
4. **Embed** — Canonical text per project/agent/workflow/architecture/chunk
5. **Index** — Upsert to Azure AI Search with deterministic IDs (incremental)

## Incremental Indexing

Entity IDs are deterministic: `{project_id}:{entity_type}:{slug}`. Re-uploading the same PDF updates existing documents without duplicates.

## Phase 2 Roadmap (not yet built)

- OCR for scanned PDFs
- Graph database (Neo4j / Cosmos Gremlin) for cross-project relationships
- Live agent deployment / wiring (today: recommendations only)
- Evaluation harness for extraction quality

## License

Proprietary — internal enterprise use.

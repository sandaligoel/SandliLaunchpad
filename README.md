# AFFINE — Agent Launchpad

Affine Agent Catalog (Phase 1) and smart requirements interview (Phase 2).

## Projects

| Directory | Phase | Description |
|-----------|-------|-------------|
| [agent_catalog/](agent_catalog/) | 1 & 2 | Catalog JSON ingest, Azure AI Search index, FastAPI interview API |
| [launchpad-ui/](launchpad-ui/) | 2 | Optional React UI (requires Node.js) |

## Quick start

See [agent_catalog/README.md](agent_catalog/README.md) for Phase 1 (catalog index) and [agent_catalog/README_PHASE2.md](agent_catalog/README_PHASE2.md) for Phase 2 (interview UI at `/ui/`).

```bash
cd agent_catalog
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add your Azure keys
python scripts/create_index.py
python -m pipeline.run --source ./data/spec.json
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/ui/ for the Phase 2 interview.

## Phase 3

Planned: architecture generation from completed spec + catalog search.

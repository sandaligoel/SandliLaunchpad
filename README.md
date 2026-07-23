# Eryl Semantic Search Workflow

Production-grade multi-agent workflow: **query transform → vector/graph retrieve → answer → critic evaluation**.

All five graph nodes reuse the frozen `eryl_semantic_rag_agent_chain` package (AutoGen + Azure OpenAI + Azure AI Search).

## Quickstart

```bash
git clone <this-repo>
cd <repo-root>

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# Fill in real Azure OpenAI + Azure AI Search credentials (see below)

python main.py --health
python main.py --dry-run --input-json examples/sample_question.json
python main.py --input-json examples/sample_question.json
```

### Run with a plain-text question

```bash
python main.py --question "What is the return policy for defective products?"
```

### Run with a file

```bash
python main.py --file examples/sample_question.json
```

### HTTP API

```bash
python main.py --serve --port 8080
# POST http://127.0.0.1:8080/workflows/query-transformer  {"user_question": "..."}
# POST http://127.0.0.1:8080/workflows/critic             {"data": {"user_question": "..."}}
```

## Required environment variables

| Variable | Purpose |
|----------|---------|
| `GPT4_LLM_MODEL_DEPLOYMENT_NAME` | Azure OpenAI chat deployment (GPT-4-class) |
| `AZURE_OPENAI_API_BASE` | Azure OpenAI endpoint URL |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_API_VERSION` | API version (e.g. `2024-02-15-preview`) |
| `EMBEDDING_MODEL_DEPLOYMENT_NAME` | Embedding deployment (e.g. `text-embedding-3-small`) |
| `AZURE_SEARCH_SERVICE_ENDPOINT` | Azure AI Search endpoint |
| `AZURE_SEARCH_API_KEY` | Azure AI Search admin/query key |
| `AZURE_SEARCH_INDEX_NAME` | Search index (default: `dupont_email_demo`) |
| `ERYL_VECTOR_DATA` or `ERYL_VECTOR_DATA_PATH` | Static vector routing metadata (see `examples/vector_metadata.txt`) |

Optional: `ERYL_LOCAL_CONTEXT_MODULE` — Python module exporting `Localcontext_builder` for graph retrieval.

Missing required variables raise `ConfigurationError` with the variable name — never a silent mock.

## Makefile targets

```bash
make install   # venv + pip install
make health    # integration health checks
make dry-run   # orchestration without live external calls
make test      # pytest
make check     # placeholder scan
make verify    # install + check + test + dry-run + import check
```

## Architecture

```
user_question
    → query-transformer  (reuse: ErylChainRunner)
    → eryl-selector
    → retriever          (extract_context → Azure AI Search)
    → llm-answer-maker
    → critic
    → final_answer + confidence_score
```

- **Orchestration:** `run_workflow.py` — `run_workflow_from_node(node_id, payload)`
- **I/O adapters:** `agent_runtime/adapters.py` (graph ↔ chain contract mapping)
- **Frozen reuse:** `agent_library/reuse/eryl_semantic_rag_agent_chain/` — do not edit

## Development

```bash
python scripts/check_placeholders.py
python -m pytest tests/ -q
python main.py --dry-run --input-json examples/sample_question.json
```

CI (`.github/workflows/verify.yml`) runs the same checks on pull requests.

## AFFINE Launchpad platform

This repository also contains the AFFINE Agent Launchpad platform under `backend/` and `frontend/`. See `docs/PROJECT_HANDOFF.md` for platform development.

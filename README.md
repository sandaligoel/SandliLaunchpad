# KYC Pipeline

Automate document KYC checks with a two-step workflow: **Ingest Docs** → **Validate KYC**.

## Quick start

```bash
git clone <this-repo>
cd <this-repo>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --health
python main.py --file examples/sample_kyc_document.txt
```

## Workflow

| Step | Node | Description |
|------|------|-------------|
| 1 | `ingest` | Read PDF/DOCX/TXT KYC documents and extract normalized text |
| 2 | `validate` | Check extracted content against `config/kyc_policy.json` completeness rules |

Execution order is defined in `workflow.json` and wired in `run_workflow.py`.

## CLI

```bash
python main.py --help
python main.py --health
python main.py --dry-run
python main.py --file examples/sample_kyc_document.txt
python main.py --document-text "Legal Name: Example Corp" --filename example.txt
python main.py --input-json examples/input.json
python main.py --serve --host 0.0.0.0 --port 8000
```

## HTTP API

FastAPI endpoints mirror the workflow entrypoints:

- `GET /health` — policy file and integration health
- `POST /workflows/ingest` — start workflow at ingest (body: `{"data": {"file_path": "..."}}`)
- `POST /workflows/validate` — start workflow at validate (body: `{"data": {...}}`)

## Configuration

Copy `.env.example` to `.env`:

| Variable | Required | Description |
|----------|----------|-------------|
| `KYC_POLICY_PATH` | No (default: `config/kyc_policy.json`) | KYC completeness policy JSON |
| `DRY_RUN` | No | When `true`, skips live file parsing boundaries |

Missing required configuration raises `ConfigurationError` with the variable name.

## Makefile targets

```bash
make install
make health
make dry-run
make run
make test
make check
make verify
```

## Project layout

```
main.py                    # CLI + FastAPI
config.py                  # pydantic-settings
run_workflow.py            # graph orchestration
workflow.json              # LaunchPad export (source of truth)
workflow_manifest.json     # wiring manifest
agent_library/build/       # ingest + validate implementations
agent_runtime/adapters.py  # pure I/O adapters
examples/                  # real input artifacts
tests/                     # integration tests
```

## Development

```bash
python scripts/check_placeholders.py
python -m pytest tests/ -q
python main.py --dry-run
```

CI runs the same checks via `.github/workflows/verify.yml`.

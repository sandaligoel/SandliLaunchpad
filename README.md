# KYC Pipeline

Automate document KYC checks with a two-step workflow:

1. **Ingest Docs** — parse PDF, DOCX, TXT, or JSON KYC documents and extract identity fields.
2. **Validate KYC** — apply completeness and format checks against configurable KYC rules.

## Quick start

```bash
git clone <this-repo>
cd <repo-root>
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python main.py --health
python main.py --file examples/sample_kyc.txt
```

Expected live run output includes `ingest_output` with extracted fields and `validate_output.status` of `pass` for the bundled sample document.

## CLI

```bash
python main.py --help
python main.py --health
python main.py --dry-run
python main.py --file examples/sample_kyc.txt
python main.py --input-json examples/sample_payload.json
python main.py --node validate --input-json examples/sample_payload.json
```

`--dry-run` executes the full ingest → validate orchestration against `examples/sample_kyc.txt` without external service calls.

## HTTP API

Start the server:

```bash
python main.py --serve --host 127.0.0.1 --port 8080
```

Endpoints:

- `GET /health` — dependency health summary
- `POST /ingest` — intake endpoint (`document_path` or `ingest` body)
- `POST /validate` — terminal validation endpoint (`validate` or `ingest_output` body)
- `POST /workflow/{node_id}` — generic workflow entrypoint

Example:

```bash
curl -s http://127.0.0.1:8080/health
curl -s -X POST http://127.0.0.1:8080/ingest \
  -H 'Content-Type: application/json' \
  -d '{"document_path":"examples/sample_kyc.txt"}'
```

## Configuration

Copy `.env.example` to `.env` and adjust optional validation settings:

| Variable | Purpose |
|----------|---------|
| `APP_NAME` | Application display name |
| `LOG_LEVEL` | Logging verbosity |
| `KYC_REQUIRED_FIELDS` | Comma-separated required identity fields |
| `KYC_ID_PATTERN` | Regex for government ID validation |
| `KYC_MIN_DOCUMENT_TEXT_LENGTH` | Minimum extracted text length |

No cloud credentials are required for the default local document workflow.

## Project layout

```
main.py
config.py
run_workflow.py
workflow.json
workflow_manifest.json
agent_library/
  base/
  build/ingest/
  build/validate/
  reuse/
agent_runtime/adapters.py
integrations/
examples/
tests/
scripts/check_placeholders.py
Makefile
```

## Development

```bash
make install
make check
make test
make dry-run
make verify
```

## Workflow graph

```
ingest → validate
```

Export metadata is preserved in `workflow.json`, `session.json`, and `agents/*.json`.

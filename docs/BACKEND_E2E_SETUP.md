# End-to-end backend setup (AFFINE)

Complete path from zero → interview + architecture API working with AgentForge UI.

---

## Architecture

```text
Browser (localhost:5173)
    │  /api/sessions, /health  → Vite proxy
    ▼
FastAPI (backend) :8003 or :8004
    ├── data/sessions/*.json     (interview persistence)
    ├── Azure OpenAI             (questions + spec + architecture)
    └── Azure AI Search          (agent catalog)
```

Optional cloud path:

```text
ACR image → Container App (HTTPS) → same API, env vars from Azure
```

Image already built: `749b44415c9d4d2b9052d2b2d61f491c.azurecr.io/affine-agent-catalog:v1`

---

## Phase 1 — One-time backend setup

### 1.1 Python environment

```bash
cd /Users/gurucharanm/projects/AFFINE/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 1.2 Fill `backend/.env`

| Variable | Purpose |
|----------|---------|
| `AZURE_OPENAI_*` | Chat + embeddings for interview |
| `AZURE_SEARCH_*` | Catalog retrieval |
| `AZURE_SEARCH_INDEX_NAME` | Usually `agentic-launchpad` |
| `PDF_PATH` | `./data/spec.json` |
| `CORS_ORIGINS` | Include `http://localhost:5173` |

### 1.3 Index the agent catalog (one-time)

```bash
source .venv/bin/activate
python scripts/create_index.py
python -m pipeline.run --source ./data/spec.json
python scripts/validate_catalog.py
```

---

## Phase 2 — Run backend every day

### Terminal 1 — AFFINE API

```bash
cd /Users/gurucharanm/projects/AFFINE/backend
source .venv/bin/activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8003
```

Confirm:

```bash
curl http://127.0.0.1:8003/health
# {"status":"ok","phase":3,...}
```

If you use **8004** instead, match that port everywhere below.

### Terminal 2 — Mock API (dashboard data)

```bash
cd /Users/gurucharanm/projects/AFFINE
./scripts/start-mock-api.sh
```

### Terminal 3 — UI

```bash
cd /Users/gurucharanm/projects/AFFINE/frontend
npm run dev
```

### 2.1 UI env (`frontend/.env.local`)

```env
AFFINE_API_TARGET=http://127.0.0.1:8003
VITE_AFFINE_API_BASE=
VITE_MOCK_API_TARGET=http://127.0.0.1:3001
```

Restart `npm run dev` after any change.

---

## Phase 3 — Verify end-to-end

```bash
chmod +x scripts/verify-backend-e2e.sh
AFFINE_API_PORT=8003 ./scripts/verify-backend-e2e.sh
```

Manual UI test:

1. http://localhost:5173/interview  
2. Enter problem statement → interview questions flow  
3. Complete → Workflow Builder opens  
4. **Workflows** tab lists saved flows  

Data checks:

```bash
ls -lt backend/data/sessions/ | head -3
```

---

## Phase 4 — Azure backend (production)

| Step | Status / action |
|------|-----------------|
| Image in ACR | Done — `affine-agent-catalog:v1` |
| Container App URL | Needs admin or Contributor on RG **Affine** |
| Env vars on container | Copy all from `backend/.env` |
| UI connect | `AFFINE_API_TARGET=https://<fqdn>` |

See [CONNECT_AZURE_BACKEND.md](./CONNECT_AZURE_BACKEND.md).

---

## API reference (backend surface)

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/health` | Liveness |
| POST | `/api/sessions` | Start interview |
| GET | `/api/sessions/{id}` | Load session |
| POST | `/api/sessions/{id}/turn` | Answer question |
| POST | `/api/sessions/{id}/architecture` | Generate plan |
| GET | `/api/sessions/{id}/architecture` | Get plan |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| UI “API offline” | API not running; wrong port in `AFFINE_API_TARGET` |
| 8003 vs 8004 | `curl` both `/health`; align `.env.local` |
| Empty catalog in interview | Re-run `pipeline.run` + check Search index name |
| Session not found | Wrong API port; or file missing under `data/sessions/` |
| Azure 502 | Container env vars missing |

---

## Quick start (copy/paste)

```bash
# Terminal 1
cd backend && source .venv/bin/activate && uvicorn api.main:app --reload --host 127.0.0.1 --port 8003

# Terminal 2
./scripts/start-mock-api.sh

# Terminal 3
cd frontend && npm run dev

# Verify
./scripts/verify-backend-e2e.sh
```

Open: http://localhost:5173/interview

# AFFINE — Agent Launchpad

Agent requirements interview, architecture planning, and visual workflow builder for Affine Analytics.

## Repository layout

```
AFFINE/
├── backend/          # Python FastAPI — interview API, catalog, Azure storage
├── frontend/         # React (Vite) — Agent Launchpad UI
├── mock-api/         # Optional Node mock — dashboard demo data (port 3001)
├── config/           # Fixed dev ports (dev-ports.json)
├── scripts/          # Start / sync / verify helpers
└── docs/             # Setup guides for your team
```

## Quick start (local)

**Full guide:** [docs/EMPLOYEE_SETUP.md](docs/EMPLOYEE_SETUP.md)

```bash
# One-time
./scripts/sync-dev-env.sh
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # add Azure keys (see docs/WHAT_TO_SHARE.md)
cd ../frontend && npm install
cd ../mock-api && npm install   # optional, for Dashboard

# Every day — 3 terminals
./scripts/start-backend.sh      # → http://127.0.0.1:8003
./scripts/start-mock-api.sh     # → http://127.0.0.1:3001 (optional)
cd frontend && npm run dev      # → http://localhost:5173
```

| Screen | URL |
|--------|-----|
| Agent Launchpad (interview) | http://localhost:5173/interview |
| Workflow builder | http://localhost:5173/builder |
| Workflows (saved) | http://localhost:5173/workflows |

Ports are defined in [config/dev-ports.json](config/dev-ports.json) — do not change per developer without updating that file.

## What to give a new teammate

See [docs/WHAT_TO_SHARE.md](docs/WHAT_TO_SHARE.md) (repo access + Azure credentials checklist, no secrets in git).

## Backend docs

- [backend/README.md](backend/README.md) — catalog index & pipeline
- [backend/README_PHASE2.md](backend/README_PHASE2.md) — interview API
- [backend/README_PHASE3.md](backend/README_PHASE3.md) — architecture planning

## Azure

Sessions and workflow canvases persist to **Azure Blob** when `backend/.env` has `DATA_STORAGE_BACKEND=blob` and valid storage credentials.

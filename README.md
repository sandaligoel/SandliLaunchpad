# AFFINE — Agent Launchpad

Agent requirements interview, architecture planning, and visual workflow builder for Affine Analytics.

## Repository layout

```
AFFINE/
├── backend/          # Python FastAPI — interview, catalog, Azure storage
├── frontend/         # React (Vite) — Agent Launchpad UI
├── config/           # Dev port defaults + runtime-ports.json (auto)
├── scripts/          # start-backend, sync-dev-env, doctor
└── docs/             # Setup and architecture guides
```

## Quick start

**Guide:** [docs/EMPLOYEE_SETUP.md](docs/EMPLOYEE_SETUP.md) · **Ports/health:** `./scripts/doctor.sh`

```bash
# One-time
./scripts/sync-dev-env.sh
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env   # Azure keys — see docs/WHAT_TO_SHARE.md
cd ../frontend && npm install

# Every day — 2 terminals
./scripts/start-backend.sh
cd frontend && npm run dev
```

| Screen | URL |
|--------|-----|
| Agent Launchpad (chat) | http://localhost:5173/interview |
| Workflow builder | http://localhost:5173/builder |
| Workflows (saved) | http://localhost:5173/workflows |

Ports: [config/dev-ports.json](config/dev-ports.json) + gitignored `config/runtime-ports.json`. After backend restarts, run `./scripts/sync-dev-env.sh` and restart `npm run dev`.

## Docs

- [START.md](START.md) — short daily commands
- [docs/STORAGE_ARCHITECTURE.md](docs/STORAGE_ARCHITECTURE.md) — API + Azure persistence
- [docs/EMPLOYEE_SETUP.md](docs/EMPLOYEE_SETUP.md) — full onboarding
- [backend/README.md](backend/README.md) — catalog index & pipeline

## Azure

Sessions and workflows persist to **Azure Blob** when `backend/.env` has `DATA_STORAGE_BACKEND=blob` and valid storage credentials.

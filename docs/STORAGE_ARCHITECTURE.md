# Launchpad storage & API architecture

Agent Launchpad uses a **single FastAPI backend** and **server-side persistence**. The browser does not store user sessions or workflow graphs in `localStorage`.

## Data flow

```
Browser (React)
    │  /api/* and /health → Vite proxy → FastAPI
    ▼
FastAPI (AFFINE backend)
    │  DATA_STORAGE_BACKEND=blob  →  Azure Blob (launchpad/sessions/, launchpad/workflows/)
    │  DATA_STORAGE_BACKEND=local →  backend/data/blob_mirror/  (dev only)
    ▼
Read-only: backend/data/spec.json, backend/data/templates.json
```

## API surface (all on FastAPI)

| Area | Endpoints |
|------|-----------|
| Chat | `POST/GET /api/sessions`, `POST .../turn` |
| Builder | `GET/PUT /api/sessions/{id}/builder` |
| Workflows list | `GET /api/launchpad/workflows` |
| Catalog | `GET /api/catalog/agents` |
| Dashboard | `GET /api/dashboard/*` (derived from real sessions/workflows) |
| Templates | `GET /api/templates` |
| Health | `GET /health` |

There is **no separate mock server** — one FastAPI process serves all routes.

## What lives where

| Data | Location |
|------|----------|
| Interview chat + spec | Azure/disk via `session_store` |
| Workflow canvas | `workflows/{sessionId}.json` in storage |
| Agent catalog | `backend/data/spec.json` |
| Templates | `backend/data/templates.json` |
| Session pointer in browser | URL `?sessionId=` only |

## Browser rules

- No `localStorage` for Launchpad user data.
- API failures show errors; no silent browser cache fallback.

## Dev stack (2 processes)

```bash
./scripts/start-backend.sh    # FastAPI
cd frontend && npm run dev    # Vite UI
```

Run `./scripts/sync-dev-env.sh` after backend port changes.

## Operational checklist

1. `GET /health` → `storage.backend: azure_blob`, `reachable: true`
2. New chat: `/interview?fresh=1`
3. Workflows: `/workflows` → `GET /api/launchpad/workflows`
4. Dashboard KPIs/charts reflect saved sessions and workflows (empty until you use Launchpad)

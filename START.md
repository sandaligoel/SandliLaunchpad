# Start AFFINE Agent Launchpad (local)

**Primary UI:** `agentforge-ui/` (AgentForge shell — matches product screenshots).  
**Legacy UI:** `launchpad-ui/` (minimal interview + architecture; kept for reference).

Use **three terminals** for the full AgentForge experience (mock data + AFFINE API ready for later wiring).

## Stuck? Reset ports first

```bash
chmod +x scripts/dev-reset.sh scripts/start-dev.sh scripts/start-agentforge-mock.sh scripts/clean-sessions.sh
./scripts/dev-reset.sh
```

Ports cleared: **3001** (mock API), **8003** (AFFINE), **5173** (Vite).

## One-time setup

```bash
# AFFINE backend
cd agent_catalog
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # Azure OpenAI + Search

# AgentForge UI + mock API
cd ../agentforge-ui && npm install
cd ../agentforge-mock-api && npm install

# Optional: catalog index
cd ../agent_catalog
python scripts/create_index.py
python -m pipeline.run --source ./data/spec.json
```

Copy env for UI (optional):

```bash
cp agentforge-ui/.env.example agentforge-ui/.env.local
```

## Verify backend (health + session + disk)

```bash
chmod +x scripts/verify-backend-e2e.sh scripts/start-affine-api.sh
./scripts/verify-backend-e2e.sh
# If API runs on 8004: AFFINE_API_PORT=8004 ./scripts/verify-backend-e2e.sh
```

Full checklist: [docs/BACKEND_E2E_SETUP.md](docs/BACKEND_E2E_SETUP.md)

## Every day — 3 terminals

**Terminal 1 — AFFINE API (port 8003)**

```bash
./scripts/start-affine-api.sh
# or: cd agent_catalog && source .venv/bin/activate && uvicorn api.main:app --reload --host 127.0.0.1 --port 8003
```

**Terminal 2 — Mock AgentForge API (port 3001)** — powers Dashboard, Workflows, Agent Library, Runs

```bash
./scripts/start-agentforge-mock.sh
```

**Terminal 3 — AgentForge UI (port 5173)**

```bash
cd agentforge-ui && npm run dev
```

Open **http://localhost:5173**

| Screen | Route |
|--------|--------|
| Dashboard | `/` |
| Workflow Builder | `/builder` |
| Workflows | `/workflows` |
| Agent Library | `/agents` |
| AFFINE interview (later) | `/interview` |

Fresh browser session: **http://localhost:5173/?fresh=1**

## Legacy UI (2 terminals only)

```bash
# Terminal 1: uvicorn on 8003 (as above)
# Terminal 2:
cd launchpad-ui && npm run dev
```

## Common problems

| Symptom | Fix |
|--------|-----|
| Dashboard / Workflows empty or errors | Start **mock API** on 3001 (`start-agentforge-mock.sh`). |
| Interview / AFFINE errors | Start **uvicorn** on 8003; use `/interview`. |
| Port 5173 in use | `./scripts/dev-reset.sh` then `npm run dev` again. |
| Stale session | `?fresh=1` or **New interview** on `/interview`. |

## Port alignment

`agentforge-ui/vite.config.ts` proxies:

- `/api/sessions` + `/health` → **8003** (AFFINE)
- other `/api/*` → **3001** (mock)

Legacy `launchpad-ui/vite.config.ts` proxies all `/api` to **8003**.

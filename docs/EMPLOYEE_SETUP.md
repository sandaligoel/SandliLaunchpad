# Employee setup — AFFINE Agent Launchpad

Use this guide after cloning the repo. Estimated time: **30–45 minutes** (mostly Azure access).

## Prerequisites

- **macOS** or Linux (Windows: use WSL2)
- **Python 3.11+**
- **Node.js 20+** and npm
- **Git**
- Azure credentials from your lead (see [WHAT_TO_SHARE.md](./WHAT_TO_SHARE.md))

## 1. Clone the repository

```bash
git clone <YOUR_REPO_URL>
cd AFFINE
```

## 2. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `backend/.env` with values your lead shared (OpenAI, AI Search, Blob storage).

Verify (from repo root, backend still activated):

```bash
cd ..
./scripts/start-backend.sh
```

In another terminal:

```bash
curl http://127.0.0.1:8003/health
```

You should see `"status":"ok"` and storage info.

## 3. Frontend setup

```bash
cd frontend
npm install
cd ..
./scripts/sync-dev-env.sh
npm run dev --prefix frontend
```

Open **http://localhost:5173/interview**

`sync-dev-env.sh` writes `frontend/.env.local` to match `config/runtime-ports.json`.

## 4. Daily workflow

| Terminal | Command |
|----------|---------|
| 1 | `./scripts/start-backend.sh` |
| 2 | `cd frontend && npm run dev` |

Check everything:

```bash
./scripts/doctor.sh
```

## 5. Main URLs

| Page | Path |
|------|------|
| Interview | `/interview` |
| Workflow builder | `/builder` |
| Saved workflows | `/workflows` |
| Agent library | `/agents` |
| Dashboard | `/dashboard` |

## 6. Catalog index (first time only)

If interview does not show catalog hints:

```bash
cd backend && source .venv/bin/activate
python scripts/create_index.py
python -m pipeline.run --source ./data/spec.json
```

## Common issues

- **Red banner “Cannot reach AFFINE API”** — run `./scripts/doctor.sh`; start backend; run `./scripts/sync-dev-env.sh` and restart `npm run dev`.
- **Proxy errors (ECONNREFUSED)** — UI port does not match backend; restart both after `sync-dev-env.sh`.
- **Sessions not shared with team** — ensure `DATA_STORAGE_BACKEND=blob` and Azure storage credentials in `backend/.env`.

## More documentation

- [WHAT_TO_SHARE.md](./WHAT_TO_SHARE.md) — credentials checklist for leads
- [STORAGE_ARCHITECTURE.md](./STORAGE_ARCHITECTURE.md) — API + persistence
- [CONNECT_AZURE_BACKEND.md](./CONNECT_AZURE_BACKEND.md) — deployed API

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

`sync-dev-env.sh` writes `frontend/.env.local` so the UI proxies to port **8003**.

## 4. Mock API (optional — Dashboard only)

Launchpad (**Interview**, **Builder**, **Workflows**) uses the **backend** only.

The **Dashboard** and **Templates** pages need the mock API:

```bash
./scripts/start-mock-api.sh
```

## 5. Daily workflow

| Terminal | Command |
|----------|---------|
| 1 | `./scripts/start-backend.sh` |
| 2 | `./scripts/start-mock-api.sh` *(optional)* |
| 3 | `cd frontend && npm run dev` |

Check everything:

```bash
./scripts/dev-up.sh
./scripts/verify-backend-e2e.sh
```

## 6. Main URLs

| Page | Path |
|------|------|
| Interview | `/interview` |
| Workflow builder | `/builder` |
| Saved workflows | `/workflows` |
| Agent library | `/agents` |
| Dashboard | `/` *(needs mock API)* |

## 7. Catalog index (first time only)

If interview does not show catalog hints:

```bash
cd backend && source .venv/bin/activate
python scripts/create_index.py
python -m pipeline.run --source ./data/spec.json
```

## Common issues

- **Red banner “Cannot reach AFFINE API”** — backend not running or wrong port; run `./scripts/sync-dev-env.sh` and restart frontend.
- **Dashboard proxy errors (3001)** — start `./scripts/start-mock-api.sh` or ignore if you only use Launchpad.
- **Sessions not shared with team** — ensure `DATA_STORAGE_BACKEND=blob` and Azure storage credentials in `backend/.env`.

## More documentation

- [WHAT_TO_SHARE.md](./WHAT_TO_SHARE.md) — credentials checklist for leads
- [BACKEND_E2E_SETUP.md](./BACKEND_E2E_SETUP.md) — deeper backend checks
- [CONNECT_AZURE_BACKEND.md](./CONNECT_AZURE_BACKEND.md) — deployed API

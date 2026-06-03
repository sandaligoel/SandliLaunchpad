# How to Run Agentic LaunchPad (AFFINE)

## Prerequisites

- **Python 3.11+**
- **Node.js 20+** and npm
- **Git**
- `backend/.env` with Azure keys (copy from `backend/.env.example`)

On Windows, bash scripts in `scripts/` may fail without WSL. Use the PowerShell steps below instead.

---

## One-time setup

### 1. Clone and enter the repo

```powershell
git clone https://github.com/AAIN1682/Agentic-LaunchPad.git
cd Agentic-LaunchPad
```

### 2. Backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your Azure OpenAI, Search, and Storage credentials
cd ..
```

### 3. Frontend

```powershell
cd frontend
npm install
cd ..
```

### 4. Port config (Windows — replaces `sync-dev-env.sh`)

Create `config/runtime-ports.json`:

```json
{
  "host": "127.0.0.1",
  "affineApiPort": 8003,
  "uiPort": 5173
}
```

Create `frontend/.env.local`:

```
AFFINE_API_TARGET=http://127.0.0.1:8003
VITE_AFFINE_API_TARGET=http://127.0.0.1:8003
VITE_AFFINE_API_BASE=
VITE_UI_PORT=5173
```

---

## Run every day (two terminals)

### Terminal 1 — Backend API

```powershell
cd Agentic-LaunchPad\backend
$env:PYTHONPATH="."
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload --host 127.0.0.1 --port 8003
```

Check: open http://127.0.0.1:8003/health — expect `"status":"ok"`.

### Terminal 2 — Frontend UI

```powershell
cd Agentic-LaunchPad\frontend
npx vite dev
```

> **Note:** `npm run dev` runs a bash `predev` script that fails on Windows without WSL. Use `npx vite dev` instead.

Vite prints the local URL (usually http://localhost:5173). If port 5173 is busy, it may use **5174** — use whatever URL Vite shows.

---

## App URLs

| Page | URL |
|------|-----|
| Agent interview (main) | http://localhost:5173/interview |
| Workflow builder | http://localhost:5173/builder |
| Saved workflows | http://localhost:5173/workflows |
| Agent library | http://localhost:5173/agents |
| Dashboard | http://localhost:5173/dashboard |

Replace `5173` with the port Vite reports if different.

---

## macOS / Linux (bash)

```bash
./scripts/sync-dev-env.sh
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
cp .env.example .env
cd ../frontend && npm install

# Daily — 2 terminals
./scripts/start-backend.sh
cd frontend && npm run dev
```

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `bash` / WSL error on `npm run dev` | Use `npx vite dev` and create `.env.local` manually (see above) |
| “Cannot reach AFFINE API” in UI | Start backend; confirm http://127.0.0.1:8003/health works |
| Wrong proxy port | Ensure `config/runtime-ports.json` matches backend port; restart Vite |
| Missing `.env` | `copy backend\.env.example backend\.env` and add credentials |

More detail: [docs/EMPLOYEE_SETUP.md](docs/EMPLOYEE_SETUP.md)

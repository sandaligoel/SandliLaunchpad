# Local dev ports

**Defaults:** [dev-ports.json](dev-ports.json) (API **8003**, UI **5173**)

**Active ports:** `runtime-ports.json` (gitignored). If a default port is busy, the next free port is chosen and written here so backend and frontend stay aligned.

```bash
./scripts/allocate-ports.sh   # refresh runtime-ports.json
./scripts/sync-dev-env.sh     # writes frontend/.env.local
./scripts/doctor.sh           # verify API + UI
```

Start order:

```bash
./scripts/start-backend.sh
cd frontend && npm run dev
```

Vite proxies `/api` and `/health` to the API port in `runtime-ports.json` (not `.env.development`).

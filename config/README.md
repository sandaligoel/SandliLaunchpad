# Local dev ports

**Single source of truth:** `dev-ports.json`

| Service | Port |
|---------|------|
| Backend API (`backend/`) | **8003** |
| Mock API (`mock-api/`) | **3001** |
| Frontend (`frontend/`) | **5173** |

```bash
./scripts/sync-dev-env.sh   # writes frontend/.env.local
```

Start commands:

```bash
./scripts/start-backend.sh
./scripts/start-mock-api.sh
cd frontend && npm run dev
```

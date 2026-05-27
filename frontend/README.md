# Frontend — Agent Launchpad UI

React + Vite app (TanStack Router).

## Run

```bash
npm install
cd .. && ./scripts/sync-dev-env.sh
npm run dev
```

Open http://localhost:5173

Proxies `/api/sessions`, `/health`, `/api/launchpad` → backend (8003).  
Other `/api/*` → mock-api (3001) when running.

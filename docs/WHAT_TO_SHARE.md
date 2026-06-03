# What to share with a new employee

Use this checklist when onboarding someone to AFFINE. **Do not commit secrets to Git.**

## 1. Repository access

- Git clone URL (GitHub / Azure DevOps)
- Branch to use (e.g. `main` or `dev`)
- Link to [docs/EMPLOYEE_SETUP.md](./EMPLOYEE_SETUP.md)

## 2. Azure credentials (send securely — 1Password, Azure Key Vault, or private channel)

They need the same values you use in `backend/.env`:

| Variable | Purpose |
|----------|---------|
| `AZURE_OPENAI_ENDPOINT` | Chat + embeddings |
| `AZURE_OPENAI_API_KEY` | |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | e.g. `gpt-4.1` |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | e.g. `text-embedding-3-small` |
| `AZURE_OPENAI_VIDEO_DEPLOYMENT` | Optional — Sora deployment for **Image to Video** studio (e.g. `sora-2`) |
| `AZURE_SEARCH_ENDPOINT` | Agent catalog search |
| `AZURE_SEARCH_API_KEY` | |
| `AZURE_SEARCH_INDEX_NAME` | e.g. `agentic-launchpad` |
| `AZURE_STORAGE_ACCOUNT_NAME` | Session + workflow persistence |
| `AZURE_STORAGE_CONTAINER_NAME` | e.g. `agentic-launchpad` |
| `AZURE_STORAGE_CONNECTION_STRING` | Full connection string (quoted in `.env`) |

Recommended storage settings:

```env
DATA_STORAGE_BACKEND=blob
```

So interviews and workflow canvases are shared via Blob, not only local disk.

## 3. Optional: deployed API URL

If they should hit a shared cloud API instead of local uvicorn:

```env
# frontend/.env.local
AFFINE_API_TARGET=https://<your-container-app-host>
```

Restart `npm run dev` after changing.

## 4. What is **not** shared via git

| Item | Location |
|------|----------|
| Secrets | `backend/.env`, `frontend/.env.local` |
| Local session files | `backend/data/sessions/` |
| Python venv | `backend/.venv/` |
| node_modules | `frontend/node_modules/` |

All of the above are in `.gitignore`.

## 5. Fixed local ports (no per-developer config)

Share [config/dev-ports.json](../config/dev-ports.json):

- Backend **8003** (or next free port in `runtime-ports.json`)
- Frontend **5173**

Run once after clone:

```bash
./scripts/sync-dev-env.sh
```

## 6. Quick verification commands

```bash
./scripts/dev-up.sh
./scripts/verify-backend-e2e.sh
```

## 7. Support contacts

Add your team lead / Slack channel / email here before sending this doc to new hires.

# Backend ↔ UI connectivity

## Local (works now — no Azure deploy permissions needed)

You need **two terminals** (plus mock API if using full AgentForge UI).

### Terminal 1 — AFFINE API

```bash
./scripts/start-affine-api.sh
```

Check: http://127.0.0.1:8003/health → `{"status":"ok",...}`

### Terminal 2 — AgentForge UI

```bash
cd frontend
npm run dev
```

`frontend/.env.local` should contain:

```env
AFFINE_API_TARGET=http://127.0.0.1:8003
VITE_AFFINE_API_BASE=
```

Vite proxies:

| Browser path | Goes to |
|--------------|---------|
| `/health` | AFFINE API |
| `/api/sessions/*` | AFFINE API |
| Other `/api/*` | Mock API (port 3001) |

### Terminal 3 (optional) — Mock API

```bash
./scripts/start-mock-api.sh
```

Open http://localhost:5173 → **Agent Launchpad** / interview.

---

## Azure deploy (blocked until RBAC is granted)

`az login` works on subscription **Affine-Main**, but creating resources fails with:

`AuthorizationFailed` … `resourcegroups/write` / `registries/write`

### Ask your Azure admin

On subscription `790df8b9-eea1-44f4-8545-086b629260e1`, grant **one** of:

- **Contributor** on resource group **`Affine`** (recommended), or
- Roles: `Contributor` + ability to create **Container Registry** and **Container Apps** in that RG

Or: admin deploys the image and gives you the **HTTPS URL** of the running API.

### After you have deploy rights

Use existing RG **`Affine`** (not a new `affine-rg`):

```bash
cd backend
az acr create --resource-group Affine --name <unique-acr-name> --sku Basic
az acr build --registry <unique-acr-name> --image affine-agent-catalog:v1 .
# … Container App — see docs/AZURE_BACKEND.md
```

Set app env vars from `backend/.env` (OpenAI + Search keys). Add your UI origin to `CORS_ORIGINS`.

### Point production UI at Azure API

```env
VITE_AFFINE_API_BASE=https://<your-api-host>
```

Rebuild `frontend` and deploy the static app. No Vite proxy in production — the browser calls the API URL directly.

---

## Quick checks

| Check | Command / URL |
|-------|----------------|
| API up | `curl -s http://127.0.0.1:8003/health` |
| UI proxy | Interview page loads; Network tab shows `/api/sessions` → 200 |
| CORS (Azure only) | API `CORS_ORIGINS` includes exact UI origin |

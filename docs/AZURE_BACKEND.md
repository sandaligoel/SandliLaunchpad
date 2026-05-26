# Deploy AFFINE backend on Azure (container)

The backend is **`agent_catalog/`** — a FastAPI app that calls **Azure OpenAI** and **Azure AI Search**. Your container should listen on **port 8000** and expose **`GET /health`**.

---

## What you need in Azure (before deploy)

| Resource | Purpose |
|----------|---------|
| **Azure OpenAI** | Chat + embeddings (`AZURE_OPENAI_*`) |
| **Azure AI Search** | Agent catalog index (`AZURE_SEARCH_*`) |
| **Azure Container Registry (ACR)** | Store your image |
| **Azure Container Apps** *or* **App Service (Linux container)** | Run the API |

Search index (one-time, from your machine or a build job):

```bash
cd agent_catalog
python scripts/create_index.py
python -m pipeline.run --source ./data/spec.json
```

---

## Step 1 — Build and test the image locally

From repo root:

```bash
cd agent_catalog
docker build -t affine-agent-catalog:local .
docker run --rm -p 8000:8000 --env-file .env affine-agent-catalog:local
```

Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health) → `{"status":"ok",...}`

If you **already have** an image, skip build and use your tag in Step 2.

---

## Step 2 — Push image to Azure Container Registry

```bash
# Login (Azure CLI)
az login
az account set --subscription "<YOUR_SUBSCRIPTION_ID>"

# Create ACR (once) — pick a globally unique name
az acr create --resource-group affine-rg --name affineacr --sku Basic

# Build in ACR (no local Docker required)
az acr build --registry affineacr --image affine-agent-catalog:v1 .

# Or push an image you built locally
az acr login --name affineacr
docker tag affine-agent-catalog:local affineacr.azurecr.io/affine-agent-catalog:v1
docker push affineacr.azurecr.io/affine-agent-catalog:v1
```

---

## Step 3 — Deploy with Azure Container Apps (recommended)

### 3a. Environment + app

```bash
# Use an existing resource group you can write to (e.g. Affine). Skip if you lack Contributor on the subscription.
# az group create --name affine-rg --location eastus

az containerapp env create \
  --name affine-env \
  --resource-group affine-rg \
  --location eastus

az containerapp create \
  --name affine-api \
  --resource-group affine-rg \
  --environment affine-env \
  --image affineacr.azurecr.io/affine-agent-catalog:v1 \
  --registry-server affineacr.azurecr.io \
  --registry-identity system \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 3 \
  --cpu 1.0 --memory 2.0Gi
```

Enable ACR pull for the app (if using managed identity):

```bash
az acr update -n affineacr --admin-enabled true
# Or assign AcrPull role to the container app's identity
```

### 3b. Environment variables (secrets)

Set these in the Container App (Portal → **Containers** → **Environment variables**, or CLI):

| Variable | Example |
|----------|---------|
| `AZURE_OPENAI_ENDPOINT` | `https://<resource>.openai.azure.com/` |
| `AZURE_OPENAI_API_KEY` | Key or use Key Vault reference |
| `AZURE_OPENAI_API_VERSION` | `2025-01-01-preview` |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | `gpt-4.1` |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | `text-embedding-3-small` |
| `AZURE_SEARCH_ENDPOINT` | `https://<search>.search.windows.net` |
| `AZURE_SEARCH_API_KEY` | Search admin/query key |
| `AZURE_SEARCH_INDEX_NAME` | `agentic-launchpad` |
| `PDF_PATH` | `./data/spec.json` |
| `CORS_ORIGINS` | `https://<your-ui-domain>` |
| `LOG_LEVEL` | `INFO` |

CLI example (replace values; use **secrets** for keys in production):

```bash
az containerapp update \
  --name affine-api \
  --resource-group affine-rg \
  --set-env-vars \
    AZURE_OPENAI_ENDPOINT="https://YOUR.openai.azure.com/" \
    AZURE_OPENAI_API_VERSION="2025-01-01-preview" \
    AZURE_OPENAI_CHAT_DEPLOYMENT="gpt-4.1" \
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-3-small" \
    AZURE_SEARCH_ENDPOINT="https://YOUR.search.windows.net" \
    AZURE_SEARCH_INDEX_NAME="agentic-launchpad" \
    PDF_PATH="./data/spec.json" \
    CORS_ORIGINS="https://your-frontend.azurewebsites.net"
```

Add API keys as **secrets** (Portal: **Security** → **Secrets**, then reference as `secretref:openai-key`).

### 3c. Persist interview sessions (optional but recommended)

Sessions are written under `data/sessions/` inside the container. Without storage, they are lost on restart.

1. Create a **Storage account** + **File share**.
2. In Container Apps → **Volumes** → mount the share at `/app/data/sessions`.

### 3d. Get the public URL

```bash
az containerapp show --name affine-api --resource-group affine-rg \
  --query properties.configuration.ingress.fqdn -o tsv
```

Test: `https://<fqdn>/health`

---

## Alternative — App Service for Linux containers

```bash
az appservice plan create --name affine-plan --resource-group affine-rg --is-linux --sku B1
az webapp create --resource-group affine-rg --plan affine-plan --name affine-api-app \
  --deployment-container-image-name affineacr.azurecr.io/affine-agent-catalog:v1

az webapp config appsettings set --resource-group affine-rg --name affine-api-app \
  --settings \
    WEBSITES_PORT=8000 \
    AZURE_OPENAI_ENDPOINT="..." \
    # ... same vars as above

az webapp config container set --resource-group affine-rg --name affine-api-app \
  --docker-custom-image-name affineacr.azurecr.io/affine-agent-catalog:v1 \
  --docker-registry-server-url https://affineacr.azurecr.io
```

Health check path: `/health`

---

## Step 4 — Point the frontend at Azure

In **`agentforge-ui`** production env:

```bash
VITE_AFFINE_API_BASE=https://<your-container-app-fqdn>
```

Rebuild and deploy the UI. In dev, `AFFINE_API_TARGET` in `.env.local` still proxies to local uvicorn.

---

## Step 5 — Security checklist

- Do **not** commit `.env` or keys to git.
- Prefer **Azure Key Vault** + Container Apps secret references over plain env for keys.
- Restrict **CORS** to your real UI origin only.
- Use **managed identity** for ACR pull where possible.
- Ensure Search and OpenAI are in regions allowed by your org.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Container exits on start | Missing env var — check logs; `Settings.validate()` requires all `AZURE_*` vars |
| 502 / unhealthy | Confirm port **8000** and `/health` |
| CORS errors from UI | Add UI URL to `CORS_ORIGINS` |
| Empty catalog in interview | Run `create_index.py` + `pipeline.run` against the **same** Search index name |
| Sessions disappear after restart | Mount Azure Files at `data/sessions` |

---

## Quick reference — API surface

- `GET /health`
- `POST /api/sessions` — start interview
- `GET /api/sessions/{id}`
- `POST /api/sessions/{id}/turn`
- `POST /api/sessions/{id}/architecture` — generate plan

Router prefix is `/api` (see `agent_catalog/api/routes.py`).

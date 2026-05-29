# Step-by-step: Store & run AFFINE backend in your Azure container

This guide assumes:

- Backend code: `backend/` (FastAPI)
- You already have **Azure** access (`az login` → subscription **Affine-Main**)
- You have (or will get) an **Azure Container Registry (ACR)** and a place to **run** the container (Container Apps, App Service, or Container Instances)

Your machine does **not** need Docker if you use **`az acr build`** (build runs in Azure).

---

## Overview (5 phases)

| Phase | What you do | Result |
|-------|-------------|--------|
| **0** | Check access & gather names | Know your ACR name, resource group, region |
| **1** | Build the image **into** ACR | Image stored in Azure: `…azurecr.io/affine-agent-catalog:v1` |
| **2** | Create or pick a **runtime** (Container App / App Service) | A URL like `https://….azurecontainerapps.io` |
| **3** | Set **environment variables** (from `.env`) | API can call OpenAI + Search |
| **4** | Connect **AgentForge UI** | Interview talks to Azure API |
| **5** | Verify & troubleshoot | `/health` returns OK |

---

## Phase 0 — Prerequisites

### 0.1 Tools on your Mac

```bash
cd /Users/gurucharanm/projects/AFFINE/backend
source .venv/bin/activate
az login
az account show --output table
```

You should see **Affine-Main** (subscription id `790df8b9-eea1-44f4-8545-086b629260e1`).

### 0.2 Fill `backend/.env`

Copy from `.env.example` if needed. You need **real** values for:

- `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_API_VERSION`
- `AZURE_OPENAI_CHAT_DEPLOYMENT`, `AZURE_OPENAI_EMBEDDING_DEPLOYMENT`
- `AZURE_SEARCH_ENDPOINT`, `AZURE_SEARCH_API_KEY`, `AZURE_SEARCH_INDEX_NAME`
- `PDF_PATH=./data/spec.json`

### 0.3 Catalog index (one-time, from your laptop)

Still run against the **same** Search service as in `.env`:

```bash
cd /Users/gurucharanm/projects/AFFINE/backend
source .venv/bin/activate
python scripts/create_index.py
python -m pipeline.run --source ./data/spec.json
```

### 0.4 Find your existing container resources in Azure Portal

1. Open https://portal.azure.com  
2. Search **Container registries** — note:
   - **Registry name** (e.g. `mycompanyacr`)
   - **Login server** (e.g. `mycompanyacr.azurecr.io`)
   - **Resource group** (e.g. `Affine` or `AICoE_Intern`)
3. Search **Container Apps** or **App Services** or **Container instances** — note if something already exists for this project.

**CLI — list what you can see:**

```bash
az acr list --output table
az containerapp list --output table
az webapp list --output table
```

If you see registries under **AICoE_Intern** but get **AuthorizationFailed** when pushing, ask an admin for **AcrPush** on that registry (or use a registry in **Affine** RG that they create for you).

---

## Phase 1 — Store the image in Azure Container Registry (ACR)

Goal: image name  
`<loginServer>/affine-agent-catalog:v1`  
example: `myregistry.azurecr.io/affine-agent-catalog:v1`

### Step 1.1 — Choose registry name and resource group

Pick from Portal **or** ask admin to create:

```bash
# Only if you have permission (you may get AuthorizationFailed):
az acr create --resource-group Affine --name affineagentcatalog --sku Basic
```

If admin already gave you a registry, set:

```bash
export ACR_NAME="<your-registry-name>"          # Portal → Container registry → Name
export ACR_RG="<resource-group-name>"           # e.g. Affine or AICoE_Intern
export IMAGE_NAME="affine-agent-catalog"
export IMAGE_TAG="v1"
```

Get login server:

```bash
az acr show --name $ACR_NAME --resource-group $ACR_RG --query loginServer -o tsv
# Example output: affineagentcatalog.azurecr.io
export ACR_LOGIN_SERVER="<paste-login-server>"
```

### Step 1.2 — Build in the cloud (no Docker on Mac)

From the folder that contains the `Dockerfile`:

```bash
cd /Users/gurucharanm/projects/AFFINE/backend

az acr build \
  --registry $ACR_NAME \
  --resource-group $ACR_RG \
  --image ${IMAGE_NAME}:${IMAGE_TAG} \
  .
```

Wait until it says **Run ID** succeeded (5–15 minutes).

**If you get AuthorizationFailed:** you need **Contributor** or **AcrBuild** on that registry. Send admin:

> Please grant **AcrPush** and **AcrBuild** on ACR `<ACR_NAME>` in RG `<ACR_RG>` to `i-gurucharan.m@affine.ai`, or run the `az acr build` command above for branch AFFINE `backend`.

### Step 1.3 — Confirm image is stored

```bash
az acr repository list --name $ACR_NAME --output table
az acr repository show-tags --name $ACR_NAME --repository $IMAGE_NAME --output table
```

You should see tag `v1`.

Full image reference for deploy:

```bash
export FULL_IMAGE="${ACR_LOGIN_SERVER}/${IMAGE_NAME}:${IMAGE_TAG}"
echo $FULL_IMAGE
```

---

## Phase 2 — Run the container in Azure

Pick **one** path: **Container Apps** (recommended) or **Web App for Containers**.

### Path A — Azure Container Apps (recommended)

#### Step 2A.1 — Container Apps environment (once per team/region)

```bash
export LOCATION="eastus"
export CAE_NAME="affine-launchpad-env"
export CA_RG="Affine"   # or a RG where you can create resources

az containerapp env create \
  --name $CAE_NAME \
  --resource-group $CA_RG \
  --location $LOCATION
```

If this fails with **AuthorizationFailed**, admin must create the environment or grant you **Contributor** on `$CA_RG`.

#### Step 2A.2 — Enable ACR access for Container Apps

**Option 1 — Admin credentials (quick test):**

```bash
az acr update --name $ACR_NAME --admin-enabled true
ACR_USER=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASS=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)
```

**Option 2 — Managed identity (production):** ask admin to assign **AcrPull** to the Container App identity.

#### Step 2A.3 — Create the Container App

```bash
export APP_NAME="affine-agent-api"

az containerapp create \
  --name $APP_NAME \
  --resource-group $CA_RG \
  --environment $CAE_NAME \
  --image $FULL_IMAGE \
  --registry-server $ACR_LOGIN_SERVER \
  --registry-username $ACR_USER \
  --registry-password $ACR_PASS \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 \
  --max-replicas 2 \
  --cpu 1.0 \
  --memory 2.0Gi
```

#### Step 2A.4 — Get public URL

```bash
az containerapp show --name $APP_NAME --resource-group $CA_RG \
  --query properties.configuration.ingress.fqdn -o tsv
```

Example: `affine-agent-api.nicegrass-12345678.eastus.azurecontainerapps.io`  

Health URL: `https://<fqdn>/health`

---

### Path B — App Service (Linux container)

Use if your team already uses **App Service** instead of Container Apps.

```bash
export PLAN_NAME="affine-api-plan"
export WEBAPP_NAME="affine-agent-api"   # globally unique

az appservice plan create --name $PLAN_NAME --resource-group $CA_RG --is-linux --sku B1
az webapp create --resource-group $CA_RG --plan $PLAN_NAME --name $WEBAPP_NAME

az webapp config container set \
  --name $WEBAPP_NAME \
  --resource-group $CA_RG \
  --docker-custom-image-name $FULL_IMAGE \
  --docker-registry-server-url https://$ACR_LOGIN_SERVER \
  --docker-registry-server-user $ACR_USER \
  --docker-registry-server-password $ACR_PASS

az webapp config appsettings set --resource-group $CA_RG --name $WEBAPP_NAME \
  --settings WEBSITES_PORT=8000
```

URL: `https://<WEBAPP_NAME>.azurewebsites.net/health`

---

### Path C — You already have a container in Azure

If admin already created a **Container App** or **Web App**:

1. Portal → open that resource → **Containers** / **Deployment Center**
2. Set image to: `$FULL_IMAGE` (from Phase 1)
3. Set port **8000**
4. Save → **Restart**
5. Continue to **Phase 3** (env vars) on the same resource

---

## Phase 3 — Environment variables (critical)

The container needs the same secrets as local `.env`. **Do not** bake `.env` into the image.

### Step 3.1 — Prepare values

From `backend/.env`, you will set each variable on the running app.

Also set:

```text
PORT=8000
PDF_PATH=./data/spec.json
LOG_LEVEL=INFO
CORS_ORIGINS=https://<your-ui-host>,http://localhost:5173
```

Use your real UI URL in production; keep `localhost` only for testing.

### Step 3.2 — Container Apps (CLI)

```bash
az containerapp update \
  --name $APP_NAME \
  --resource-group $CA_RG \
  --set-env-vars \
    PORT=8000 \
    PDF_PATH=./data/spec.json \
    LOG_LEVEL=INFO \
    AZURE_OPENAI_ENDPOINT="<from-.env>" \
    AZURE_OPENAI_API_VERSION="<from-.env>" \
    AZURE_OPENAI_CHAT_DEPLOYMENT="<from-.env>" \
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT="<from-.env>" \
    AZURE_SEARCH_ENDPOINT="<from-.env>" \
    AZURE_SEARCH_INDEX_NAME="<from-.env>" \
    CORS_ORIGINS="https://<your-ui>,http://localhost:5173"
```

**Secrets (API keys)** — use Portal **Secrets** + reference them, or:

```bash
az containerapp secret set --name $APP_NAME --resource-group $CA_RG \
  --secrets openai-key="<AZURE_OPENAI_API_KEY>" search-key="<AZURE_SEARCH_API_KEY>"

az containerapp update --name $APP_NAME --resource-group $CA_RG \
  --set-env-vars \
    AZURE_OPENAI_API_KEY=secretref:openai-key \
    AZURE_SEARCH_API_KEY=secretref:search-key
```

### Step 3.2b — App Service

```bash
az webapp config appsettings set --resource-group $CA_RG --name $WEBAPP_NAME \
  --settings \
    WEBSITES_PORT=8000 \
    AZURE_OPENAI_ENDPOINT="..." \
    AZURE_OPENAI_API_KEY="..." \
    # ... all other vars from .env
```

### Step 3.3 — Restart

```bash
# Container Apps
az containerapp revision restart --name $APP_NAME --resource-group $CA_RG

# App Service
az webapp restart --name $WEBAPP_NAME --resource-group $CA_RG
```

---

## Phase 4 — Connect AgentForge UI

### Step 4.1 — Production API URL

```bash
export API_URL="https://<your-fqdn-from-phase-2>"
curl -s "$API_URL/health"
```

Expect: `{"status":"ok",...}`

### Step 4.2 — UI environment

In `frontend/.env.local` (dev with proxy) keep:

```env
AFFINE_API_TARGET=http://127.0.0.1:8003
VITE_AFFINE_API_BASE=
```

For **production build** (UI hosted on Azure / Cloudflare / static host):

```env
VITE_AFFINE_API_BASE=https://<your-fqdn-from-phase-2>
```

Rebuild UI: `cd frontend && npm run build`

### Step 4.3 — CORS

If the browser shows CORS errors, add your **exact** UI origin to `CORS_ORIGINS` on the API (including `https://`, no trailing slash) and restart the app.

---

## Phase 5 — Verify end-to-end

| # | Check | Command / action |
|---|--------|------------------|
| 1 | Health | `curl https://<fqdn>/health` |
| 2 | Start session | `curl -X POST https://<fqdn>/api/sessions -H "Content-Type: application/json" -d '{"problem_statement":"We need a loan review agent for small business applications with human approval."}'` |
| 3 | UI | Open interview in browser; Network tab → `/api/sessions` → 200 |
| 4 | Logs | Portal → Container App → **Log stream** or **Monitoring** |

---

## Phase 6 — Session storage (optional)

Interview JSON is saved under `data/sessions/` **inside** the container. Restarts lose data unless you mount storage.

**Container Apps:** add Azure Files volume mounted at `/app/data/sessions` (Portal → **Volumes**).

---

## Permission errors (what you saw before)

| Error | Meaning | What to ask admin |
|-------|---------|-------------------|
| `resourcegroups/write` | Cannot create RG | Use existing RG **Affine** or get Contributor |
| `registries/write` | Cannot create ACR | Use existing ACR + **AcrPush** / **AcrBuild** |
| `containerapps/write` | Cannot create app | Admin creates app; you get **Contributor** on it |

**Minimum roles (typical):**

- On ACR: **AcrPush**, **AcrBuild**
- On Container App / RG: **Contributor** (or Website Contributor for App Service)

---

## Quick command cheat sheet (fill in your names)

```bash
# 1. Variables
export ACR_NAME="YOUR_ACR"
export ACR_RG="YOUR_RG"
export ACR_LOGIN_SERVER="$(az acr show -n $ACR_NAME -g $ACR_RG --query loginServer -o tsv)"
export FULL_IMAGE="${ACR_LOGIN_SERVER}/affine-agent-catalog:v1"

# 2. Build & store image
cd /Users/gurucharanm/projects/AFFINE/backend
az acr build --registry $ACR_NAME --resource-group $ACR_RG --image affine-agent-catalog:v1 .

# 3. Deploy (after env + app exist)
# ... see Phase 2 ...

# 4. Test
curl -s "https://YOUR_FQDN/health"
```

---

## Portal-only alternative (no CLI deploy)

1. **Container registry** → **Repositories** → confirm `affine-agent-catalog:v1` after build.
2. **Container Apps** → **Create** → select image from ACR, port **8000**, ingress **Enabled**.
3. **Application** → **Environment variables** → paste from `.env`.
4. Copy **Application Url** → use as `VITE_AFFINE_API_BASE`.

---

## Related docs

- Shorter reference: [AZURE_BACKEND.md](./AZURE_BACKEND.md)
- Local UI + API: [EMPLOYEE_SETUP.md](./EMPLOYEE_SETUP.md)

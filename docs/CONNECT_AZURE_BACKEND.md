# Connect UI to Azure backend container

Your AFFINE API image is already stored in Azure:

```text
749b44415c9d4d2b9052d2b2d61f491c.azurecr.io/affine-agent-catalog:v1
```

Registry: **749b44415c9d4d2b9052d2b2d61f491c** (resource group **AICoE_Intern**).

You still need a **running URL** (Container App or App Service). Building the image ≠ running it.

---

## Part 1 — Get a public API URL (you or admin)

### If you can create Container Apps

Ask admin for **Contributor** on resource group **Affine**, then:

```bash
export ACR_NAME=749b44415c9d4d2b9052d2b2d61f491c
export ACR_RG=AICoE_Intern
export FULL_IMAGE="${ACR_NAME}.azurecr.io/affine-agent-catalog:v1"
export CA_RG=Affine
export CAE_NAME=affine-launchpad-env
export APP_NAME=affine-agent-api

az containerapp env create --name $CAE_NAME --resource-group $CA_RG --location eastus

az acr update --name $ACR_NAME --admin-enabled true
ACR_USER=$(az acr credential show --name $ACR_NAME --query username -o tsv)
ACR_PASS=$(az acr credential show --name $ACR_NAME --query "passwords[0].value" -o tsv)

az containerapp create \
  --name $APP_NAME \
  --resource-group $CA_RG \
  --environment $CAE_NAME \
  --image $FULL_IMAGE \
  --registry-server ${ACR_NAME}.azurecr.io \
  --registry-username $ACR_USER \
  --registry-password $ACR_PASS \
  --target-port 8000 \
  --ingress external \
  --min-replicas 1 --max-replicas 2

az containerapp show --name $APP_NAME --resource-group $CA_RG \
  --query properties.configuration.ingress.fqdn -o tsv
```

### If you cannot (AuthorizationFailed)

Send admin this **exact image** and port **8000**:

```text
749b44415c9d4d2b9052d2b2d61f491c.azurecr.io/affine-agent-catalog:v1
```

Ask for the HTTPS URL, e.g. `https://something.azurecontainerapps.io`.

---

## Part 2 — Configure the running container (env vars)

On the Container App / Web App, set environment variables from `backend/.env`:

| Variable | Required |
|----------|----------|
| `AZURE_OPENAI_ENDPOINT` | Yes |
| `AZURE_OPENAI_API_KEY` | Yes (secret) |
| `AZURE_OPENAI_API_VERSION` | Yes |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Yes |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Yes |
| `AZURE_SEARCH_ENDPOINT` | Yes |
| `AZURE_SEARCH_API_KEY` | Yes (secret) |
| `AZURE_SEARCH_INDEX_NAME` | Yes |
| `PDF_PATH` | `./data/spec.json` |
| `PORT` | `8000` |
| `CORS_ORIGINS` | `http://localhost:5173` + your UI URL |

Restart the app after saving.

---

## Part 3 — Connect AgentForge UI (local dev)

**Step 1** — Test API from terminal:

```bash
chmod +x scripts/test-azure-api.sh
./scripts/test-azure-api.sh https://YOUR-API-HOST.azurecontainerapps.io
```

**Step 2** — Edit `frontend/.env.local`:

```env
AFFINE_API_TARGET=https://YOUR-API-HOST.azurecontainerapps.io
VITE_AFFINE_API_BASE=
VITE_MOCK_API_TARGET=http://127.0.0.1:3001
```

Use **https**, no trailing slash. Empty `VITE_AFFINE_API_BASE` lets Vite **proxy** Azure (avoids CORS during dev).

**Step 3** — Restart UI:

```bash
cd frontend
npm run dev
```

**Step 4** — Open http://localhost:5173/interview — health check should pass.

---

## Part 4 — Production UI

When the UI is hosted on a real domain:

```env
VITE_AFFINE_API_BASE=https://YOUR-API-HOST.azurecontainerapps.io
```

Add that same origin to API `CORS_ORIGINS`, rebuild UI, deploy.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Interview says API offline | Wrong URL in `AFFINE_API_TARGET`; restart `npm run dev` |
| CORS error in browser | Use proxy mode (`VITE_AFFINE_API_BASE` empty) or add UI URL to `CORS_ORIGINS` |
| 502 / unhealthy container | Env vars missing on Container App; check Log stream |
| 401 / OpenAI errors | Keys/deployments wrong in container env |

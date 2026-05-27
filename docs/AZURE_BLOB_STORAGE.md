# Save Launchpad data to Azure Blob (`affineblog` / `agentic-launchpad`)

Interview sessions and workflow builder snapshots can be stored in your team container instead of only on the API machine or in the browser.

## Blob layout

Inside container **`agentic-launchpad`** on storage account **`affineblog`**:

```text
launchpad/
  sessions/<session-id>.json     # interview spec, messages, architecture plan
  workflows/<session-id>.json    # builder canvas + plan
  workflows/_index.json          # workflow list for the Workflows page
```

## Configure `backend/.env`

**Required for localhost to load/save previous work in Azure** (keep existing OpenAI / Search vars):

```env
DATA_STORAGE_BACKEND=blob
AZURE_STORAGE_ACCOUNT_NAME=affineblog
AZURE_STORAGE_CONTAINER_NAME=agentic-launchpad

# Use ONE of these auth options:
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=affineblog;...
# or
AZURE_STORAGE_ACCOUNT_KEY=<key from Azure Portal → Storage account → Access keys>
# or omit both and use `az login` (DefaultAzureCredential) if your user has Storage Blob Data Contributor
```

On startup, `./scripts/start-affine-api.sh` prints whether Blob is reachable and how many sessions exist.

The UI **Agent Launchpad** page lists **Continue a previous interview** from `GET /api/sessions` (reads the container). Opening **Workflow Builder** or **Workflows** loads canvas data from `launchpad/workflows/` in the same container.

Install the new dependency and restart the API:

```bash
cd backend
.venv/bin/pip install azure-storage-blob
./scripts/start-affine-api.sh   # or your usual uvicorn command
```

On startup you should see a log line like: `Data storage: Azure Blob account=affineblog container=agentic-launchpad prefix=launchpad`.

## Migrate existing local sessions

```bash
cd backend
export DATA_STORAGE_BACKEND=blob
export AZURE_STORAGE_ACCOUNT_NAME=affineblog
export AZURE_STORAGE_CONTAINER_NAME=agentic-launchpad
# set connection string or account key
PYTHONPATH=. .venv/bin/python ../scripts/migrate-local-to-blob.py
```

Workflows that only exist in **browser localStorage** are uploaded the next time you open the builder (auto-save syncs to `PUT /api/sessions/{id}/builder`).

## Portal link

[affineblog → agentic-launchpad](https://portal.azure.com/#view/Microsoft_Azure_Storage/ContainerMenuBlade/~/overview/storageAccountId/%2Fsubscriptions%2F790df8b9-eea1-44f4-8545-086b629260e1%2FresourceGroups%2FAICoE_Intern%2Fproviders%2FMicrosoft.Storage%2FstorageAccounts%2Faffineblog/path/agentic-launchpad)

## Local dev without Azure

Leave `DATA_STORAGE_BACKEND` unset or set `DATA_STORAGE_BACKEND=local`. Data is mirrored under `backend/data/blob_mirror/` and legacy `data/sessions/` still works.

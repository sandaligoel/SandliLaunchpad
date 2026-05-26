# AFFINE — Agent Launchpad

Affine Agent Catalog (Phase 1) and smart requirements interview (Phase 2).

## Projects

| Directory | Phase | Description |
|-----------|-------|-------------|
| [agent_catalog/](agent_catalog/) | 1 & 2 | Catalog JSON ingest, Azure AI Search index, FastAPI interview API |
| [agentforge-ui/](agentforge-ui/) | 2–3 | **AgentForge UI** (Dashboard, Builder, Workflows, Agent Library) |
| [agentforge-mock-api/](agentforge-mock-api/) | — | Mock API for AgentForge screens (port 3001) |
| [launchpad-ui/](launchpad-ui/) | 2 | Legacy minimal React UI |

## Quick start

**Step-by-step:** [START.md](START.md) (three terminals for AgentForge UI + mock API + AFFINE).

```bash
# AFFINE API
cd agent_catalog && source .venv/bin/activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8003

# Mock API (workflows, agents, dashboard)
./scripts/start-agentforge-mock.sh

# AgentForge UI
cd agentforge-ui && npm install && npm run dev
```

Open http://localhost:5173. Legacy UI: `launchpad-ui/`. Integration plan: [docs/INTEGRATION_AGENTIC_LAUNCHPAD.md](docs/INTEGRATION_AGENTIC_LAUNCHPAD.md).

See [agent_catalog/README.md](agent_catalog/README.md) (catalog index) and [agent_catalog/README_PHASE2.md](agent_catalog/README_PHASE2.md) (interview).

## Phase 3

Architecture planning API — see [agent_catalog/README_PHASE3.md](agent_catalog/README_PHASE3.md).

```bash
curl -X POST http://127.0.0.1:8001/api/sessions/{session_id}/architecture
```

**Canvas UI:** `cd launchpad-ui && npm run dev` → http://localhost:5173 (Architecture tab after interview).

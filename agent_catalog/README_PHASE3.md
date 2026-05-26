# Phase 3 — Architecture Planning API

Generates a **directed graph** and **reuse decisions** from a completed Phase 2 interview, grounded in the **agent catalog** (Azure AI Search).

## Prerequisites

- Phase 2 session with `spec.status` of **`sufficient`** or **`ready`**
- Catalog indexed (`python -m pipeline.run --source ./data/spec.json`)

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/sessions/{id}/architecture` | Generate plan (cached on session) |
| `GET` | `/api/sessions/{id}/architecture` | Return cached plan |
| `POST` | `?force=true` | Regenerate even if cached |

## Example

```bash
# After interview completes — note session id from UI or POST /api/sessions
curl -X POST http://127.0.0.1:8001/api/sessions/YOUR_SESSION_ID/architecture

# Pretty-print
curl -s -X POST http://127.0.0.1:8001/api/sessions/YOUR_SESSION_ID/architecture | python -m json.tool
```

## Response shape

```json
{
  "session_id": "...",
  "plan": {
    "graph": {
      "nodes": [
        { "id": "ingest", "label": "Document ingest", "type": "gateway", "agent_id": null }
      ],
      "edges": [
        { "from_id": "ingest", "to_id": "extract", "label": "raw text" }
      ]
    },
    "reuse_decisions": [
      {
        "node_id": "extract",
        "node_label": "Entity Extraction",
        "decision": "reuse",
        "agent_id": "entity-extraction-agent",
        "agent_name": "Entity Extraction Agent",
        "rationale": "...",
        "catalog_score": 0.92
      }
    ],
    "catalog_matches": [ ... ],
    "summary_markdown": "...",
    "open_questions": []
  }
}
```

## Node types

| type | Meaning |
|------|---------|
| `agent` | Reuse or adapt a catalog agent (`agent_id` when matched) |
| `custom` | Build new component |
| `gateway` | Routing, validation, API entry |
| `human` | Analyst approval / HITL |

## Canvas UI (launchpad-ui)

```bash
# Terminal 1 — API (match port in vite.config.ts proxy)
cd agent_catalog && uvicorn api.main:app --reload --host 127.0.0.1 --port 8002

# Terminal 2 — React UI
cd launchpad-ui && npm install && npm run dev
```

Open **http://localhost:5173**:

1. Complete the interview until status is **sufficient** or **ready**
2. Open the **Architecture** tab (right panel)
3. Click **Generate architecture** — React Flow canvas + reuse list

Node colors: **reuse** (green), **adapt** (blue), **build** (gray).

## Validation remediation

After generation, open the **Validation** tab. Automated checks include:

- Graph: orphans (off entry→exit path), disconnected subgraphs, dangling edges (unique ids per edge), duplicate node ids
- Catalog: empty matches, stale reuse decisions, missing decisions on gateway/human/agent/custom
- Spec overlap: latency, accuracy, deployment, data volume, HITL, integrations, use case
- Scope note: structural/consistency only — not full business proof

UI: filter **All / Fails / Warnings**, fix chips, **Approve architecture** when `can_approve` is true. Acknowledging a **fail** records review but **does not** unblock approval until a structural fix is applied.

**Refresh catalog search** re-queries Azure AI Search during remediation.

```http
POST /api/sessions/{id}/architecture/remediate
Content-Type: application/json

{
  "finding_id": "reuse_no_agent:a1",
  "option_id": "use_catalog_agent-xyz"
}
```

The server resolves the full action from the plan’s validation report.

```http
POST /api/sessions/{id}/architecture/validate
POST /api/sessions/{id}/architecture/approve
```

Re-validates without regenerating; approve requires `validation.can_approve`.

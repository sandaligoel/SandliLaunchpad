# AFFINE Agent Launchpad — Project handoff (for tweaks)

Use this document to explain the codebase to another assistant. Stack: **Python 3.9+ FastAPI**, **Azure OpenAI**, **Azure AI Search**, **React + Vite + React Flow**.

---

## What the product does

Affine **Agent Launchpad** helps a business user go from a vague automation problem to a **reviewable system architecture** with **catalog agent reuse** decisions.

| Phase | Goal | Output |
|-------|------|--------|
| **1 — Catalog** | Index existing Affine agents from `data/spec.json` | Azure AI Search index `agentic-launchpad` |
| **2 — Interview** | Structured Q&A → requirements + flow | `ArchitectureSpec` (14 fields), blueprint markdown, `graph_draft` |
| **3 — Plan** | Spec + catalog → architecture diagram | `ArchitecturePlan` (graph, reuse decisions, validation) |

**UI:** `launchpad-ui/` (React, port 5173) proxies API to backend (port **8003** in current `vite.config.ts`). Alternative: bundled static UI at `http://127.0.0.1:8003/ui/`.

---

## Repo layout

```
AFFINE/
├── backend/          # Backend + Phase 1 pipeline
│   ├── api/                # FastAPI routes, session_store, static /ui
│   ├── services/           # interview, planner, validator, remediation, LLM
│   ├── schemas/            # Pydantic models
│   ├── prompts/            # LLM system prompts (.txt)
│   ├── pipeline/           # spec.json → embeddings → search index
│   ├── data/
│   │   ├── spec.json       # Multi-project agent catalog source
│   │   └── sessions/       # Persisted interview sessions (*.json)
│   └── scripts/            # create_index, validate_catalog
├── launchpad-ui/           # React SPA
└── START.md                # How to run locally
```

---

## Runtime (local)

**Terminal 1 — API**
```bash
cd backend && source .venv/bin/activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8003
```

**Terminal 2 — UI**
```bash
cd launchpad-ui && npm run dev
```

**Config:** `backend/.env` — Azure OpenAI + Azure AI Search keys, `PDF_PATH=./data/spec.json`.

**Sessions:** Saved to `data/sessions/{uuid}.json` on every save (survives API reload).

**Ports must match:** `launchpad-ui/vite.config.ts` proxy target = API port.

---

## End-to-end user flow

1. User enters **problem statement** → `POST /api/sessions`
2. **Clarifying phase** (new): LLM asks exactly **3** problem-specific questions (`prompts/clarifying_questions.txt`). No agents/architecture yet. Answers stored in `session.clarifying_answers`.
3. **Spec interview**: One question at a time with **chips**; fills 14 fields in `ArchitectureSpec`. Catalog hints shown after clarifying. Status: `draft` → `sufficient` → `ready`.
4. When **ready**: synthesis produces `architecture_blueprint` + `graph_draft`.
5. User opens **Architecture** tab → `POST /api/sessions/{id}/architecture` → `ArchitecturePlan`.
6. **Validation** tab: rule-based checks + **fix chips** (`POST .../architecture/remediate`). **Approve** when `validation.can_approve`.
7. Canvas: React Flow, left-to-right, nodes colored by reuse/adapt/build.

---

## Phase 1 — Catalog pipeline (offline)

**Purpose:** Load agents from JSON into Azure AI Search for hybrid retrieval during interview/planning.

```bash
python scripts/create_index.py
python -m pipeline.run --source ./data/spec.json
python scripts/validate_catalog.py
```

**Key files:**
- `pipeline/spec_loader.py` — supports array of `{project, agents}` or single object; dedupes agent IDs
- `pipeline/indexer.py` — `search_agents(query)` for planner + hints
- `schemas/agent_record.py` — `AgentRecord`, vertical normalization

**Not used in normal path:** PDF chunking/LLM extract (legacy); production path is whole `spec.json`.

---

## Phase 2 — Interview (core logic)

### Data model (`schemas/architecture_spec.py`)

- **`ArchitectureSpec`**: `problem_statement`, `fields` (14 slots), `status`, `catalog_hints`, `transcript_summary`, `architecture_blueprint`, `graph_draft`
- **`InterviewSession`**: `messages`, `pending_question`, `clarifying_questions`, `clarifying_answers`, `architecture_plan`
- **`InterviewQuestion`**: `field_key`, `question`, `chips`, optional `why_it_matters`

**Field groups:**
- Requirements: `use_case`, `data_volume`, `accuracy_target`, `hitl_behavior`, `integrations`, `latency_target`, `model_preference`, `deployment_platform`
- Architecture: `architectural_flow`, `architectural_flow_feedback`, `architectural_pattern`, `core_components`, `data_flow`, `orchestration_model`, `scalability_constraints`

**Question order:** `_pick_next_field_key` in `services/interview.py` asks every **requirements** field (in list order) before any **architecture** field. Spec becomes **sufficient** once all requirements are known (Phase 3 can start); **ready** when all 14 fields are confirmed.

### Interview turn pipeline (`services/interview.py`)

Each `POST /api/sessions/{id}/turn`:

1. **Direct slot fill** — user answer → target `field_key` immediately (`source=user_answer`)
2. **`update_spec`** — LLM merges conversation into spec (`prompts/spec_update.txt`, JSON mode)
3. **Validators** — `services/spec_validators.py` (latency format, flow length, etc.)
4. **Architecture gate** — arch fields stay pending until user answers a dedicated question (not just inferred)
5. **`next_question`** — code picks next field; LLM writes question + chips only (`prompts/next_question.txt` or field-specific prompts)
6. **`ready`** → `synthesize_architecture_blueprint` → blueprint + graph_draft

**Clarifying phase** (`services/clarifying_questions.py`):
- Runs at `start_session` before catalog/spec questions
- `field_key` like `clarifying:q1`, `clarifying:q2`, `clarifying:q3`
- After Q3 → `_begin_main_interview()` loads catalog hints + normal interview

**Other helpers:**
- `services/catalog_hints.py` — hybrid search on problem statement
- `services/answer_utils.py` — blocks submitting chip label "Other / describe" without real text
- `api/session_store.py` — memory + `data/sessions/*.json` persistence

### API routes (`api/routes.py`)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/sessions` | Start interview |
| GET | `/api/sessions/{id}` | Full session state |
| POST | `/api/sessions/{id}/turn` | Submit answer |
| POST | `/api/sessions/{id}/architecture?force=` | Generate plan |
| GET | `/api/sessions/{id}/architecture` | Cached plan |
| POST | `/api/sessions/{id}/architecture/remediate` | Apply validation fix (`finding_id`, `option_id`) |
| POST | `/api/sessions/{id}/architecture/validate` | Re-run validation only |
| POST | `/api/sessions/{id}/architecture/approve` | Mark approved if `can_approve` |

---

## Phase 3 — Architecture planning

### Planner (`services/architecture_planner.py`)

Inputs:
- `ArchitectureSpec` (known fields, blueprint excerpt)
- Interview `graph_draft`
- `catalog_matches` from multi-query Azure Search — first query is **problem statement + `transcript_summary`** (clarifying answers), then spec fields (`_enriched_problem_context` in `architecture_planner.py`)

LLM: `prompts/architecture_plan.txt` → JSON:
- `graph` — nodes (`agent|custom|gateway|human`) + edges
- `reuse_decisions` — per node: `reuse|adapt|build`, optional `agent_id`
- `summary_markdown`, `open_questions`

Fallback: if LLM fails, use interview `graph_draft` + catalog matches.

Then: **`validate_architecture_plan`** + **`enrich_validation_report`** (remediations attached).

### Validation (`services/architecture_validator.py`)

Rule-based (not full business proof). Examples:
- Graph: empty, dangling edges (unique `finding_key` per edge), orphans (off entry→exit path), disconnected subgraphs, duplicate node ids
- Catalog: empty matches, stale reuse decisions, missing decisions (incl. gateway/human), reuse without agent_id, weak fit / low score
- Spec: HITL, integrations, use_case overlap, latency/accuracy/deployment/data_volume gaps
- `open_question` items from plan

### Remediation (`services/architecture_remediation.py`)

- Builds **fix options** per finding code (`build_remediations`)
- `POST remediate` with `{ finding_id, option_id }` — server resolves full action from plan
- Actions: `set_decision`, `add_human_node`, `add_gateway_node`, `refresh_catalog`, `acknowledge`, `remove_open_question`, etc.
- **Acknowledge on fail** does not unblock approval — structural fixes required
- `can_approve`, `approval_hint` on validation report

---

## Frontend (`launchpad-ui/`)

| File | Role |
|------|------|
| `App.tsx` | Session state, tabs (spec / architecture), restore session from `localStorage`, session-lost handling |
| `ChatPanel.tsx` | Problem start, messages, chips, clarifying hint, custom describe |
| `SpecificationPanel.tsx` | Live spec fields + catalog hints |
| `ArchitectureWorkspace.tsx` | React Flow canvas + toolbar |
| `ArchitectureInspector.tsx` | Flow tab + Validation tab |
| `ArchitectureValidationPanel.tsx` | Filters, fix chips, approve, regenerate |
| `utils/graphLayout.ts` | Layered L→R layout, validation borders on nodes |
| `api.ts` | Fetch wrappers, `ApiError`, session storage key |

**Workflow steps:** Interview → Specification → Architecture (header).

---

## LLM usage pattern

- `services/llm.py`: `make_client`, `call_llm`, `load_prompt`, `strip_json_fences`
- Azure OpenAI chat + embeddings; JSON mode for structured outputs
- Prompts in `backend/prompts/*.txt` — primary place for **wording/behavior tweaks**

---

## Common tweak locations

| Want to change… | Edit |
|-----------------|------|
| Clarifying 3 questions | `prompts/clarifying_questions.txt`, `services/clarifying_questions.py` |
| Interview questions / chips | `prompts/next_question.txt`, `requirements_question.txt`, `architecture_feedback_question.txt` |
| Spec merge behavior | `prompts/spec_update.txt`, `services/interview.py` |
| Field order / required set | `schemas/architecture_spec.py` (`SUFFICIENT_REQUIREMENT_KEYS`, field lists) |
| Architecture plan quality | `prompts/architecture_plan.txt`, `architecture_planner.py` |
| Validation rules | `services/architecture_validator.py` |
| Fix options per issue | `services/architecture_remediation.py` → `build_remediations()` |
| UI copy / layout | `launchpad-ui/src/components/*.tsx`, `App.css` |
| API port / proxy | uvicorn port + `vite.config.ts` |
| Catalog data | `data/spec.json` + re-run `pipeline.run` |
| Session persistence | `api/session_store.py` |

---

## Important constraints / gotchas

1. **In-memory + disk sessions** — UI may hold stale `session_id` after manual file delete; 404 on architecture → start new interview.
2. **Catalog must be indexed** for meaningful reuse; empty index still runs but warns.
3. **Validation ≠ correctness** — structural/spec overlap only; user still judges business fit.
4. **`--reload` on uvicorn** reloads code; sessions reload from `data/sessions/` if file exists.
5. **Phase 2 static `/ui/`** is older bundled HTML; full features in Vite app.
6. **Embedding dimensions** in `.env` must match index (e.g. 1536 for `text-embedding-3-small`).

---

## Docs in repo

- `START.md` — run + troubleshooting
- `backend/README.md` — Phase 1 catalog
- `backend/README_PHASE2.md` — interview
- `backend/README_PHASE3.md` — planning + validation API

---

## Suggested prompt for Claude when tweaking

> You are editing the AFFINE Agent Launchpad repo. Read `PROJECT_HANDOFF.md` first. Make minimal diffs. Backend: FastAPI in `backend/`, prompts in `prompts/`. Frontend: `launchpad-ui/`. Do not change Azure credentials. After Python changes, assume uvicorn `--reload` on port 8003. Preserve session JSON persistence and validation `finding_id` stability when touching remediation.

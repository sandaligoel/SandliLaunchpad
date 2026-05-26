# Phase 2 — Smart Requirements & Architecture Interview

The chatbot fills an **ArchitectureSpec** (single source of truth): business requirements **and** architectural flow, grounded in your **problem statement** and **Phase 1 agent catalog** hints.

## Interview style

After the problem statement, the assistant asks **4 simple questions** only (no latency, accuracy, volume, model, or hosting — those are inferred). Grounded in **`data/spec.json`**. User-facing: **when a person steps in**, **tools to connect**, **steps end-to-end**, **main parts**. Catalog: `services/catalog_interview_context.py`.

## Turn pipeline (Phase 2.1)

Each user answer:

1. **Direct slot fill** — answer is written immediately to `pending_question.field_key` (`source=user_answer`, `confidence=1.0`).
2. **Spec update** — LLM merges problem statement + rolling **transcript summary** + last 6 messages + catalog hints (JSON mode). Does not downgrade fields just set by the user.
3. **Validators** — deterministic checks (latency format, flow length, RAG/data_flow consistency).
4. **Architecture gate** — architecture fields stay pending until the user answers a targeted question (except fields just set).
5. **Next question** — code picks the field; LLM only writes question + chips (compact prompt: known fields + pending lists).
6. **Ready** — all 14 fields known → markdown blueprint + **graph_draft** JSON for Phase 3.

**Interview order:** All **requirements** fields are asked first (in order: use case → … → deployment platform). Only after every requirement is known does the interview ask **architecture** fields (flow, pattern, components, etc.).

**Sufficient** status: all **requirements** fields known — Phase 3 architecture planning can start while architecture interview questions continue. **Ready** when every field (requirements + architecture) is confirmed.

## Spec fields

### Requirements
| Key | Label |
|-----|--------|
| `use_case` | Use case |
| `data_volume` | Data volume |
| `accuracy_target` | Accuracy target |
| `hitl_behavior` | HITL / uncertainty behaviour |
| `integrations` | Required integrations |
| `latency_target` | Latency target |
| `model_preference` | Model preference |
| `deployment_platform` | Deployment platform |

### Architectural flow
| Key | Label |
|-----|--------|
| `architectural_flow` | End-to-end architectural flow (draft) |
| `architectural_flow_feedback` | Architectural flow — your feedback (auto-filled if flow answer is detailed) |
| `architectural_pattern` | Architectural pattern |
| `core_components` | Core components / agents |
| `data_flow` | Data flow between components |
| `orchestration_model` | Orchestration model |
| `scalability_constraints` | Scalability & concurrency |

## Catalog grounding

On session start, hybrid search runs against the Phase 1 index (`fetch_catalog_hints`). Top agents appear in the spec panel and the first assistant message. Hints inform drafts only — they do not mark fields as known.

Requires a populated Azure AI Search index (`create_index.py` + `pipeline.run` or manual index from `data/spec.json`).

## Session persistence

Each save writes `data/sessions/{session_id}.json`. After `uvicorn --reload`, the API reloads sessions from disk. If **Regenerate** returns `404 Session not found`, that id was never persisted (interview before this feature) or the file was deleted — start a new interview in the UI.

## Run locally

### API

```bash
cd agent_catalog
source .venv/bin/activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### UI (Vite)

```bash
cd launchpad-ui
npm install && npm run dev
```

Open **http://localhost:5173** (API at **http://127.0.0.1:8000**). Or use **http://127.0.0.1:8000/ui/** for the bundled static UI.

## Phase 3 handoff

When `status=ready`:

- `architecture_blueprint` — markdown narrative
- `graph_draft` — `{ nodes[], edges[] }` with `type` and optional `agent_id` from catalog

## Performance notes

- Two LLM calls per turn, but prompts are smaller on the question path and transcript is summarized.
- Use `json_object` response format to reduce parse failures.
- Catalog search is best-effort; pipeline works if the index is empty.

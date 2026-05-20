# Phase 2 — Smart Requirements & Architecture Interview

The chatbot fills an **ArchitectureSpec** (single source of truth): business requirements **and** architectural flow, grounded in your **problem statement**. Each turn:

1. **Update spec** — LLM reads problem statement + conversation + current spec JSON; fills requirements and architecture fields.
2. **Next question** — Alternates **architecture feedback** (confirm/correct the flow) with **requirements** questions. Architecture fields stay pending until you answer a targeted feedback question — not auto-filled from the problem statement alone.
3. **Ready + blueprint** — When all fields are `known`, a markdown **architecture blueprint** is synthesized for Phase 3.

The Specification panel shows **Requirements** and **Architectural flow** sections plus the blueprint when complete.

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
| `architectural_flow_feedback` | Architectural flow — your feedback |
| `architectural_pattern` | Architectural pattern |
| `core_components` | Core components / agents |
| `data_flow` | Data flow between components |
| `orchestration_model` | Orchestration model |
| `scalability_constraints` | Scalability & concurrency |

## Run locally

### API

```bash
cd agent_catalog
source .venv/bin/activate
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

### UI

Open **http://127.0.0.1:8000/ui/** — paste a problem statement (e.g. your JPMC KYC platform). Questions will reference it and probe how the system should flow end-to-end.

## Design notes

- **Problem statement first** — initial spec update infers tentative architecture from the statement before the first question.
- **Continuous clarity** — each answer updates the same spec JSON; prompts see full state every turn (no reliance on chat memory alone).
- **Blueprint** — `architecture_blueprint` on the spec is generated once when status becomes `ready`.

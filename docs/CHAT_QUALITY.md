# Launchpad chat quality (questions + chips)

Professional interview flow: structured question selection, tiered grounded chips, quality gate, UI transparency.

## Architecture

| Layer | Module | Role |
|-------|--------|------|
| Quality gate | `services/chip_quality.py` | Length, dedupe, grounding; merge tiers |
| Agent input chips | `services/agent_input_chips.py` | Deterministic + catalog + contextual merge per `input_name` |
| Catalog fields | `services/catalog_chip_suggestions.py` | Architecture topics; `merge_catalog_chips` uses quality gate |
| Interview engine | `services/agent_workflow_interview.py` | Ranking, coverage, polish, handoff |
| UI | `ChatPanel.tsx` | Topic, why, coverage/risk |

## Chip tiers (merge order)

1. **Deterministic** — `_chips_for_input` / `_topic_aligned_chip`
2. **Catalog** — `catalog_values_for_input` (same input name across spec.json)
3. **Contextual** — `contextual_chips_from_conversation` (prior answers)
4. **LLM** — chips from `agent_workflow_interview` JSON (gated before use)

Always ends with `Other / describe in chat`. **Suggested** chip is never `Other`.

## Question policy

- **Coverage** — `required_input_count` from canonical spec.json inputs (minus skipped pipeline fields)
- **Next question** — rank score + dependency boost (policy before scores on same agent)
- **Wording** — `_polish_question_text` (single `?`, human label, max length)
- **Handoff** — clarifying answers + transcript in `{answered}` block for agent workflow init

## UI

- Cluster badge (`topic_label`)
- Why we ask (`why_it_matters`)
- Catalog hint (`suggestion_reason`)
- Coverage % and risk (from `agent_workflow`)

## Tests

```bash
cd backend && python3 -m pytest tests/test_chip_quality.py -q
```

## P3 — LLM chip-only (implemented)

When tiers 1–2 (deterministic + catalog + contextual) produce **fewer than 3** gated chips, the backend runs a **small dedicated** completion:

- Prompt: `prompts/agent_input_chips.txt`
- Code: `generate_llm_chips_for_input()` in `services/agent_input_chips.py`
- Temperature `0.2`, JSON mode, chips gated again before UI
- Skipped when catalog tiers already yield ≥3 chips (saves latency and tokens)
- Suggestion reason includes “AI-generated options” when P3 ran

## Future (P4)

- Turn telemetry (`chip_click`, `custom_text`, latency) for KPI tuning

# Interview Baseline (Current State)

This document captures the current backend interview behavior as a rollback and comparison reference.

## Scope

- Backend interview engine: `backend/services/agent_workflow_interview.py`
- Session state schema: `backend/schemas/agent_workflow.py`
- Session container: `backend/schemas/architecture_spec.py`
- Prompt contract: `backend/prompts/agent_workflow_interview.txt`

## Phase Model

Current phase values:

- `start`
- `interview`
- `completion_check`
- `handover`

Current phase flow:

1. `start`: session initializes, agents are matched, queue is built.
2. `interview`: one pending input question is asked at a time.
3. `completion_check`: triggered by completion gate; readiness/report content is prepared.
4. `handover`: session transitions to ready/finalized flow and returns control to builder flow.

Notes:

- Backend sets phase explicitly in interview service logic.
- Pending queue is answer-driven (not index-only).

## Metric Formulas (Current)

### Per-question rank components

Each question stores:

- `impact_score`
- `dependency_score`
- `uncertainty_score`
- `business_criticality_score`

Weighted rank:

`rank_score = 0.40*impact + 0.30*dependency + 0.20*uncertainty + 0.10*business_criticality`

### Coverage

- `coverage_score = (answered_count / total_questions) * 100`
- Rounded to one decimal place.

### Risk

- Pending questions are evaluated.
- `risk_score = min(10, avg(pending impact score) / 10)`
- Rounded to one decimal place.
- If no pending questions, risk is `0.0`.

### Critical Items

- Critical items are pending questions with `impact_score > 65`.
- Stored as short `agent_name — input_name` strings (truncated list).

## Completion Gates (Current)

Completion is triggered when any of the following are true:

1. No pending input with `impact_score > 65`
2. Question budget reached (`question_count >= min(question_budget, hard_cap)`)
3. Explicit finish intent in user answer (`ready`, `finish`, `complete`, `generate`, `done`, `proceed`)

Completion reason is stored in `completion_reason`:

- `no_high_impact_inputs_remaining`
- `question_budget_reached`
- `user_requested_finish`

## Reliability Controls (Current)

- Question dedupe by:
  - `field_key`
  - semantic pair `(agent_id, normalized_input_name)`
  - normalized question fingerprint
- Queue filtered to skip pipeline/internal inputs and inputs already implied by query.
- Per-agent cap and global safety cap are applied.
- Answer reconciliation from message history is applied to avoid re-asking after refresh.

## Known Limitations

1. Scoring heuristics are currently rule-based, not calibrated from production analytics.
2. Completion can occur by finish intent even if some medium-impact details remain.
3. Coverage denominator uses current queue, not a stable per-agent canonical required-input set.
4. Risk score is based primarily on pending impact average; uncertainty/dependency are not yet directly included in risk.
5. Progress summaries are periodic but not yet tied to a dedicated UI timeline component.
6. Cluster/phase behavior is backend-driven, but UI presentation does not yet expose all metrics consistently.

## Rollback Guidance

If future changes regress behavior, compare these areas first:

- Phase transition logic in `agent_workflow_interview.py`
- Ranking and completion gates
- Dedupe and queue finalization
- Prompt contract fields in `agent_workflow_interview.txt`

Keep this document updated whenever formulas, gates, or phase semantics change.

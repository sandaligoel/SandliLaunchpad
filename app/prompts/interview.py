"""Prompts for slot-filling interview (flow diagram + technical platform)."""

SLOT_EXTRACT_SYSTEM = """You extract architecture information for a business-friendly agent workflow interview.

Use clear, everyday names for steps (e.g. "Receive uploads", "Check compliance", "Person approves") — not heavy technical jargon.

Fill slots when evidenced: flow_steps, agent_roles, orchestration_pattern, data_sources, data_volume_scale,
retrieval_required, knowledge_graph_scope, agent_tools, model_constraints, integrations, deployment_target,
cloud_provider, human_in_the_loop, failure_escalation.

RULES:
1. flow_steps and agent_roles should align when both mentioned.
2. Do not fill security, IAM, compliance, or data-residency slots.
3. Use plain language in values. Avoid: RAG, GraphRAG, orchestrator, pipeline, subgraph, dual-lane, event-driven, hybrid index, UBO, DLQ.
4. Never use "helper" or "helpers" as a role name — say "automated step" or "specialist step".
5. Use "inferred" when implied; "empty" when unknown.

Output JSON matching SlotExtractionResult schema."""

SLOT_EXTRACT_USER = """Problem statement:
{problem_statement}

Slot keys to evaluate: {slot_keys}

Current slot state (JSON):
{current_slots}

Return slot_updates array with: key, value, status (empty|inferred|confirmed)."""

INTERVIEW_QUESTION_SYSTEM = """You generate ONE interview question for a business user planning an AI-assisted workflow.

You receive the full specification as JSON (all slots with key, label, value, status). Your question MUST:
1. Target ONLY the slot named in target_slot_key — do not ask about other topics in the same question.
2. Use confirmed and inferred values from the JSON — reference what they already said (e.g. their flow steps) so the question feels connected.
3. Skip re-asking facts already confirmed in JSON for the target slot.
4. If related_slots_json is non-empty, weave those prior answers into the question naturally.
5. One short, friendly sentence — no jargon. Write like a product manager, not a cloud architect.
6. BANNED unless the user's problem already uses them: RAG, GraphRAG, orchestrator, pipeline, subgraph, dual-lane, event-driven, hybrid, ingest, UBO, DLQ, vector, embedding.
7. BANNED role words: helper, helpers (use "automated step", "specialist step", or "coordinator step" instead).
8. Do NOT ask about security, IAM, encryption, or legal compliance regimes.
9. Exactly 4 options with snake_case id (never A/B/C/D), plain 5–12 word label, 1–2 sentence value. No "Other".

--- FEW-SHOT EXAMPLE 1 ---
target_slot_key: flow_steps
spec_json excerpt: flow_steps empty; problem mentions "weekly shelf photos for retail stores"
Output:
{{
  "question": "Starting when photos arrive each week, what are the main steps until your team gets order guidance?",
  "options": [
    {{"id": "photos_to_report", "label": "Photos, then analysis, then guidance", "value": "Photos are collected, analyzed against sales data, then the team receives suggested orders."}},
    {{"id": "photos_review_publish", "label": "Photos, review, then publish", "value": "Photos are processed, someone reviews the result, then guidance is published."}},
    {{"id": "batch_overnight", "label": "Overnight batch processing", "value": "Photos are uploaded during the day and processed overnight in one batch."}},
    {{"id": "simple_three_step", "label": "Three clear steps only", "value": "Receive photos, run checks, send the final recommendation."}}
  ]
}}

--- FEW-SHOT EXAMPLE 2 ---
target_slot_key: orchestration_pattern
related_slots_json: flow_steps confirmed "Upload photos → analyze shelf → join sales data → publish guidance"
Output:
{{
  "question": "For your flow (upload → analyze → join sales → publish), should those steps run strictly one after another or can some run at the same time?",
  "options": [
    {{"id": "strictly_sequential", "label": "Strictly one after another", "value": "Each step waits for the previous step to finish."}},
    {{"id": "parallel_checks", "label": "Some checks at the same time", "value": "Independent checks run together, then results are combined before publish."}},
    {{"id": "coordinator_routes", "label": "A coordinator picks the next step", "value": "One central step decides which step runs next based on the case."}},
    {{"id": "trigger_on_upload", "label": "Starts when new photos arrive", "value": "Each new upload automatically starts the workflow."}}
  ]
}}

--- FEW-SHOT EXAMPLE 3 ---
target_slot_key: human_in_the_loop
related_slots_json: agent_roles confirmed "Photo reader, Shelf analyzer, Guidance writer"
Output:
{{
  "question": "At which point should a person review the work before guidance goes out?",
  "options": [
    {{"id": "before_publish", "label": "Before anything is published", "value": "A person approves the final guidance before it is sent."}},
    {{"id": "after_analysis", "label": "After the shelf analysis", "value": "Automated analysis runs first; a person checks before joining sales data."}},
    {{"id": "exceptions_only", "label": "Only when something looks wrong", "value": "Routine cases stay automatic; people only handle flagged items."}},
    {{"id": "no_regular_review", "label": "No regular human review", "value": "The main path stays fully automatic."}}
  ]
}}

Output JSON: {{ "question": "...", "options": [...] }}"""

INTERVIEW_QUESTION_USER = """Problem statement:
{problem_statement}

Target slot to ask about NOW:
- key: {slot_key}
- label: {slot_label}
- description: {slot_description}
- current value: {current_value}
- current status: {current_status}

Focus for this slot: {deep_guidance}

Full specification state (JSON — read this to stay relevant):
{spec_json}

Related prior answers (JSON — reference these in your question when useful):
{related_slots_json}

Interview progress: {progress_summary}

Generate the next question and four options for target slot "{slot_key}" only."""

FOLLOWUP_QUESTION_SYSTEM = """You generate ONE follow-up because the prior answer on this slot was too brief.

RULES:
1. Read spec_json and related_slots_json — stay on the same target slot; reference what they already confirmed elsewhere.
2. One short sentence a business user would understand. No jargon. Never use "helper" or "helpers" as a role name.
3. Four options: snake_case id, plain 5–12 word label, 1–2 sentence value. Not A/B/C/D.

Output JSON: {{ "question": "...", "options": [...] }}"""

FOLLOWUP_QUESTION_USER = """Problem statement: {problem_statement}

Target slot: {slot_label} ({slot_key})
Focus: {deep_guidance}
Current answer on this slot (too brief): {current_value}

Full specification state (JSON):
{spec_json}

Related prior answers (JSON):
{related_slots_json}

Generate a follow-up question and four options."""

ANSWER_PARSE_SYSTEM = """Parse the user's answer into architecture spec slot updates.

Use plain language in slot values. Never use "helper" or "helpers" as a role name.
Update only slots clearly addressed. Prefer confirmed status for explicit answers.
Do not invent security/compliance values.

Output JSON matching SlotExtractionResult schema."""

ANSWER_PARSE_USER = """Problem statement: {problem_statement}

Target slot: {target_slot} ({target_label})
User answer: {answer}

Current specification (JSON):
{current_slots}

Return slot_updates with key, value, status."""

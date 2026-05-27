"""Default multiple-choice options per spec slot — plain language, minimal jargon."""

from __future__ import annotations

from backend.app.schemas.interview import InterviewOption

_SLOT_DEFAULTS: dict[str, list[tuple[str, str, str]]] = {
    "flow_steps": [
        (
            "linear",
            "One step after another",
            "Work moves in a clear order from start to finish. Each step finishes before the next begins.",
        ),
        (
            "parallel_then_combine",
            "Some steps run together, then combine",
            "A few checks can run at the same time. After that, results are brought together in one place.",
        ),
        (
            "human_before_finish",
            "Person checks before we finish",
            "Most work is automatic, but someone reviews important results before we call it done.",
        ),
        (
            "upload_to_output",
            "From upload to final output",
            "Files or requests come in, get processed through several steps, and end as a report or published result.",
        ),
    ],
    "agent_roles": [
        (
            "intake_process_publish",
            "Receive, process, publish",
            "One step receives inputs, another does the main work, another prepares the final output.",
        ),
        (
            "check_and_approve",
            "Check work, then approve",
            "Steps that review quality, flag problems, and hand off to a person if needed.",
        ),
        (
            "specialist_steps",
            "A few focused specialists",
            "Separate steps for reading documents, comparing images, and writing the answer.",
        ),
        (
            "coordinator_plus_workers",
            "Coordinator plus specialist steps",
            "One step organizes the work; other steps each handle one type of task.",
        ),
    ],
    "data_sources": [
        (
            "documents",
            "Documents (PDF, Word, scans)",
            "Mainly files people upload or store in a shared folder.",
        ),
        (
            "documents_and_photos",
            "Documents and photos",
            "A mix of PDFs or forms plus photos from the field or warehouse.",
        ),
        (
            "existing_system",
            "Our existing business system",
            "Data is pulled from software we already use (cases, orders, or customer records).",
        ),
        (
            "mix",
            "Files plus our internal system",
            "Some information arrives as files; some is read from internal tools we already have.",
        ),
    ],
    "data_volume_scale": [
        (
            "small",
            "Small pilot (under 100 a month)",
            "We are starting small: fewer than 100 items per month for now.",
        ),
        (
            "medium",
            "Medium (hundreds per month)",
            "A few hundred cases or jobs per month, with a handful running at once.",
        ),
        (
            "large",
            "Large (thousands per month)",
            "High volume: thousands per month and many running at the same time during peaks.",
        ),
        (
            "mostly_overnight",
            "Mostly overnight batches",
            "Heavy work runs overnight; people only check exceptions during the day.",
        ),
    ],
    "orchestration_pattern": [
        (
            "sequential",
            "One after another",
            "Each step waits for the previous one to finish. Simple and easy to follow.",
        ),
        (
            "coordinator",
            "One coordinator decides what's next",
            "A central step looks at the situation and sends work to the right next step.",
        ),
        (
            "parallel_merge",
            "Some at once, then combine",
            "Independent checks run together, then one step merges the results.",
        ),
        (
            "on_new_work",
            "Starts when new work arrives",
            "When a new file or request shows up, the workflow starts automatically.",
        ),
    ],
    "retrieval_required": [
        (
            "search_past_docs",
            "Search past documents for answers",
            "Steps should look up similar past files and policies before deciding.",
        ),
        (
            "search_text_and_images",
            "Search text and images",
            "We need to find relevant words and pictures from earlier cases.",
        ),
        (
            "link_related_facts",
            "Connect related facts, then search",
            "Related people, companies, or items should be linked to help answer questions.",
        ),
        (
            "no_search",
            "No document search needed",
            "Each case is self-contained; we do not need to search old files.",
        ),
    ],
    "knowledge_graph_scope": [
        (
            "people_and_companies",
            "Link people and companies",
            "Track who is connected to whom (owners, directors, related businesses).",
        ),
        (
            "products_and_shipments",
            "Link products and shipments",
            "Track items, orders, and whether photos match what was expected.",
        ),
        (
            "simple_lists",
            "Simple lists only",
            "No complex relationship map; keep extracted facts in plain lists.",
        ),
        (
            "not_in_first_version",
            "Not in the first version",
            "We can skip relationship maps for now and add them later if needed.",
        ),
    ],
    "agent_tools": [
        (
            "read_documents",
            "Read and extract from documents",
            "Tools that pull text and fields out of PDFs and forms.",
        ),
        (
            "read_images",
            "Understand images",
            "Tools that look at photos and describe what they see.",
        ),
        (
            "search_and_rules",
            "Search files and apply rules",
            "Tools that find relevant passages and check against written rules.",
        ),
        (
            "basic_ai_only",
            "Basic AI only",
            "Mainly language and vision AI without extra special databases.",
        ),
    ],
    "model_constraints": [
        (
            "company_approved_ai",
            "Use our company's approved AI",
            "Stick to AI services our organization already allows.",
        ),
        (
            "text_and_images",
            "Handle text and images",
            "Need both reading documents and understanding pictures.",
        ),
        (
            "keep_it_simple",
            "Keep models simple and consistent",
            "Prefer one main AI setup rather than many different ones.",
        ),
        (
            "decide_later",
            "Decide later",
            "Model choice is not fixed yet; focus on the workflow first.",
        ),
    ],
    "integrations": [
        (
            "case_system",
            "Our case or ticket system",
            "Read and update status in the tool our team already uses for cases.",
        ),
        (
            "file_storage",
            "Shared file storage",
            "Read inputs and save outputs to a shared drive or cloud folder.",
        ),
        (
            "email_or_portal",
            "Email or customer portal",
            "Results go back through email or a portal customers already use.",
        ),
        (
            "minimal",
            "Few integrations for now",
            "Only connect what is absolutely required in the first release.",
        ),
    ],
    "deployment_target": [
        (
            "cloud_managed",
            "Run in the cloud (managed service)",
            "Host in the cloud on a service that scales up and down automatically.",
        ),
        (
            "cloud_containers",
            "Run in the cloud (containers)",
            "Package each step so it can run independently in the cloud.",
        ),
        (
            "existing_servers",
            "On servers we already have",
            "Prefer running on infrastructure our IT team already operates.",
        ),
        (
            "not_sure",
            "Not sure yet",
            "Deployment choice is open; workflow design matters more right now.",
        ),
    ],
    "cloud_provider": [
        (
            "azure",
            "Microsoft Azure",
            "We use or plan to use Microsoft Azure.",
        ),
        (
            "aws",
            "Amazon Web Services",
            "We use or plan to use AWS.",
        ),
        (
            "either_major",
            "Either major cloud is fine",
            "No strong preference between the big cloud providers.",
        ),
        (
            "on_prem",
            "Mostly on our own servers",
            "Prefer keeping data and processing inside our own environment.",
        ),
    ],
    "human_in_the_loop": [
        (
            "before_finish",
            "Someone approves before we finish",
            "A person must sign off before the final result is sent out.",
        ),
        (
            "only_when_unsure",
            "Only when the system is unsure",
            "People step in for edge cases; routine work stays automatic.",
        ),
        (
            "review_queue",
            "Review queue for problems",
            "Flagged items go to a queue for a human to check.",
        ),
        (
            "fully_automatic",
            "Fully automatic",
            "No regular human approval step in the main path.",
        ),
    ],
    "failure_escalation": [
        (
            "retry_then_person",
            "Try again, then ask a person",
            "Automatic retry once or twice; then route to a human with the details.",
        ),
        (
            "hold_until_fixed",
            "Hold the case until fixed",
            "Stop the case until someone resolves the issue.",
        ),
        (
            "simple_rules_backup",
            "Fall back to simple rules",
            "If AI fails, use basic rule checks and mark for review.",
        ),
        (
            "alert_team",
            "Alert the team",
            "Send a notification so the operations team can investigate.",
        ),
    ],
}


def default_options_for_slot(slot_key: str, slot_label: str) -> list[InterviewOption]:
    raw = _SLOT_DEFAULTS.get(slot_key)
    if not raw:
        return [
            InterviewOption(
                id="approach_a",
                label=f"Simple approach for {slot_label}",
                value=f"A straightforward way to handle {slot_label}, easy for the team to understand.",
            ),
            InterviewOption(
                id="approach_b",
                label=f"Match how we work today",
                value=f"Align {slot_label} with how our team already operates.",
            ),
            InterviewOption(
                id="approach_c",
                label=f"Start small for {slot_label}",
                value=f"Keep the first version of {slot_label} small; add more later.",
            ),
            InterviewOption(
                id="approach_d",
                label=f"Full setup for {slot_label}",
                value=f"Plan for a complete setup for {slot_label} from the start.",
            ),
        ]
    return [InterviewOption(id=i, label=l, value=v) for i, l, v in raw]

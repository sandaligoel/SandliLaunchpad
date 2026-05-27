"""Fast, local prefill of spec slots from a problem statement (no LLM)."""

from __future__ import annotations

from app.schemas.architecture_spec import SlotStatus
from app.schemas.slot_extraction import SlotUpdate

_KEYWORD_UPDATES: list[tuple[tuple[str, ...], list[SlotUpdate]]] = [
    (
        ("kyc", "onboarding", "know your customer", "ubo", "beneficial owner"),
        [
            SlotUpdate(
                key="flow_steps",
                value="Receive documents → extract information → check policy → score risk → analyst review → finish case",
                status=SlotStatus.INFERRED,
            ),
            SlotUpdate(
                key="data_sources",
                value="PDF and Word documents from case uploads",
                status=SlotStatus.INFERRED,
            ),
        ],
    ),
    (
        ("shelf", "retail", "store photo", "planogram", "pos"),
        [
            SlotUpdate(
                key="flow_steps",
                value="Collect photos → analyze shelf → join sales data → publish order guidance",
                status=SlotStatus.INFERRED,
            ),
            SlotUpdate(
                key="data_sources",
                value="Field photos plus sales or POS data",
                status=SlotStatus.INFERRED,
            ),
        ],
    ),
    (
        ("trade", "bill of lading", "bl ", "shipment", "warehouse photo"),
        [
            SlotUpdate(
                key="flow_steps",
                value="Receive trade documents → extract fields → match photos → report issues → close case",
                status=SlotStatus.INFERRED,
            ),
        ],
    ),
    (
        ("pdp", "product detail", "marketplace", "listing", "compliance image"),
        [
            SlotUpdate(
                key="flow_steps",
                value="Load product assets → generate or check images → compliance review → publish listing",
                status=SlotStatus.INFERRED,
            ),
        ],
    ),
]

_SINGLE_HINTS: list[tuple[tuple[str, ...], SlotUpdate]] = [
    (("azure", "microsoft cloud"), SlotUpdate(key="cloud_provider", value="Microsoft Azure", status=SlotStatus.INFERRED)),
    (("aws", "amazon web services"), SlotUpdate(key="cloud_provider", value="Amazon Web Services", status=SlotStatus.INFERRED)),
    (("human review", "analyst review", "manual review", "approve"), SlotUpdate(key="human_in_the_loop", value="Person reviews before the case is finished", status=SlotStatus.INFERRED)),
    (("search past", "previous cases", "historical document"), SlotUpdate(key="retrieval_required", value="Search past documents for answers", status=SlotStatus.INFERRED)),
    (("graph", "relationship", "connected parties"), SlotUpdate(key="knowledge_graph_scope", value="Link related people and companies", status=SlotStatus.INFERRED)),
    (("container apps", "container app"), SlotUpdate(key="deployment_target", value="Run in the cloud (managed service)", status=SlotStatus.INFERRED)),
    (("kubernetes", " aks"), SlotUpdate(key="deployment_target", value="Run in the cloud (containers)", status=SlotStatus.INFERRED)),
]


def heuristic_prefill_from_problem(problem_statement: str) -> list[SlotUpdate]:
    """Infer obvious slots from keywords so /start does not need an LLM call."""
    text = problem_statement.lower()
    updates: list[SlotUpdate] = []
    seen: set[str] = set()

    def add(u: SlotUpdate) -> None:
        if u.key in seen:
            return
        seen.add(u.key)
        updates.append(u)

    for keywords, batch in _KEYWORD_UPDATES:
        if any(k in text for k in keywords):
            for u in batch:
                add(u)

    for keywords, u in _SINGLE_HINTS:
        if any(k in text for k in keywords):
            add(u)

    if any(w in text for w in ("thousand", "high volume", "2000", "peak")):
        add(SlotUpdate(key="data_volume_scale", value="Large (thousands per month)", status=SlotStatus.INFERRED))
    elif any(w in text for w in ("pilot", "small", "under 100")):
        add(SlotUpdate(key="data_volume_scale", value="Small pilot (under 100 a month)", status=SlotStatus.INFERRED))

    return updates

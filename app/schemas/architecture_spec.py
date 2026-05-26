"""Architecture specification with trackable slots for smart interview."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SlotStatus(str, Enum):
    EMPTY = "empty"
    INFERRED = "inferred"
    CONFIRMED = "confirmed"


class SpecSlot(BaseModel):
    key: str
    label: str
    description: str = ""
    required: bool = True
    priority: int = Field(default=50, ge=1, le=200)
    value: str = ""
    status: SlotStatus = SlotStatus.EMPTY
    source: str = ""
    depth_followup_done: bool = False


# Flow diagram + platform slots (plain-language interview; no security deep-dive).
SLOT_DEFINITIONS: list[dict] = [
    {
        "key": "flow_steps",
        "label": "What happens, in order",
        "description": "The main steps from start to finish, in order",
        "priority": 10,
    },
    {
        "key": "agent_roles",
        "label": "Who does each job",
        "description": "Each automated step and what it is responsible for",
        "priority": 20,
    },
    {
        "key": "data_sources",
        "label": "Where information comes from",
        "description": "Files, photos, or systems that supply the data",
        "priority": 22,
    },
    {
        "key": "data_volume_scale",
        "label": "How much work to expect",
        "description": "Roughly how many cases or jobs per month",
        "priority": 24,
        "required": False,
    },
    {
        "key": "orchestration_pattern",
        "label": "How steps are chained",
        "description": "One-by-one, some at the same time, or with a coordinator",
        "priority": 30,
    },
    {
        "key": "retrieval_required",
        "label": "Searching past documents",
        "description": "Whether the system needs to look up older files to decide",
        "priority": 32,
    },
    {
        "key": "knowledge_graph_scope",
        "label": "Linking related facts",
        "description": "Whether related people, companies, or items should be connected",
        "priority": 34,
    },
    {
        "key": "agent_tools",
        "label": "Tools each step can use",
        "description": "Such as reading documents, reading images, or searching files",
        "priority": 36,
        "required": False,
    },
    {
        "key": "model_constraints",
        "label": "Which AI to use",
        "description": "What kind of AI the organization allows",
        "priority": 38,
        "required": False,
    },
    {
        "key": "integrations",
        "label": "Other systems to connect",
        "description": "Software you already use that must send or receive data",
        "priority": 40,
        "required": False,
    },
    {
        "key": "deployment_target",
        "label": "Where it runs",
        "description": "Cloud service or servers that will host the solution",
        "priority": 42,
    },
    {
        "key": "cloud_provider",
        "label": "Which cloud",
        "description": "If applicable — e.g. Microsoft Azure or AWS",
        "priority": 44,
        "required": False,
    },
    {
        "key": "human_in_the_loop",
        "label": "When a person reviews",
        "description": "Where someone must check or approve before finishing",
        "priority": 50,
        "required": False,
    },
    {
        "key": "failure_escalation",
        "label": "When something goes wrong",
        "description": "Retry, alert a person, or hold the case",
        "priority": 52,
        "required": False,
    },
]

DEPTH_FOLLOWUP_SLOTS: frozenset[str] = frozenset({"agent_roles", "flow_steps"})

SHALLOW_ANSWER_MAX_CHARS = 100
GENERIC_ANSWER_MARKERS = (
    "not specified",
    "best effort",
    "tbd",
    "to be determined",
    "n/a",
    "unknown",
)


class ArchitectureSpec(BaseModel):
    session_id: str = ""
    problem_statement: str = ""
    project_name: str = ""
    slots: list[SpecSlot] = Field(default_factory=list)
    ready_for_plan: bool = False
    pending_question: str = ""
    pending_target_slot: str = ""
    pending_options: list[dict[str, str]] = Field(default_factory=list)
    pending_is_followup: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def missing_required_slots(self) -> list[SpecSlot]:
        return [
            s
            for s in self.slots
            if s.required
            and s.status in (SlotStatus.EMPTY, SlotStatus.INFERRED)
            and not s.value.strip()
        ]

    def _slot_allows_depth_followup(self, slot: SpecSlot) -> bool:
        return slot.key in DEPTH_FOLLOWUP_SLOTS

    def slots_needing_depth_followup(self) -> list[SpecSlot]:
        out: list[SpecSlot] = []
        for s in self.slots:
            if not self._slot_allows_depth_followup(s):
                continue
            if s.depth_followup_done or not s.value.strip():
                continue
            if s.status not in (SlotStatus.CONFIRMED, SlotStatus.INFERRED):
                continue
            lower = s.value.lower()
            if len(s.value) < SHALLOW_ANSWER_MAX_CHARS:
                out.append(s)
                continue
            if any(m in lower for m in GENERIC_ANSWER_MARKERS):
                out.append(s)
        return sorted(out, key=lambda x: x.priority)

    def next_slot_to_ask(self) -> SpecSlot | None:
        missing = self.missing_required_slots()
        if missing:
            return sorted(missing, key=lambda x: x.priority)[0]

        inferred = [
            s for s in self.slots if s.status == SlotStatus.INFERRED and s.value.strip()
        ]
        if inferred:
            return sorted(inferred, key=lambda x: x.priority)[0]

        depth = self.slots_needing_depth_followup()
        if depth:
            return depth[0]

        return None

    def is_complete(self) -> bool:
        for s in self.slots:
            if s.required and not s.value.strip():
                return False
            if s.status == SlotStatus.INFERRED:
                return False
            if (
                self._slot_allows_depth_followup(s)
                and not s.depth_followup_done
                and self._slot_is_shallow(s)
            ):
                return False
        return True

    def _slot_is_shallow(self, slot: SpecSlot) -> bool:
        if not slot.value.strip():
            return False
        lower = slot.value.lower()
        if len(slot.value) < SHALLOW_ANSWER_MAX_CHARS:
            return True
        return any(m in lower for m in GENERIC_ANSWER_MARKERS)

    def completion_pct(self) -> float:
        required = [s for s in self.slots if s.required]
        if not required:
            return 100.0
        filled = sum(
            1
            for s in required
            if s.value.strip()
            and s.status == SlotStatus.CONFIRMED
            and (
                s.depth_followup_done
                or not self._slot_allows_depth_followup(s)
            )
        )
        partial = sum(
            1
            for s in required
            if s.value.strip()
            and s.status == SlotStatus.CONFIRMED
            and self._slot_allows_depth_followup(s)
            and not s.depth_followup_done
        )
        score = filled + 0.5 * partial
        return round(100.0 * score / len(required), 1)

    def to_summary_dict(self) -> dict[str, str]:
        return {s.key: s.value for s in self.slots if s.value.strip()}

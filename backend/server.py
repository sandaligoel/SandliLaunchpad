"""Agent Launchpad backend — single-file bundle. Regenerate: python scripts/bundle_server.py"""

from __future__ import annotations

import logging
import os
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent
PROMPTS_DIR = BACKEND_ROOT / "prompts"
DATA_DIR = BACKEND_ROOT / "data"
SESSIONS_DIR = DATA_DIR / "sessions"



# ========================================================================
# config.py
# ========================================================================


"""Application configuration loaded from environment variables."""
import logging
import os
import re
from dataclasses import dataclass
from dotenv import load_dotenv
load_dotenv()
logger = logging.getLogger(__name__)
EMBEDDING_DIMENSIONS = 1536
_REQUIRED_VARS = ('AZURE_OPENAI_ENDPOINT', 'AZURE_OPENAI_API_KEY', 'AZURE_OPENAI_API_VERSION', 'AZURE_OPENAI_CHAT_DEPLOYMENT', 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'AZURE_SEARCH_ENDPOINT', 'AZURE_SEARCH_API_KEY', 'AZURE_SEARCH_INDEX_NAME')

def _mask_secret(value: str, visible: int=4) -> str:
    """Return a masked representation of a secret, showing only the last N characters."""
    if not value:
        return '(empty)'
    if len(value) <= visible:
        return '*' * len(value)
    return '*' * (len(value) - visible) + value[-visible:]

@dataclass(frozen=True)
class Settings:
    """Typed configuration for the agent catalog pipeline."""
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str
    azure_openai_chat_deployment: str
    azure_openai_embedding_deployment: str
    azure_search_endpoint: str
    azure_search_api_key: str
    azure_search_index_name: str
    pdf_path: str
    log_level: str

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from environment variables."""
        return cls(azure_openai_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT', '').strip(), azure_openai_api_key=os.getenv('AZURE_OPENAI_API_KEY', '').strip(), azure_openai_api_version=os.getenv('AZURE_OPENAI_API_VERSION', '').strip(), azure_openai_chat_deployment=os.getenv('AZURE_OPENAI_CHAT_DEPLOYMENT', '').strip(), azure_openai_embedding_deployment=os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', '').strip(), azure_search_endpoint=os.getenv('AZURE_SEARCH_ENDPOINT', '').strip(), azure_search_api_key=os.getenv('AZURE_SEARCH_API_KEY', '').strip(), azure_search_index_name=os.getenv('AZURE_SEARCH_INDEX_NAME', '').strip(), pdf_path=os.getenv('PDF_PATH', './data/spec.json').strip(), log_level=os.getenv('LOG_LEVEL', 'INFO').strip().upper())

    def validate(self) -> None:
        """Raise ValueError if any required environment variable is missing."""
        missing = []
        for var in _REQUIRED_VARS:
            if not getattr(self, _field_name(var)):
                missing.append(var)
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}. Copy .env.example to .env and fill in your Azure credentials.")

    def print_masked_summary(self) -> None:
        """Log a masked summary of configuration (endpoints visible, keys masked)."""
        logger.info('Configuration loaded:')
        logger.info('  AZURE_OPENAI_ENDPOINT: %s', self.azure_openai_endpoint)
        logger.info('  AZURE_OPENAI_API_KEY: %s', _mask_secret(self.azure_openai_api_key))
        logger.info('  AZURE_OPENAI_API_VERSION: %s', self.azure_openai_api_version)
        logger.info('  AZURE_OPENAI_CHAT_DEPLOYMENT: %s', self.azure_openai_chat_deployment)
        logger.info('  AZURE_OPENAI_EMBEDDING_DEPLOYMENT: %s', self.azure_openai_embedding_deployment)
        logger.info('  AZURE_SEARCH_ENDPOINT: %s', self.azure_search_endpoint)
        logger.info('  AZURE_SEARCH_API_KEY: %s', _mask_secret(self.azure_search_api_key))
        logger.info('  AZURE_SEARCH_INDEX_NAME: %s', self.azure_search_index_name)
        logger.info('  PDF_PATH: %s', self.pdf_path)
        logger.info('  LOG_LEVEL: %s', self.log_level)

def _field_name(env_var: str) -> str:
    """Map an environment variable name to a Settings field name."""
    return env_var.lower()

def get_settings() -> Settings:
    """Load, validate, and return application settings."""
    settings = Settings.from_env()
    settings.validate()
    return settings

def configure_logging(level: str | None=None) -> None:
    """Configure root logging from settings or an explicit level."""
    log_level = (level or os.getenv('LOG_LEVEL', 'INFO')).upper()
    logging.basicConfig(level=getattr(logging, log_level, logging.INFO), format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')


# ========================================================================
# schemas/architecture_plan.py
# ========================================================================


"""Phase 3 architecture plan — graph + catalog reuse decisions."""
from typing import Literal, Optional
from pydantic import BaseModel, Field
ReuseDecisionType = Literal['reuse', 'adapt', 'build']

class CatalogMatch(BaseModel):
    """Agent retrieved from the catalog for planning."""
    agent_id: str
    name: str
    category: str = ''
    origin_client: str = ''
    origin_project: str = ''
    function_summary: str = ''
    score: float = 0.0
    matched_for: str = ''

class ReuseDecision(BaseModel):
    """Whether a graph node reuses a catalog agent or is built custom."""
    node_id: str
    node_label: str
    decision: ReuseDecisionType
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    rationale: str = ''
    catalog_score: Optional[float] = None

class RemediationOption(BaseModel):
    """User-selectable fix for a validation finding."""
    id: str
    label: str
    description: str = ''
    finding_id: str = ''
    action: str = 'acknowledge'
    node_id: Optional[str] = None
    decision: Optional[ReuseDecisionType] = None
    agent_id: Optional[str] = None
    agent_name: Optional[str] = None
    catalog_score: Optional[float] = None
    gateway_label: Optional[str] = None
    question_text: Optional[str] = None
    edge_from: Optional[str] = None
    edge_to: Optional[str] = None

class ValidationResolution(BaseModel):
    """Recorded user choice for a finding."""
    action: str
    action_id: str
    label: str = ''

class ValidationFinding(BaseModel):
    """One pass, warn, or fail check."""
    level: Literal['pass', 'warn', 'fail']
    code: str
    message: str
    node_id: Optional[str] = None
    finding_id: Optional[str] = None
    finding_key: Optional[str] = None
    blocks_approval: bool = False
    help_text: str = ''
    remediations: list[RemediationOption] = Field(default_factory=list)
    resolved: bool = False
    resolution: Optional[ValidationResolution] = None

class ArchitectureValidationReport(BaseModel):
    """Rule-based validation of plan vs spec and catalog."""
    overall: Literal['pass', 'warn', 'fail'] = 'pass'
    pass_count: int = 0
    warn_count: int = 0
    fail_count: int = 0
    structural_fail_count: int = 0
    unresolved_actionable_count: int = 0
    can_approve: bool = False
    approval_hint: str = ''
    items: list[ValidationFinding] = Field(default_factory=list)
    node_status: dict[str, Literal['pass', 'warn', 'fail']] = Field(default_factory=dict)

class ArchitecturePlan(BaseModel):
    """Final planned architecture for canvas rendering."""
    graph: GraphDraft
    reuse_decisions: list[ReuseDecision] = Field(default_factory=list)
    catalog_matches: list[CatalogMatch] = Field(default_factory=list)
    summary_markdown: str = ''
    open_questions: list[str] = Field(default_factory=list)
    validation: Optional[ArchitectureValidationReport] = None
    validation_resolutions: dict[str, ValidationResolution] = Field(default_factory=dict)
    architecture_approved: bool = False


# ========================================================================
# schemas/agent_workflow.py
# ========================================================================


"""Agent-centric setup interview (spec.json inputs) for Agent Launchpad."""
from typing import Literal
from pydantic import BaseModel, Field

class MatchedAgentSummary(BaseModel):
    agent_id: str
    name: str
    reason: str

class AgentSetupQuestionItem(BaseModel):
    field_key: str
    agent_id: str
    agent_name: str
    input_name: str
    question: str
    chips: list[str] = Field(default_factory=list)
    cluster: str = 'General Configuration'
    impact_score: int = 50
    dependency_score: int = 50
    uncertainty_score: int = 50
    business_criticality_score: int = 50
    rank_score: float = 50.0
WorkflowPhase = Literal['start', 'interview', 'completion_check', 'handover']

class AgentWorkflowState(BaseModel):
    query_understood: str = ''
    matched_agents: list[MatchedAgentSummary] = Field(default_factory=list)
    questions: list[AgentSetupQuestionItem] = Field(default_factory=list)
    answers: dict[str, str] = Field(default_factory=dict)
    next_index: int = 0
    current_phase: WorkflowPhase = 'start'
    question_count: int = 0
    question_budget: int = 18
    hard_cap: int = 25
    coverage_score: float = 0.0
    risk_score: float = 10.0
    required_input_count: int = 0
    critical_items: list[str] = Field(default_factory=list)
    completion_reason: str | None = None
    current_cluster: str | None = None

    def is_complete(self) -> bool:
        """True when no pending questions remain (see agent_workflow_interview)."""
        answered = {k for k, v in self.answers.items() if str(v).strip()}
        for q in self.questions:
            if q.field_key not in answered:
                return False
        return True


# ========================================================================
# schemas/discovery.py
# ========================================================================


"""Conversation state for ChatGPT-style workflow discovery."""
from typing import Any, Literal
from pydantic import BaseModel, Field
DiscoveryPhase = Literal['active', 'complete']
InterviewPhase = Literal['asking', 'waiting_for_answer', 'explaining', 'followup', 'sufficient_information', 'ready_for_architecture']
DISCOVERY_FIELD_PREFIX = 'discovery:'
DISCOVERY_TOPICS: tuple[str, ...] = ('workflow_domain', 'input_types', 'data_sources', 'hitl_review_policy', 'integrations_systems', 'output_deliverables', 'deployment_context', 'domain_constraints')

class DiscoveryAnswer(BaseModel):
    question_id: str
    question: str
    answer: str
    topic: str = ''
    turn_index: int = 0

class ExtractedRequirement(BaseModel):
    key: str
    value: str
    confidence: float = 0.7
    source: Literal['problem_statement', 'user_answer', 'inferred'] = 'inferred'

class DiscoveryState(BaseModel):
    """Accumulated context for state-driven questioning."""
    original_request: str = ''
    phase: DiscoveryPhase = 'active'
    answers: list[DiscoveryAnswer] = Field(default_factory=list)
    extracted_requirements: list[ExtractedRequirement] = Field(default_factory=list)
    catalog_agent_ids: list[str] = Field(default_factory=list)
    matched_agent_names: list[str] = Field(default_factory=list)
    current_understanding: str = ''
    missing_information: list[str] = Field(default_factory=list)
    last_question_reason: str = ''
    last_topic: str = ''
    question_count: int = 0
    max_questions: int = 7
    covered_topics: list[str] = Field(default_factory=list)
    interview_phase: InterviewPhase = 'waiting_for_answer'
    debug_entries: list[dict[str, Any]] = Field(default_factory=list)

def discovery_field_key(topic: str, question_id: str) -> str:
    return f'{DISCOVERY_FIELD_PREFIX}{topic}:{question_id}'

def is_discovery_field_key(field_key: str | None) -> bool:
    return bool(field_key and field_key.startswith(DISCOVERY_FIELD_PREFIX))

def parse_discovery_field_key(field_key: str) -> tuple[str, str]:
    """Return (topic, question_id) from discovery:topic:qid."""
    body = field_key[len(DISCOVERY_FIELD_PREFIX):]
    if ':' in body:
        topic, qid = body.split(':', 1)
        return (topic, qid)
    return (body, 'q0')


# ========================================================================
# schemas/agent_record.py
# ========================================================================


"""Pydantic models for agent and project catalog records."""
import re
from typing import Literal, Optional, get_args
from pydantic import BaseModel, Field
Category = Literal['Finance & Procurement', 'Document & Data', 'Quality & Compliance', 'Supply Chain & Logistics', 'Sales & Revenue', 'Healthcare & Compliance']
Vertical = Literal['CPG', 'Retail', 'Healthcare', 'Manufacturing', 'Finance', 'Other']
_VERTICAL_VALUES: frozenset[str] = frozenset(get_args(Vertical))
_VERTICAL_ALIASES: dict[str, Vertical] = {'financial': 'Finance', 'financial services': 'Finance', 'banking': 'Finance', 'consumer packaged goods': 'CPG', 'fmcg': 'CPG', 'retail / cpg': 'Retail', 'retail/cpg': 'Retail', 'retail and cpg': 'Retail', 'cpg / retail': 'Retail', 'health care': 'Healthcare', 'life sciences': 'Healthcare', 'industrial': 'Manufacturing'}

def normalize_vertical(value: str | None) -> Vertical:
    """
    Map LLM or PDF text to a canonical vertical, defaulting to Other.

    Accepts known literals case-insensitively and common synonyms (e.g. Banking → Finance).
    """
    if not value or not str(value).strip():
        return 'Other'
    text = str(value).strip()
    if text in _VERTICAL_VALUES:
        return text
    lowered = text.lower()
    mapped = _VERTICAL_ALIASES.get(lowered)
    if mapped:
        return mapped
    if 'retail' in lowered and 'cpg' in lowered:
        return 'Retail'
    if 'finance' in lowered or 'banking' in lowered:
        return 'Finance'
    for canonical in _VERTICAL_VALUES:
        if text.lower() == canonical.lower():
            return canonical
    return 'Other'
AgentStatus = Literal['live', 'available', 'deprecated']
ImplementationKind = Literal['agent', 'function', 'tool']

def slugify(text: str) -> str:
    """
    Convert text to a URL-safe slug for use as record IDs.

    Lowercases, strips special characters, and replaces spaces with hyphens.
    """
    text = text.lower().strip()
    text = re.sub('[^\\w\\s-]', '', text)
    text = re.sub('[\\s_]+', '-', text)
    text = re.sub('-+', '-', text)
    return text.strip('-')

class AgentRecord(BaseModel):
    """Structured record for a single AI agent extracted from the solutions PDF."""
    id: str = ''
    name: str
    version: str = '1.0'
    category: Category
    function_summary: str
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    model_used: str = 'Unknown'
    tech_stack: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    origin_project: str = ''
    origin_client: str = ''
    vertical: Vertical = 'Other'
    status: AgentStatus = 'available'
    typical_accuracy: Optional[str] = None
    notes: Optional[str] = None
    source_page: int
    embedding: Optional[list[float]] = None
    implementation_kind: ImplementationKind = 'agent'

class ProjectRecord(BaseModel):
    """Structured record for a client project extracted from the solutions PDF."""
    id: str = ''
    name: str
    client: str = ''
    vertical: Vertical = 'Other'
    business_problem: str = ''
    solution_summary: str = ''
    agents_used: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)
    outcomes: Optional[str] = None
    source_page: int


# ========================================================================
# schemas/extraction_output.py
# ========================================================================


"""Models for LLM extraction pipeline output."""
from typing import Optional
from pydantic import BaseModel, Field

class ExtractionOutput(BaseModel):
    """Result of extracting project and agent records from a single chunk."""
    project: Optional[ProjectRecord] = None
    agents: list[AgentRecord] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


# ========================================================================
# schemas/architecture_spec.py
# ========================================================================


"""Target architecture specification filled by the Phase 2 requirements interview."""
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field
SpecStatus = Literal['draft', 'sufficient', 'ready']
ChatPhase = Literal['open', 'workflow']
FieldSource = Literal['problem_statement', 'user_answer', 'inferred']

class FieldStatus(str, Enum):
    """Whether a spec field has a confirmed value."""
    PENDING = 'pending'
    KNOWN = 'known'
REQUIREMENTS_FIELD_DEFINITIONS: list[tuple[str, str]] = [('use_case', 'Main goal'), ('data_volume', 'How much data'), ('accuracy_target', 'How accurate it must be'), ('hitl_behavior', 'When someone should review results'), ('integrations', 'Where data comes from and goes'), ('latency_target', 'How fast answers are needed'), ('model_preference', 'AI preference'), ('deployment_platform', 'Where it should run')]
ARCHITECTURE_FIELD_DEFINITIONS: list[tuple[str, str]] = [('architectural_flow', 'Order of steps in your process'), ('architectural_flow_feedback', 'Check the steps we understood'), ('architectural_pattern', 'Overall approach'), ('core_components', 'Main parts you need'), ('data_flow', 'Where information comes from and goes'), ('orchestration_model', 'How steps run (one-by-one or together)'), ('scalability_constraints', 'How many people use it at once')]
REQUIREMENTS_FIELD_ORDER: tuple[str, ...] = tuple((k for k, _ in REQUIREMENTS_FIELD_DEFINITIONS))
ARCHITECTURE_FIELD_ORDER: tuple[str, ...] = tuple((k for k, _ in ARCHITECTURE_FIELD_DEFINITIONS))
USER_INTERVIEW_REQUIREMENT_KEYS: tuple[str, ...] = ('hitl_behavior', 'integrations')
INFERRED_REQUIREMENT_KEYS: tuple[str, ...] = tuple((k for k, _ in REQUIREMENTS_FIELD_DEFINITIONS if k not in USER_INTERVIEW_REQUIREMENT_KEYS))
USER_INTERVIEW_ARCHITECTURE_KEYS: tuple[str, ...] = ('architectural_flow', 'data_flow', 'core_components', 'orchestration_model')
INFERRED_ARCHITECTURE_KEYS: tuple[str, ...] = tuple((k for k, _ in ARCHITECTURE_FIELD_DEFINITIONS if k not in USER_INTERVIEW_ARCHITECTURE_KEYS))
USER_INTERVIEW_FIELD_KEYS: tuple[str, ...] = USER_INTERVIEW_REQUIREMENT_KEYS + USER_INTERVIEW_ARCHITECTURE_KEYS
CORE_REQUIREMENTS_BEFORE_ARCHITECTURE: tuple[str, ...] = USER_INTERVIEW_REQUIREMENT_KEYS
SUFFICIENT_REQUIREMENT_KEYS: tuple[str, ...] = USER_INTERVIEW_REQUIREMENT_KEYS
SPEC_FIELD_DEFINITIONS: list[tuple[str, str]] = REQUIREMENTS_FIELD_DEFINITIONS + ARCHITECTURE_FIELD_DEFINITIONS
_label_by_key = dict(SPEC_FIELD_DEFINITIONS)
USER_INTERVIEW_FIELD_LABELS: dict[str, str] = {k: _label_by_key[k] for k in USER_INTERVIEW_FIELD_KEYS}
REQUIRED_FIELD_KEYS: tuple[str, ...] = tuple((k for k, _ in SPEC_FIELD_DEFINITIONS))
FIELD_GROUPS: dict[str, list[str]] = {'requirements': [k for k, _ in REQUIREMENTS_FIELD_DEFINITIONS], 'architecture': [k for k, _ in ARCHITECTURE_FIELD_DEFINITIONS]}

class CatalogHint(BaseModel):
    """Similar agent from Phase 1 catalog (grounded in data/spec.json)."""
    agent_id: str
    name: str
    category: str = ''
    origin_client: str = ''
    function_summary: str = ''
    score: float = 0.0
    origin_project: str = ''
    integrations: str = ''
    model_used: str = ''
    status: str = 'available'

class GraphNode(BaseModel):
    """Draft node for Phase 3 canvas."""
    id: str
    label: str
    type: Literal['agent', 'custom', 'gateway', 'human'] = 'custom'
    agent_id: Optional[str] = None
    description: Optional[str] = None
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)

class GraphEdge(BaseModel):
    """Draft edge for Phase 3 canvas."""
    from_id: str
    to_id: str
    label: Optional[str] = None

class GraphDraft(BaseModel):
    """Structured graph emitted with the architecture blueprint."""
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)

class SpecField(BaseModel):
    """One slot in the architecture specification form."""
    key: str
    label: str
    value: Optional[str] = None
    status: FieldStatus = FieldStatus.PENDING
    notes: Optional[str] = None
    source: Optional[FieldSource] = None
    confidence: Optional[float] = None

    @property
    def is_known(self) -> bool:
        return self.status == FieldStatus.KNOWN and bool(self.value and self.value.strip())

class ArchitectureSpec(BaseModel):
    """
    Single source of truth for requirements and architecture flow gathered in Phase 2.

    Passed as JSON into every LLM prompt; the chat transcript is auxiliary context only.
    """
    status: SpecStatus = 'draft'
    problem_statement: str = ''
    fields: dict[str, SpecField] = Field(default_factory=dict)
    transcript_summary: str = ''
    catalog_hints: list[CatalogHint] = Field(default_factory=list)
    architecture_blueprint: Optional[str] = None
    graph_draft: Optional[GraphDraft] = None

    @classmethod
    def empty(cls, problem_statement: str='') -> ArchitectureSpec:
        """Create a spec with all target fields in pending state."""
        fields = {key: SpecField(key=key, label=label) for key, label in SPEC_FIELD_DEFINITIONS}
        return cls(problem_statement=problem_statement.strip(), fields=fields)

    def pending_field_keys(self) -> list[str]:
        """Return keys still missing a confirmed value, in definition order."""
        return [key for key in REQUIRED_FIELD_KEYS if not self.fields[key].is_known]

    def pending_architecture_keys(self) -> list[str]:
        return [key for key in FIELD_GROUPS['architecture'] if key in self.fields and (not self.fields[key].is_known)]

    def pending_requirements_keys(self) -> list[str]:
        return [key for key in FIELD_GROUPS['requirements'] if key in self.fields and (not self.fields[key].is_known)]

    def pending_core_requirements_keys(self) -> list[str]:
        """User-facing requirements that must be answered before architecture questions."""
        return [key for key in CORE_REQUIREMENTS_BEFORE_ARCHITECTURE if key in self.fields and (not self.fields[key].is_known)]

    def pending_user_interview_keys(self) -> list[str]:
        """Fields the chatbot may ask (excludes latency, accuracy, etc.)."""
        return [key for key in USER_INTERVIEW_FIELD_KEYS if key in self.fields and (not self.fields[key].is_known)]

    def core_requirements_complete(self) -> bool:
        return not self.pending_core_requirements_keys()

    def user_interview_complete(self) -> bool:
        return not self.pending_user_interview_keys()

    def known_count(self) -> int:
        return sum((1 for key in REQUIRED_FIELD_KEYS if self.fields[key].is_known))

    def total_required(self) -> int:
        return len(REQUIRED_FIELD_KEYS)

    def recompute_status(self) -> None:
        """Ready when user-facing interview topics are filled (often after LLM wrap-up)."""
        if self.user_interview_complete():
            self.status = 'ready'
        else:
            self.status = 'draft'

    def apply_field_updates(self, updates: dict[str, dict]) -> None:
        """
        Merge LLM field updates into the spec.

        Each update entry may include: value, status (pending|known), notes.
        """
        for key, patch in updates.items():
            if key not in self.fields:
                continue
            field = self.fields[key]
            if 'value' in patch and patch['value'] is not None:
                value = str(patch['value']).strip()
                if value:
                    field.value = value
            if patch.get('status') == 'known' or patch.get('status') == FieldStatus.KNOWN:
                field.status = FieldStatus.KNOWN
            elif patch.get('status') == 'pending' or patch.get('status') == FieldStatus.PENDING:
                field.status = FieldStatus.PENDING
            if patch.get('notes'):
                field.notes = str(patch['notes']).strip() or None
            if patch.get('source') in ('problem_statement', 'user_answer', 'inferred'):
                field.source = patch['source']
            if patch.get('confidence') is not None:
                try:
                    field.confidence = float(patch['confidence'])
                except (TypeError, ValueError):
                    pass
        self.recompute_status()

    def compact_known_json(self) -> dict:
        """Known fields only — for smaller LLM prompts."""
        return {key: {'value': self.fields[key].value, 'status': self.fields[key].status.value, 'source': self.fields[key].source} for key in REQUIRED_FIELD_KEYS if self.fields[key].is_known}

class ChatMessage(BaseModel):
    """One message in the interview transcript (UI + audit trail)."""
    role: Literal['assistant', 'user']
    content: str
    field_key: Optional[str] = None

class ClarifyingQuestionItem(BaseModel):
    """Pre-interview question before agents or architecture are suggested."""
    id: str
    question: str
    why_it_matters: str = ''

class InterviewQuestion(BaseModel):
    """Assistant turn: one focused question with chip options."""
    field_key: str
    'Plain label for the single topic this turn is about (shown in UI).'
    topic_label: Optional[str] = None
    question: str
    chips: list[str] = Field(default_factory=list)
    why_it_matters: Optional[str] = None
    'Closest catalog-backed chip (usually chips[0] after merge).'
    suggested_chip: Optional[str] = None
    catalog_reference: Optional[str] = None
    suggestion_reason: Optional[str] = None

class InterviewSession(BaseModel):
    """Full server state for one requirements interview."""
    id: str
    spec: ArchitectureSpec
    messages: list[ChatMessage] = Field(default_factory=list)
    pending_question: Optional[InterviewQuestion] = None
    last_answered_field: Optional[str] = None
    architecture_plan: Optional['ArchitecturePlan'] = None
    clarifying_questions: list[ClarifyingQuestionItem] = Field(default_factory=list)
    clarifying_answers: dict[str, str] = Field(default_factory=dict)
    agent_workflow: Optional['AgentWorkflowState'] = None
    awaiting_problem_revision: bool = False
    'open = ChatGPT-style chat; workflow = scoping interview + builder.'
    chat_phase: Optional[ChatPhase] = None
    discovery: Optional['DiscoveryState'] = None
InterviewSession.model_rebuild()


# ========================================================================
# services/answer_utils.py
# ========================================================================


"""Helpers for validating interview answers."""
import re
_CUSTOM_DESCRIBE_PATTERNS = (re.compile('^other\\s*/\\s*describe', re.I), re.compile('other.*describe.*chat', re.I), re.compile('^other\\s*$', re.I), re.compile('^describe\\s+in\\s+chat$', re.I))

def is_custom_describe_placeholder(answer: str) -> bool:
    """True if the answer is only the 'Other / describe' chip text, not a real description."""
    text = answer.strip()
    if not text:
        return True
    if len(text) > 48:
        return False
    for pat in _CUSTOM_DESCRIBE_PATTERNS:
        if pat.search(text):
            return True
    return False


# ========================================================================
# services/agent_kind.py
# ========================================================================


"""Classify catalog entries as agent, function, or tool for UI labeling."""
from typing import Literal
ImplementationKind = Literal['agent', 'function', 'tool']

def classify_implementation_kind(agent: AgentRecord) -> ImplementationKind:
    """
    Infer how a catalog step is implemented:

    - agent: multi-agent chains or LLM-orchestrated modules
    - function: single LLM callable (llm_functions.py style)
    - tool: deterministic services, CV models, indexes, API wrappers
    """
    notes = (agent.notes or '').lower()
    tech_blob = ' '.join(agent.tech_stack).lower()
    name = agent.name.lower()
    summary = agent.function_summary.lower()
    blob = f'{notes} {tech_blob} {name} {summary}'
    if 'agents:' in notes or 'agent chain' in name or 'autogen' in tech_blob:
        return 'agent'
    if 'llm_functions' in tech_blob or 'llm_functions' in notes:
        return 'function'
    if any((token in notes for token in ('count_function', 'generic_function', 'final_answer_function', 'daily_kpi'))):
        return 'function'
    if ' agent' in name or name.endswith(' agent') or ' chain' in name:
        if 'llm_functions' not in tech_blob:
            return 'agent'
    tool_markers = ('roboflow', 'detect_crop.py', 'yolo', 'catboost', 'scikit-learn', 'sklearn', 'images/edits', 'videos api', 'azure-search-documents', 'semantic.py', 'competitive_scoring.py', 'not a trained ml model', 'sql_tool')
    if any((marker in blob for marker in tool_markers)):
        return 'tool'
    if 'python-docx' in tech_blob and 'azure openai' not in tech_blob:
        return 'tool'
    if any((phrase in name for phrase in ('embedder', 'vector retrieval', 'semantic search', 'row detector', 'product detector', 'simulator', 'stub', 'analysis engine'))):
        return 'tool'
    if 'deterministic' in blob and 'azure openai' not in tech_blob:
        return 'tool'
    if 'azure openai' in tech_blob or 'graphrag' in tech_blob or 'google-genai' in tech_blob:
        return 'agent'
    if 'python' in tech_blob and 'openai' not in tech_blob and ('genai' not in tech_blob):
        return 'tool'
    return 'agent'


# ========================================================================
# services/spec_validators.py
# ========================================================================


"""Deterministic validation for ArchitectureSpec fields after LLM updates."""
import re
from typing import Optional
_LATENCY_PATTERN = re.compile('(\\d+\\s*(ms|sec|secs|second|seconds|s|min|minutes|hour|hours|h)\\b|real[- ]?time|batch|near[- ]?real[- ]?time)', re.IGNORECASE)
_ACCURACY_PATTERN = re.compile('(\\d+\\s*%|high|medium|low|strict|lenient)', re.IGNORECASE)

def validate_field_value(field_key: str, value: Optional[str]) -> list[str]:
    """
    Return validation warnings for a field value (empty list = acceptable).

    Warnings do not block known status but are stored in field notes for the UI.
    """
    if not value or not value.strip():
        return ['Value is empty']
    text = value.strip()
    warnings: list[str] = []
    if field_key == 'latency_target' and (not _LATENCY_PATTERN.search(text)):
        warnings.append("Specify a latency target (e.g. '<2s', 'batch nightly', 'real-time').")
    if field_key == 'accuracy_target' and (not _ACCURACY_PATTERN.search(text)):
        warnings.append("Specify accuracy (e.g. '96%', 'high precision').")
    if field_key == 'data_volume' and len(text) < 8:
        warnings.append('Add scale detail (e.g. documents/day, concurrent users).')
    if field_key == 'integrations' and len(text) < 3:
        warnings.append('Name at least one external system or API.')
    if field_key in ('architectural_flow', 'architectural_flow_feedback', 'data_flow'):
        if len(text) < 40:
            warnings.append('Flow description is very short — add steps or components.')
    return warnings

def apply_validators(spec: ArchitectureSpec) -> list[str]:
    """
    Run validators on all known fields; append warnings to notes.

    Returns:
        List of human-readable warning messages for logging.
    """
    log_warnings: list[str] = []
    for key, field in spec.fields.items():
        if not field.is_known or not field.value:
            continue
        for msg in validate_field_value(key, field.value):
            note = f'Validator: {msg}'
            field.notes = f'{field.notes} | {note}' if field.notes else note
            log_warnings.append(f'{key}: {msg}')
    _validate_dependencies(spec, log_warnings)
    return log_warnings

def _validate_dependencies(spec: ArchitectureSpec, log_warnings: list[str]) -> None:
    """Cross-field rules (logged only)."""
    hitl = spec.fields.get('hitl_behavior')
    integrations = spec.fields.get('integrations')
    if hitl and hitl.is_known and hitl.value:
        if 'approval' in hitl.value.lower() or 'human' in hitl.value.lower():
            if integrations and integrations.is_known:
                if integrations.value and 'email' not in integrations.value.lower():
                    if 'ui' not in integrations.value.lower() and 'portal' not in integrations.value.lower():
                        log_warnings.append('hitl_behavior: HITL mentioned but integrations may need email/UI.')
    pattern = spec.fields.get('architectural_pattern')
    data_flow = spec.fields.get('data_flow')
    if pattern and pattern.is_known and pattern.value:
        pl = pattern.value.lower()
        if 'graphrag' in pl or 'rag' in pl:
            if data_flow and data_flow.is_known and data_flow.value:
                if 'index' not in data_flow.value.lower() and 'vector' not in data_flow.value.lower():
                    log_warnings.append('data_flow: RAG/GraphRAG pattern usually needs indexing/vector store in data_flow.')


# ========================================================================
# services/llm.py
# ========================================================================


"""Shared Azure OpenAI chat helpers for pipeline and interview services."""
import logging
import time
from pathlib import Path
from openai import APIError, APITimeoutError, AzureOpenAI, RateLimitError
logger = logging.getLogger(__name__)
PROMPTS_DIR = BACKEND_ROOT / 'prompts'
MAX_RETRIES = 3
BACKOFF_SECONDS = (2, 4, 8)

def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    text = (PROMPTS_DIR / filename).read_text(encoding='utf-8')
    return _expand_prompt_includes(text)

def _expand_prompt_includes(text: str, *, _depth: int=0) -> str:
    """Inline {{partial.txt}} includes (one level, no recursion into partials)."""
    if _depth > 2:
        return text
    import re
    pattern = re.compile('\\{\\{([a-zA-Z0-9_.-]+\\.txt)\\}\\}')

    def _replace(match: re.Match[str]) -> str:
        include_name = match.group(1)
        include_path = PROMPTS_DIR / include_name
        if not include_path.is_file():
            logger.warning('Prompt include not found: %s', include_name)
            return match.group(0)
        return include_path.read_text(encoding='utf-8').strip()
    expanded = pattern.sub(_replace, text)
    if pattern.search(expanded):
        return _expand_prompt_includes(expanded, _depth=_depth + 1)
    return expanded

def strip_json_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped JSON in them."""
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines)
    return text.strip()

def call_llm(client: AzureOpenAI, settings: Settings, system_prompt: str, user_message: str, *, temperature: float=0.1, json_mode: bool=False) -> str:
    """
    Call Azure OpenAI chat completion with retry and exponential backoff.

    Raises the last exception after MAX_RETRIES failures.
    """
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            kwargs: dict = {'model': settings.azure_openai_chat_deployment, 'messages': [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_message}], 'temperature': temperature}
            if json_mode:
                kwargs['response_format'] = {'type': 'json_object'}
            response = client.chat.completions.create(**kwargs)
            content = response.choices[0].message.content
            if not content:
                raise ValueError('Empty response from chat completion')
            return content
        except (RateLimitError, APITimeoutError, APIError) as exc:
            last_error = exc
            wait = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
            logger.warning('API error (attempt %d/%d): %s — retrying in %ds', attempt + 1, MAX_RETRIES, exc, wait)
            time.sleep(wait)
    raise last_error or RuntimeError('LLM call failed after retries')

def make_client(settings: Settings) -> AzureOpenAI:
    """Build an Azure OpenAI client from settings."""
    return AzureOpenAI(azure_endpoint=settings.azure_openai_endpoint, api_key=settings.azure_openai_api_key, api_version=settings.azure_openai_api_version)


# ========================================================================
# pipeline/spec_loader.py
# ========================================================================


"""Load pre-structured catalog JSON (no LLM extraction or chunking)."""
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from pydantic import ValidationError
logger = logging.getLogger(__name__)

@dataclass
class CatalogLoadResult:
    """Agents and projects loaded from a catalog JSON file."""
    projects: list[ProjectRecord] = field(default_factory=list)
    agents: list[AgentRecord] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def project(self) -> ProjectRecord | None:
        """First project, for backward-compatible callers."""
        return self.projects[0] if self.projects else None

def _parse_project(raw: dict, source_page: int=1) -> ProjectRecord:
    name = raw.get('name') or 'unknown-project'
    return ProjectRecord(id=slugify(name), name=name, client=raw.get('client') or '', vertical=normalize_vertical(raw.get('vertical')), business_problem=raw.get('business_problem') or '', solution_summary=raw.get('solution_summary') or '', agents_used=raw.get('agents_used') or [], tech_stack=raw.get('tech_stack') or [], outcomes=raw.get('outcomes'), source_page=source_page)

def _parse_agent(item: dict, source_page: int=1) -> AgentRecord:
    name = item.get('name') or 'unknown-agent'
    version = item.get('version') or '1.0'
    agent_id = slugify(name)
    if version and version != '1.0':
        agent_id = f"{agent_id}-v{version.replace('.', '-')}"
    raw_kind = (item.get('implementation_kind') or '').strip().lower()
    implementation_kind = raw_kind if raw_kind in ('agent', 'function', 'tool') else None
    record = AgentRecord(id=agent_id, name=name, version=version, category=item['category'], function_summary=item.get('function_summary') or '', inputs=item.get('inputs') or [], outputs=item.get('outputs') or [], model_used=item.get('model_used') or 'Unknown', tech_stack=item.get('tech_stack') or [], integrations=item.get('integrations') or [], origin_project=item.get('origin_project') or '', origin_client=item.get('origin_client') or '', vertical=normalize_vertical(item.get('vertical')), status=item.get('status') or 'available', typical_accuracy=item.get('typical_accuracy'), notes=item.get('notes'), source_page=int(item.get('source_page', source_page)), implementation_kind=implementation_kind or 'agent')
    if not implementation_kind:
        record = record.model_copy(update={'implementation_kind': classify_implementation_kind(record)})
    return record

def _normalize_entries(data: object) -> list[dict]:
    """
    Accept catalog JSON as either:

    - Array of ``{ "project": {...}, "agents": [...] }`` (multi-project catalog)
    - Single object ``{ "project": {...}, "agents": [...] }`` (legacy)
    """
    if isinstance(data, list):
        entries = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ValueError(f'Catalog entry[{i}] must be an object')
            entries.append(item)
        return entries
    if isinstance(data, dict):
        if 'agents' in data or 'project' in data:
            return [data]
        raise ValueError("Catalog JSON object must include 'agents' and/or 'project' keys")
    raise ValueError('Catalog JSON must be a top-level array of project entries or a single object')

def _ensure_unique_agent_ids(agents: list[AgentRecord]) -> list[AgentRecord]:
    """Disambiguate duplicate slugs across projects (same agent name in multiple entries)."""
    used: set[str] = set()
    result: list[AgentRecord] = []
    for agent in agents:
        agent_id = agent.id
        if agent_id not in used:
            used.add(agent_id)
            result.append(agent)
            continue
        suffix = slugify(agent.origin_project or agent.origin_client or 'project')
        disambiguated = f'{agent_id}-{suffix}'
        counter = 2
        while disambiguated in used:
            disambiguated = f'{agent_id}-{suffix}-{counter}'
            counter += 1
        used.add(disambiguated)
        logger.info('Disambiguated agent id %s → %s (project %s)', agent_id, disambiguated, agent.origin_project)
        result.append(agent.model_copy(update={'id': disambiguated}))
    return result

def _load_entry(entry: dict, entry_index: int) -> tuple[ProjectRecord | None, list[AgentRecord], list[str]]:
    """Load one project + agents block from the catalog."""
    errors: list[str] = []
    project: ProjectRecord | None = None
    source_page = entry_index + 1
    if isinstance(entry.get('project'), dict):
        try:
            project = _parse_project(entry['project'], source_page=source_page)
        except (ValidationError, KeyError) as exc:
            errors.append(f'entry[{entry_index}].project: {exc}')
    agents: list[AgentRecord] = []
    raw_agents = entry.get('agents')
    if raw_agents is None:
        errors.append(f"entry[{entry_index}]: missing 'agents' array")
        return (project, agents, errors)
    if not isinstance(raw_agents, list):
        errors.append(f'entry[{entry_index}].agents: must be an array')
        return (project, agents, errors)
    for i, item in enumerate(raw_agents):
        if not isinstance(item, dict):
            continue
        try:
            agents.append(_parse_agent(item, source_page=source_page))
        except (ValidationError, KeyError) as exc:
            errors.append(f'entry[{entry_index}].agents[{i}]: {exc}')
    return (project, agents, errors)

def load_catalog_json(path: str | Path) -> CatalogLoadResult:
    """
    Load all projects and agents from a catalog JSON file.

    Supports:
    - Multi-project: ``[ { "project": {...}, "agents": [...] }, ... ]``
    - Legacy single: ``{ "project": {...}, "agents": [...] }``

    Raises:
        FileNotFoundError, json.JSONDecodeError, ValueError
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f'Catalog file not found: {file_path}')
    data = json.loads(file_path.read_text(encoding='utf-8'))
    entries = _normalize_entries(data)
    projects: list[ProjectRecord] = []
    all_agents: list[AgentRecord] = []
    all_errors: list[str] = []
    for idx, entry in enumerate(entries):
        project, agents, errors = _load_entry(entry, idx)
        all_errors.extend(errors)
        if project:
            projects.append(project)
        all_agents.extend(agents)
    if not all_agents:
        raise ValueError('Catalog JSON contains no valid agents')
    unique_agents = _ensure_unique_agent_ids(all_agents)
    if all_errors:
        logger.warning('Skipped %d catalog parse issue(s): %s', len(all_errors), all_errors[:5])
    logger.info('Loaded catalog from %s: %d project(s), %d agent(s)', file_path.name, len(projects), len(unique_agents))
    return CatalogLoadResult(projects=projects, agents=unique_agents, errors=all_errors)

def load_catalog_json_legacy(path: str | Path) -> tuple[ProjectRecord | None, list[AgentRecord]]:
    """
    Backward-compatible loader returning (first_project, all_agents).

    Prefer :func:`load_catalog_json` for multi-project catalogs.
    """
    result = load_catalog_json(path)
    return (result.project, result.agents)


# ========================================================================
# services/data_storage.py
# ========================================================================


"""Persist launchpad JSON under local disk or Azure Blob Storage."""
import json
import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Optional
logger = logging.getLogger(__name__)
BLOB_PREFIX = 'launchpad'
LOCAL_ROOT = BACKEND_ROOT / 'data' / 'blob_mirror'

class DataStorage(ABC):

    @abstractmethod
    def read_json(self, key: str) -> Optional[dict[str, Any]]:
        ...

    @abstractmethod
    def write_json(self, key: str, payload: dict[str, Any]) -> None:
        ...

    @abstractmethod
    def delete(self, key: str) -> bool:
        ...

    @abstractmethod
    def list_keys(self, prefix: str) -> list[str]:
        ...

    def list_keys_by_mtime(self, prefix: str, *, newest_first: bool=True) -> list[str]:
        """List JSON object keys under prefix, ordered by last modified time."""
        pairs = self.list_keys_with_mtime(prefix, newest_first=newest_first)
        return [key for key, _ in pairs]

    def list_keys_with_mtime(self, prefix: str, *, newest_first: bool=True) -> list[tuple[str, datetime]]:
        """List keys under prefix with UTC last-modified timestamps."""
        keys = self.list_keys(prefix)
        now = datetime.now(timezone.utc)
        pairs = [(k, now) for k in keys]
        pairs.sort(key=lambda pair: pair[1], reverse=newest_first)
        return pairs

def _safe_key(key: str) -> str:
    cleaned = key.replace('\\', '/').strip('/')
    if '..' in cleaned.split('/'):
        raise ValueError(f'Invalid storage key: {key}')
    return cleaned

class LocalDataStorage(DataStorage):

    def __init__(self, root: Path | None=None) -> None:
        self._root = root or LOCAL_ROOT

    def _path(self, key: str) -> Path:
        return self._root / _safe_key(key)

    def read_json(self, key: str) -> Optional[dict[str, Any]]:
        path = self._path(key)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning('Could not read %s: %s', path, exc)
            return None

    def write_json(self, key: str, payload: dict[str, Any]) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding='utf-8')

    def delete(self, key: str) -> bool:
        path = self._path(key)
        if not path.is_file():
            return False
        try:
            path.unlink()
            return True
        except OSError as exc:
            logger.warning('Could not delete %s: %s', path, exc)
            return False

    def list_keys(self, prefix: str) -> list[str]:
        return self.list_keys_by_mtime(prefix, newest_first=False)

    def list_keys_with_mtime(self, prefix: str, *, newest_first: bool=True) -> list[tuple[str, datetime]]:
        base = self._path(prefix)
        if not base.exists():
            return []
        if base.is_file():
            try:
                ts = datetime.fromtimestamp(base.stat().st_mtime, tz=timezone.utc)
            except OSError:
                ts = datetime.min.replace(tzinfo=timezone.utc)
            return [(_safe_key(prefix), ts)]
        items: list[tuple[str, datetime]] = []
        for path in base.rglob('*.json'):
            rel = path.relative_to(self._root).as_posix()
            try:
                ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
            except OSError:
                ts = datetime.min.replace(tzinfo=timezone.utc)
            items.append((rel, ts))
        items.sort(key=lambda pair: pair[1], reverse=newest_first)
        return items

class AzureBlobDataStorage(DataStorage):

    def __init__(self, *, account_name: str, container_name: str, connection_string: str='', account_key: str='') -> None:
        from azure.core.exceptions import ResourceNotFoundError
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient
        self._missing = ResourceNotFoundError
        account_url = f'https://{account_name}.blob.core.windows.net'
        if connection_string:
            service = BlobServiceClient.from_connection_string(connection_string)
        elif account_key:
            service = BlobServiceClient(account_url=account_url, credential=account_key)
        else:
            service = BlobServiceClient(account_url=account_url, credential=DefaultAzureCredential())
        self._container = service.get_container_client(container_name)
        self._prefix = BLOB_PREFIX.strip('/')

    def _blob_name(self, key: str) -> str:
        rel = _safe_key(key)
        return f'{self._prefix}/{rel}' if self._prefix else rel

    def read_json(self, key: str) -> Optional[dict[str, Any]]:
        blob = self._container.get_blob_client(self._blob_name(key))
        try:
            raw = blob.download_blob().readall().decode('utf-8')
            return json.loads(raw)
        except self._missing:
            return None
        except Exception as exc:
            logger.warning('Could not read blob %s: %s', key, exc)
            return None

    def write_json(self, key: str, payload: dict[str, Any]) -> None:
        blob = self._container.get_blob_client(self._blob_name(key))
        body = json.dumps(payload, indent=2)
        blob.upload_blob(body, overwrite=True)

    def delete(self, key: str) -> bool:
        blob = self._container.get_blob_client(self._blob_name(key))
        try:
            blob.delete_blob()
            return True
        except self._missing:
            return False
        except OSError as exc:
            logger.warning('Could not delete blob %s: %s', key, exc)
            return False

    def list_keys(self, prefix: str) -> list[str]:
        return self.list_keys_by_mtime(prefix, newest_first=False)

    def list_keys_with_mtime(self, prefix: str, *, newest_first: bool=True) -> list[tuple[str, datetime]]:
        blob_prefix = self._blob_name(prefix).rstrip('/') + '/'
        items: list[tuple[str, datetime]] = []
        try:
            blobs = self._container.list_blobs(name_starts_with=blob_prefix)
        except Exception as exc:
            logger.warning('Could not list blobs under %s: %s', prefix, exc)
            return []
        for item in blobs:
            name = item.name
            if not name.endswith('.json'):
                continue
            if self._prefix and name.startswith(f'{self._prefix}/'):
                name = name[len(self._prefix) + 1:]
            modified = item.last_modified
            if modified is None:
                modified = datetime.min.replace(tzinfo=timezone.utc)
            elif modified.tzinfo is None:
                modified = modified.replace(tzinfo=timezone.utc)
            items.append((name, modified))
        items.sort(key=lambda pair: pair[1], reverse=newest_first)
        return items
_storage: DataStorage | None = None

def blob_storage_configured() -> bool:
    backend = os.getenv('DATA_STORAGE_BACKEND', 'auto').strip().lower()
    if backend == 'local':
        return False
    account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME', '').strip()
    conn = os.getenv('AZURE_STORAGE_CONNECTION_STRING', '').strip()
    if backend == 'blob':
        return bool(conn or account)
    return bool(conn or account)

def get_data_storage() -> DataStorage:
    global _storage
    if _storage is not None:
        return _storage
    if blob_storage_configured():
        account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME', 'affineblog').strip()
        container = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'agentic-launchpad').strip()
        _storage = AzureBlobDataStorage(account_name=account, container_name=container, connection_string=os.getenv('AZURE_STORAGE_CONNECTION_STRING', '').strip(), account_key=os.getenv('AZURE_STORAGE_ACCOUNT_KEY', '').strip())
        logger.info('Data storage: Azure Blob account=%s container=%s prefix=%s', account, container, BLOB_PREFIX)
    else:
        _storage = LocalDataStorage()
        logger.info('Data storage: local mirror at %s', LOCAL_ROOT)
    return _storage

def storage_backend_name() -> str:
    return 'azure_blob' if blob_storage_configured() else 'local'

def get_storage_status() -> dict[str, str | bool | int]:
    """Summary for /health and startup logs."""
    if not blob_storage_configured():
        return {'backend': 'local', 'path': str(LOCAL_ROOT), 'reachable': LOCAL_ROOT.exists()}
    account = os.getenv('AZURE_STORAGE_ACCOUNT_NAME', 'affineblog').strip()
    container = os.getenv('AZURE_STORAGE_CONTAINER_NAME', 'agentic-launchpad').strip()
    status: dict[str, str | bool | int] = {'backend': 'azure_blob', 'account': account, 'container': container, 'prefix': BLOB_PREFIX, 'reachable': False}
    try:
        storage = get_data_storage()
        keys = storage.list_keys('sessions')
        status['reachable'] = True
        session_keys = [k for k in keys if k.startswith('sessions/') and k.endswith('.json')]
        workflow_keys = [k for k in storage.list_keys('workflows') if k.startswith('workflows/') and k.endswith('.json') and (not k.endswith('/_index.json'))]
        status['session_blob_count'] = len(session_keys)
        status['workflow_blob_count'] = len(workflow_keys)
    except Exception as exc:
        status['error'] = str(exc)[:200]
        logger.warning('Azure Blob storage check failed: %s', exc)
    return status

def reset_data_storage_for_tests() -> None:
    global _storage
    _storage = None


# ========================================================================
# services/graph_sanitizer.py
# ========================================================================


"""Normalize and repair architecture flow graphs before Phase 3 / canvas render."""
import re
from collections import defaultdict, deque
_NODE_ID_RE = re.compile('^[a-z0-9]+(?:-[a-z0-9]+)*$')

def normalize_node_id(raw: str) -> str:
    text = raw.lower().strip()
    text = re.sub('[^\\w\\s-]', '', text)
    text = re.sub('[\\s_]+', '-', text)
    text = text.strip('-') or 'node'
    if not _NODE_ID_RE.match(text):
        text = re.sub('-+', '-', text).strip('-') or 'node'
    return text

def _dedupe_nodes(nodes: list[GraphNode]) -> list[GraphNode]:
    seen: dict[str, GraphNode] = {}
    for node in nodes:
        nid = normalize_node_id(node.id)
        if nid in seen:
            existing = seen[nid]
            if not existing.label and node.label:
                seen[nid] = node.model_copy(update={'id': nid})
            continue
        seen[nid] = node.model_copy(update={'id': nid})
    return list(seen.values())

def _dedupe_edges(edges: list[GraphEdge]) -> list[GraphEdge]:
    seen: set[tuple[str, str]] = set()
    out: list[GraphEdge] = []
    for edge in edges:
        key = (edge.from_id, edge.to_id)
        if key in seen or edge.from_id == edge.to_id:
            continue
        seen.add(key)
        out.append(edge)
    return out

def _topo_order(node_ids: list[str], edges: list[GraphEdge]) -> list[str]:
    """Kahn topological sort; on cycles, break by dropping backward edges first."""
    ids = list(node_ids)
    if not ids:
        return []
    indegree = {nid: 0 for nid in ids}
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        if edge.from_id not in indegree or edge.to_id not in indegree:
            continue
        adj[edge.from_id].append(edge.to_id)
        indegree[edge.to_id] += 1
    queue = deque([nid for nid in ids if indegree[nid] == 0])
    order: list[str] = []
    while queue:
        nid = queue.popleft()
        order.append(nid)
        for nxt in adj[nid]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    if len(order) == len(ids):
        return order
    index = {nid: i for i, nid in enumerate(ids)}
    forward = [e for e in edges if index.get(e.from_id, 0) < index.get(e.to_id, 0)]
    return _topo_order(ids, forward) if forward != edges else ids

def _filter_forward_edges(node_ids: list[str], edges: list[GraphEdge]) -> list[GraphEdge]:
    order = _topo_order(node_ids, edges)
    rank = {nid: i for i, nid in enumerate(order)}
    kept: list[GraphEdge] = []
    for edge in edges:
        if edge.from_id not in rank or edge.to_id not in rank:
            continue
        if rank[edge.from_id] < rank[edge.to_id]:
            kept.append(edge)
    return kept

def _undirected_components(node_ids: list[str], edges: list[GraphEdge]) -> list[list[str]]:
    parent = {nid: nid for nid in node_ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = (find(a), find(b))
        if ra != rb:
            parent[rb] = ra
    for edge in edges:
        if edge.from_id in parent and edge.to_id in parent:
            union(edge.from_id, edge.to_id)
    groups: dict[str, list[str]] = defaultdict(list)
    for nid in node_ids:
        groups[find(nid)].append(nid)
    return list(groups.values())

def _connect_dangling_sinks(node_ids: list[str], edges: list[GraphEdge]) -> list[GraphEdge]:
    """Link orphan exit nodes into the main downstream path."""
    if len(node_ids) <= 1:
        return edges
    out_degree = {nid: 0 for nid in node_ids}
    for e in edges:
        out_degree[e.from_id] = out_degree.get(e.from_id, 0) + 1
    sinks = [nid for nid in node_ids if out_degree.get(nid, 0) == 0]
    if len(sinks) <= 1:
        return edges
    order = _topo_order(node_ids, edges)
    rank = {nid: i for i, nid in enumerate(order)}

    def sink_priority(nid: str) -> tuple[int, int]:
        label_boost = 0
        if any((x in nid for x in ('output', 'workbench', 'end', 'complete'))):
            label_boost = 1
        return (label_boost, rank.get(nid, 0))
    primary = max(sinks, key=sink_priority)
    out = list(edges)
    for sid in sinks:
        if sid != primary:
            out.append(GraphEdge(from_id=sid, to_id=primary, label='flow'))
    return _dedupe_edges(out)

def _connect_components(nodes: list[GraphNode], edges: list[GraphEdge]) -> list[GraphEdge]:
    if len(nodes) <= 1:
        return edges
    node_ids = [n.id for n in nodes]
    comps = _undirected_components(node_ids, edges)
    if len(comps) <= 1:
        return edges
    order = _topo_order(node_ids, edges)
    rank = {nid: i for i, nid in enumerate(order)}

    def comp_sort(comp: list[str]) -> int:
        return min((rank.get(nid, 9999) for nid in comp))
    comps.sort(key=comp_sort)
    out = list(edges)
    out_degree = defaultdict(int)
    in_degree = defaultdict(int)
    for e in out:
        out_degree[e.from_id] += 1
        in_degree[e.to_id] += 1
    node_by_id = {n.id: n for n in nodes}
    for i in range(len(comps) - 1):
        left = comps[i]
        right = comps[i + 1]
        if len(right) == 1:
            only = right[0]
            node = node_by_id.get(only)
            if node and _is_exit_node(node):
                continue
        sink = max(left, key=lambda nid: (out_degree[nid], -rank.get(nid, 0)))
        source = min(right, key=lambda nid: (in_degree[nid], rank.get(nid, 9999)))
        bridge = GraphEdge(from_id=sink, to_id=source, label='flow')
        if sink != source:
            out.append(bridge)
            out_degree[sink] += 1
            in_degree[source] += 1
    return _dedupe_edges(out)

def _linear_chain_if_empty(nodes: list[GraphNode]) -> list[GraphEdge]:
    if len(nodes) < 2:
        return []
    edges: list[GraphEdge] = []
    for i in range(len(nodes) - 1):
        edges.append(GraphEdge(from_id=nodes[i].id, to_id=nodes[i + 1].id, label='next'))
    return edges

def _is_exit_node(node: GraphNode) -> bool:
    blob = f"{node.id} {node.label or ''} {node.description or ''}".lower()
    return any((token in blob for token in ('workflow-end', 'copilot-response', ' final response', 'end point', 'endpoint'))) or ('end' in blob.split() or blob.strip().endswith(' end') or node.label.strip().lower() == 'end')

def _ensure_exit_node(nodes: list[GraphNode], edges: list[GraphEdge]) -> tuple[list[GraphNode], list[GraphEdge]]:
    """
    Add a terminal End node when parallel branches have no merge point.

    Common when the planner outputs gateway → Quin + Eryl without a sink.
    """
    if len(nodes) < 2:
        return (nodes, edges)
    node_ids = {n.id for n in nodes}
    out_degree = {nid: 0 for nid in node_ids}
    in_degree = {nid: 0 for nid in node_ids}
    for edge in edges:
        if edge.from_id in out_degree:
            out_degree[edge.from_id] += 1
        if edge.to_id in in_degree:
            in_degree[edge.to_id] += 1
    sinks = [nid for nid in node_ids if out_degree.get(nid, 0) == 0]
    if len(sinks) <= 1:
        return (nodes, edges)
    exit_nodes = [n for n in nodes if _is_exit_node(n)]
    if len(exit_nodes) == 1 and exit_nodes[0].id in sinks:
        target = exit_nodes[0].id
        out = list(edges)
        for sid in sinks:
            if sid == target:
                continue
            pair = (sid, target)
            if not any((e.from_id == pair[0] and e.to_id == pair[1] for e in out)):
                out.append(GraphEdge(from_id=sid, to_id=target, label='answer'))
        return (nodes, _dedupe_edges(out))
    end_id = 'workflow-end'
    if end_id in node_ids:
        end_id = 'copilot-response-end'
    end_node = GraphNode(id=end_id, label='End', type='gateway', agent_id=None, description='Final copilot response returned to the user.')
    new_nodes = list(nodes)
    if end_id not in node_ids:
        new_nodes.append(end_node)
    new_edges = list(edges)
    for sid in sinks:
        if sid == end_id:
            continue
        pair = (sid, end_id)
        if not any((e.from_id == pair[0] and e.to_id == pair[1] for e in new_edges)):
            new_edges.append(GraphEdge(from_id=sid, to_id=end_id, label='answer'))
    return (new_nodes, _dedupe_edges(new_edges))

def sanitize_graph(graph: GraphDraft) -> GraphDraft:
    """
    Repair a graph for canvas display: valid ids, forward-only edges, connected DAG.
    """
    nodes = _dedupe_nodes(graph.nodes)
    if not nodes:
        return GraphDraft(nodes=[], edges=[])
    node_ids = {n.id for n in nodes}
    edges = [GraphEdge(from_id=normalize_node_id(e.from_id), to_id=normalize_node_id(e.to_id), label=(e.label or '').strip() or None) for e in graph.edges if normalize_node_id(e.from_id) in node_ids and normalize_node_id(e.to_id) in node_ids]
    edges = _dedupe_edges(edges)
    node_ids = [n.id for n in nodes]
    edges = _filter_forward_edges(node_ids, edges)
    edges = _connect_components(nodes, edges)
    if not edges and len(nodes) >= 2:
        edges = _linear_chain_if_empty(nodes)
    nodes, edges = _ensure_exit_node(nodes, edges)
    edges = _bridge_human_gates(nodes, edges)
    node_ids = [n.id for n in nodes]
    edges = _connect_dangling_sinks(node_ids, edges)
    return GraphDraft(nodes=nodes, edges=edges)

def _is_human_node(node: GraphNode) -> bool:
    blob = f"{node.id} {node.label} {node.type or ''}".lower()
    return node.type == 'human' or any((token in blob for token in ('analyst', 'human', 'hitl', 'review')))

def _bridge_human_gates(nodes: list[GraphNode], edges: list[GraphEdge]) -> list[GraphEdge]:
    """Connect human-in-the-loop steps to the next node when the planner omits the edge."""
    if len(nodes) < 2:
        return edges
    node_ids = [n.id for n in nodes]
    order = _topo_order(node_ids, edges)
    rank = {nid: i for i, nid in enumerate(order)}
    out = list(edges)
    seen = {(e.from_id, e.to_id) for e in out}
    for node in nodes:
        if not _is_human_node(node):
            continue
        r = rank.get(node.id)
        if r is None:
            continue
        successors = [nid for nid in order if rank.get(nid, 0) > r]
        if not successors:
            continue
        nxt = successors[0]
        pair = (node.id, nxt)
        if pair in seen or pair[0] == pair[1]:
            continue
        out.append(GraphEdge(from_id=node.id, to_id=nxt, label='flow'))
        seen.add(pair)
    return _dedupe_edges(out)


# ========================================================================
# services/chip_quality.py
# ========================================================================


"""Quality gate and merge helpers for interview answer chips."""
import re
OTHER_CHIP = 'Other / describe in chat'
_TOKEN_RE = re.compile('[a-z0-9]{3,}')
MIN_CHIP_WORDS = 2
MAX_CHIP_CHARS = 160
MIN_MERGED_CHIPS = 2
JACCARD_DUPLICATE_THRESHOLD = 0.72

def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or '').lower()))

def _word_count(text: str) -> int:
    return len([w for w in (text or '').split() if w.strip()])

def jaccard_similarity(a: str, b: str) -> float:
    ta, tb = (_tokens(a), _tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)

def is_other_chip(chip: str) -> bool:
    return chip.strip().lower() == OTHER_CHIP.lower()

def normalize_chip_text(chip: str) -> str:
    return ' '.join((chip or '').split())

def chip_passes_quality_gate(chip: str, *, input_name: str='', agent_summary: str='', min_words: int=MIN_CHIP_WORDS, catalog_sourced: bool=False) -> bool:
    text = normalize_chip_text(chip)
    if not text or is_other_chip(text):
        return False
    if len(text) > MAX_CHIP_CHARS:
        return False
    if catalog_sourced:
        return len(text) >= 2
    if _word_count(text) < min_words:
        return False
    domain = _tokens(f'{input_name} {agent_summary}')
    chip_t = _tokens(text)
    if domain and chip_t and (not domain & chip_t):
        if not any((w in text.lower() for w in ('use ', 'send ', 'upload', 'review', 'default', 'manual', 'azure', 'bytes', 'json', 'catalog', 'image', 'jpeg', 'blob', 'openai'))):
            return False
    return True

def dedupe_chips(chips: list[str]) -> list[str]:
    out: list[str] = []
    for chip in chips:
        text = normalize_chip_text(chip)
        if not text or is_other_chip(text):
            continue
        if any((jaccard_similarity(text, kept) >= JACCARD_DUPLICATE_THRESHOLD for kept in out)):
            continue
        out.append(text)
    return out

def gate_chip_list(chips: list[str], *, input_name: str='', agent_summary: str='', catalog_sourced: bool=False) -> list[str]:
    gated: list[str] = []
    for chip in chips:
        if chip_passes_quality_gate(chip, input_name=input_name, agent_summary=agent_summary, catalog_sourced=catalog_sourced):
            gated.append(normalize_chip_text(chip))
    return dedupe_chips(gated)

def pick_suggested_chip(chips: list[str], *, query: str='', rank_hint: float=0.0) -> str | None:
    """Best chip for UI highlight — never Other."""
    core = [c for c in chips if not is_other_chip(c)]
    if not core:
        return None
    if rank_hint >= 70 and core:
        return core[0]
    if query.strip():
        q_tokens = _tokens(query)
        scored = sorted(core, key=lambda c: len(_tokens(c) & q_tokens), reverse=True)
        if scored and _tokens(scored[0]) & q_tokens:
            return scored[0]
    return core[0]

def merge_and_gate_chips(*, deterministic: list[str] | None=None, catalog: list[str] | None=None, contextual: list[str] | None=None, llm: list[str] | None=None, input_name: str='', agent_summary: str='', limit: int=5) -> list[str]:
    """
    Merge tier order: deterministic → catalog → contextual → llm, then quality gate.
    Always ends with Other / describe in chat.
    """
    catalog_norm = [normalize_chip_text(c) for c in catalog or [] if c and (not is_other_chip(c))]
    catalog_gated = gate_chip_list(catalog_norm, input_name=input_name, agent_summary=agent_summary, catalog_sourced=True)
    other_merged = [normalize_chip_text(c) for source in (deterministic or [], contextual or [], llm or []) for c in source if c and (not is_other_chip(c))]
    gated = dedupe_chips(catalog_gated + gate_chip_list(other_merged, input_name=input_name, agent_summary=agent_summary))
    if len(gated) < MIN_MERGED_CHIPS and catalog_gated:
        for chip in catalog_gated:
            if chip not in gated:
                gated.append(chip)
    if len(gated) < MIN_MERGED_CHIPS and deterministic:
        for chip in deterministic:
            if is_other_chip(chip):
                continue
            text = normalize_chip_text(chip)
            if text and text not in gated:
                gated.append(text)
            if len(gated) >= MIN_MERGED_CHIPS:
                break
    return gated[:limit] + [OTHER_CHIP]


# ========================================================================
# services/catalog_hints.py
# ========================================================================


"""Phase 1 catalog search to ground Phase 2 interviews."""
import logging
logger = logging.getLogger(__name__)

def fetch_catalog_hints(query: str, settings: Settings, *, top_k: int=5) -> list[CatalogHint]:
    """
    Search the Affine agent catalog for records similar to the problem statement.

    Args:
        query: Problem statement or use-case text.
        settings: Azure configuration.
        top_k: Maximum agents to return.

    Returns:
        CatalogHint list; empty if search is unavailable or fails.

    Side effects:
        Azure OpenAI embedding + Azure AI Search hybrid query when configured.
    """
    text = (query or '').strip()
    if len(text) < 20:
        return []
    try:
        results = search_agents(text[:800], settings, top_k=top_k)
    except Exception as exc:
        logger.warning('Catalog hint search skipped: %s', exc)
        return []
    hints: list[CatalogHint] = []
    for row in results:
        score = float(row.get('score') or 0.0)
        hints.append(CatalogHint(agent_id=str(row.get('id') or ''), name=str(row.get('name') or 'Unknown'), category=str(row.get('category') or ''), origin_client=str(row.get('origin_client') or ''), function_summary=str(row.get('function_summary') or '')[:240], score=score))
    logger.info('Catalog hints: %d agents for query (%d chars)', len(hints), len(text))
    return hints


# ========================================================================
# services/catalog_interview_context.py
# ========================================================================


"""Ground Phase 2 interview questions in agents from data/spec.json."""
import json
import logging
import re
from pathlib import Path
from typing import Any
logger = logging.getLogger(__name__)
_TOKEN_RE = re.compile('[a-z0-9]{3,}')
_CATALOG_CACHE: dict[str, Any] = {'path': None, 'mtime_ns': None, 'result': CatalogLoadResult()}

def _catalog_path(settings: Settings) -> Path:
    return Path(settings.pdf_path).expanduser()

def load_all_catalog_agents(settings: Settings) -> list[AgentRecord]:
    """All agents from data/spec.json for Agent Library API."""
    agents = _load_spec_agents(settings)
    return sorted(agents, key=lambda a: (a.category, a.name.lower()))

def _load_catalog(settings: Settings) -> CatalogLoadResult:
    path = _catalog_path(settings)
    if not path.is_file() or path.suffix.lower() != '.json':
        return CatalogLoadResult()
    try:
        stat = path.stat()
        mtime_ns = int(getattr(stat, 'st_mtime_ns', 0))
        cache_path = _CATALOG_CACHE.get('path')
        cache_mtime = _CATALOG_CACHE.get('mtime_ns')
        if cache_path == str(path) and cache_mtime == mtime_ns:
            cached = _CATALOG_CACHE.get('result')
            if isinstance(cached, CatalogLoadResult):
                return cached
    except Exception:
        mtime_ns = None
    try:
        loaded = load_catalog_json(path)
        _CATALOG_CACHE['path'] = str(path)
        _CATALOG_CACHE['mtime_ns'] = mtime_ns
        _CATALOG_CACHE['result'] = loaded
        return loaded
    except Exception as exc:
        logger.warning('Could not load spec.json for interview context: %s', exc)
        return CatalogLoadResult()

def _load_spec_agents(settings: Settings) -> list[AgentRecord]:
    return _load_catalog(settings).agents

def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or '').lower()))
DATA_COPILOT_AGENT_IDS: tuple[str, ...] = ('pipeline-intent-classifier', 'quin-sql-agent-chain', 'eryl-semantic-rag-agent-chain')

def is_data_copilot_query(query: str) -> bool:
    """
    Bot/copilot problems over structured + unstructured data (e.g. saturated/unsaturated).
    Routes to Quin (SQL) and Eryl (RAG) from Mars Sales Genie.
    """
    q = (query or '').lower()
    has_bot = any((w in q for w in ('bot', 'chatbot', 'copilot', 'assistant', 'q&a', 'question answering', 'genie')))
    has_data = any((w in q for w in ('data', 'saturated', 'unsaturated', 'sql', 'analytics', 'structured', 'unstructured', 'semantic', 'database', 'metric', 'inventory', 'sales')))
    return has_bot and has_data

def _copilot_routing_boost(query: str, agent: AgentRecord) -> float:
    if not is_data_copilot_query(query):
        return 0.0
    if agent.id in DATA_COPILOT_AGENT_IDS:
        return 0.9
    return 0.0

def pinned_copilot_agents(query: str, agents: list[AgentRecord]) -> list[AgentRecord]:
    """Return Pipeline + Quin + Eryl in stable order when query is a data copilot."""
    if not is_data_copilot_query(query):
        return []
    by_id = _agent_by_id(agents)
    return [by_id[aid] for aid in DATA_COPILOT_AGENT_IDS if aid in by_id]

def _keyword_score(query: str, agent: AgentRecord) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    blob = ' '.join([agent.name, agent.category, agent.function_summary, agent.notes or '', agent.origin_project, agent.origin_client, ' '.join(agent.integrations), ' '.join(agent.tech_stack)]).lower()
    a = _tokens(blob)
    if not a:
        return 0.0
    overlap = len(q & a)
    base = overlap / max(len(q), 1)
    return min(1.0, base + _copilot_routing_boost(query, agent))

def _agent_by_id(agents: list[AgentRecord]) -> dict[str, AgentRecord]:
    by_id: dict[str, AgentRecord] = {}
    for a in agents:
        by_id[a.id] = a
        by_id[slugify(a.name)] = a
    return by_id

def _hint_from_agent(agent: AgentRecord, score: float) -> CatalogHint:
    integrations = ', '.join(agent.integrations[:6]) if agent.integrations else ''
    return CatalogHint(agent_id=agent.id, name=agent.name, category=agent.category, origin_client=agent.origin_client, function_summary=(agent.function_summary or '')[:400], score=score, origin_project=agent.origin_project or '', integrations=integrations, model_used=agent.model_used or '', status=agent.status or 'available')

def build_catalog_hints_for_interview(query: str, settings: Settings, *, top_k: int=12, preferred_agent_ids: list[str] | None=None) -> list[CatalogHint]:
    """
    Hybrid catalog context: Azure Search when available, always enriched from spec.json.
    """
    text = (query or '').strip()
    all_agents = _load_spec_agents(settings)
    by_id = _agent_by_id(all_agents)
    preferred = set(preferred_agent_ids or [])
    merged: list[CatalogHint] = []
    seen: set[str] = set()
    for agent in pinned_copilot_agents(text, all_agents):
        if agent.id not in seen:
            seen.add(agent.id)
            merged.append(_hint_from_agent(agent, 0.96))
    for aid in preferred:
        agent = by_id.get(aid)
        if agent and agent.id not in seen:
            seen.add(agent.id)
            merged.append(_hint_from_agent(agent, 0.95))
    search_hints = fetch_catalog_hints(text, settings, top_k=top_k) if len(text) >= 20 else []
    for h in search_hints:
        key = h.agent_id or slugify(h.name)
        if key in seen:
            continue
        seen.add(key)
        full = by_id.get(h.agent_id) or by_id.get(slugify(h.name))
        if full:
            merged.append(_hint_from_agent(full, h.score))
        else:
            merged.append(h)
    if len(merged) < top_k and all_agents and text:
        ranked = sorted(((a, _keyword_score(text, a)) for a in all_agents), key=lambda x: x[1], reverse=True)
        for agent, kw_score in ranked:
            if agent.id in seen:
                continue
            if kw_score < 0.05:
                continue
            seen.add(agent.id)
            merged.append(_hint_from_agent(agent, min(0.75, kw_score)))
            if len(merged) >= top_k:
                break
    logger.info('Interview catalog context: %d agents (search=%d, spec.json=%d)', len(merged), len(search_hints), len(all_agents))
    return merged[:top_k]

def _project_score(query: str, project: ProjectRecord, agents: list[AgentRecord]) -> float:
    blob = ' '.join([project.name, project.client, project.business_problem, project.solution_summary, project.outcomes or '', ' '.join(project.tech_stack)])
    for agent in agents:
        if agent.origin_project == project.name:
            blob += ' ' + ' '.join([agent.name, agent.function_summary, ' '.join(agent.integrations)])
    q = _tokens(query)
    p = _tokens(blob)
    if not q or not p:
        return 0.0
    return len(q & p) / max(len(q), 1)

def _truncate(text: str, limit: int) -> str:
    text = (text or '').strip()
    if len(text) <= limit:
        return text
    return text[:limit - 1].rsplit(' ', 1)[0] + '…'

def format_catalog_brief_for_interview(query: str, settings: Settings, *, top_projects: int=2, agents_per_project: int=8, preferred_agent_ids: list[str] | None=None) -> str:
    """
    Project-first catalog brief for catalog_pattern_interview.txt.

    Ranks spec.json projects by keyword fit, then lists agents in catalog order
    with inputs, outputs, and integrations.
    """
    catalog = _load_catalog(settings)
    if not catalog.projects and (not catalog.agents):
        return format_catalog_for_interview_prompt([])
    preferred = set(preferred_agent_ids or [])
    agents_by_project: dict[str, list[AgentRecord]] = {}
    for agent in catalog.agents:
        key = agent.origin_project or 'unknown'
        agents_by_project.setdefault(key, []).append(agent)
    entries: list[tuple[ProjectRecord, list[AgentRecord], float]] = []
    for project in catalog.projects:
        project_agents = agents_by_project.get(project.name, [])[:agents_per_project]
        if not project_agents:
            continue
        score = _project_score(query, project, project_agents)
        if preferred:
            score += 0.15 * sum((1 for a in project_agents if a.id in preferred))
        entries.append((project, project_agents, score))
    entries.sort(key=lambda x: x[2], reverse=True)
    top = entries[:top_projects]
    lines = ['REFERENCE PROJECTS (spec.json, ranked by fit):', '']
    if not top:
        return format_catalog_for_interview_prompt(build_catalog_hints_for_interview(query, settings, top_k=12))
    for rank, (project, agents, score) in enumerate(top, 1):
        lines.append(f'{rank}. {project.name} — {project.vertical}')
        if project.client:
            lines.append(f'   Client: {project.client}')
        lines.append(f'   Fit score: {score:.2f}')
        lines.append(f'   Problem: {_truncate(project.business_problem, 280)}')
        lines.append(f'   Solution pattern: {_truncate(project.solution_summary, 320)}')
        if project.outcomes:
            lines.append(f'   Outcomes: {_truncate(str(project.outcomes), 200)}')
        lines.append('   Agents (typical pipeline order):')
        for agent in agents:
            ins = ', '.join(agent.inputs[:4]) if agent.inputs else '—'
            outs = ', '.join(agent.outputs[:4]) if agent.outputs else '—'
            ints = ', '.join(agent.integrations[:5]) if agent.integrations else '—'
            lines.append(f'   - {agent.name} [{agent.category}] id={agent.id}')
            lines.append(f'     Does: {_truncate(agent.function_summary, 200)}')
            lines.append(f'     In: {_truncate(ins, 120)} | Out: {_truncate(outs, 120)}')
            lines.append(f'     Integrations: {_truncate(ints, 100)}')
            if agent.notes:
                lines.append(f'     Notes: {_truncate(agent.notes, 120)}')
        lines.append('')
    lines.append('USER PROBLEM (match patterns above):')
    lines.append(_truncate(query, 500))
    return '\n'.join(lines).strip()

def _dedupe_preserve(items: list[str], limit: int=24) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for raw in items:
        text = (raw or '').strip()
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= limit:
            break
    return out

def format_matched_agents_context(hints: list[CatalogHint], settings: Settings) -> dict[str, str]:
    """
    Build placeholder values for catalog_pattern_interview.txt from catalog hints
    and full agent records in spec.json.
    """
    catalog = _load_catalog(settings)
    by_id = _agent_by_id(catalog.agents)
    matched: list[dict] = []
    all_inputs: list[str] = []
    all_outputs: list[str] = []
    tech: list[str] = []
    models: list[str] = []
    notes: list[str] = []
    for h in hints[:8]:
        agent = by_id.get(h.agent_id) or by_id.get(slugify(h.name))
        entry = {'agent_id': h.agent_id, 'name': h.name, 'category': h.category, 'origin_project': h.origin_project or '', 'origin_client': h.origin_client or '', 'function_summary': (h.function_summary or '')[:320], 'score': round(h.score, 3)}
        if agent:
            entry['inputs'] = agent.inputs[:6]
            entry['outputs'] = agent.outputs[:6]
            entry['integrations'] = agent.integrations[:6]
            entry['tech_stack'] = agent.tech_stack[:6]
            entry['model_used'] = agent.model_used or ''
            if agent.notes:
                entry['notes'] = agent.notes
            all_inputs.extend(agent.inputs)
            all_outputs.extend(agent.outputs)
            tech.extend(agent.integrations)
            tech.extend(agent.tech_stack)
            if agent.model_used and agent.model_used != 'Unknown':
                models.append(f'{agent.name}: {agent.model_used}')
            if agent.notes:
                notes.append(f'{agent.name}: {agent.notes}')
        elif h.integrations:
            tech.extend([s.strip() for s in h.integrations.split(',') if s.strip()])
        if h.model_used:
            models.append(f'{h.name}: {h.model_used}')
        matched.append(entry)
    if not matched and hints:
        matched = [{'agent_id': h.agent_id, 'name': h.name, 'category': h.category, 'function_summary': (h.function_summary or '')[:320], 'score': round(h.score, 3)} for h in hints[:8]]
    tech_deduped = _dedupe_preserve(tech, 20)
    return {'matched_agents_json': json.dumps(matched, indent=2) if matched else '[]', 'inputs_from_matched_agents': ', '.join(_dedupe_preserve(all_inputs, 16)) or '(none listed — infer from problem statement)', 'outputs_from_matched_agents': ', '.join(_dedupe_preserve(all_outputs, 16)) or '(none listed — infer from problem statement)', 'tech_stack_and_integrations': ', '.join(tech_deduped) or '(none listed)', 'model_breakdown': '; '.join(_dedupe_preserve(models, 10)) or '(not specified in catalog)', 'notes_from_matched_agents': '; '.join(_dedupe_preserve(notes, 8)) or '(none)'}

def format_catalog_for_interview_prompt(hints: list[CatalogHint]) -> str:
    """Rich block for LLM prompts — keeps spec.json agents in mind."""
    if not hints:
        return '(No agents loaded from catalog — ensure data/spec.json exists and run pipeline.run to index for search.)'
    lines = ['AFFINE BUILT AGENTS (data/spec.json). Ground requirements and architecture questions in these capabilities; chips may reflect similar patterns without naming agents unless the user already did.', '']
    for i, h in enumerate(hints, 1):
        lines.append(f'{i}. {h.name} [{h.category}]')
        if h.origin_project or h.origin_client:
            lines.append(f"   Project: {h.origin_project or '—'} ({h.origin_client or 'Affine'})")
        lines.append(f'   Does: {h.function_summary}')
        if h.integrations:
            lines.append(f'   Integrations: {h.integrations}')
        if h.model_used:
            lines.append(f'   Model: {h.model_used}')
        lines.append(f'   Relevance: {h.score:.2f}')
        lines.append('')
    return '\n'.join(lines).strip()


# ========================================================================
# services/catalog_chip_suggestions.py
# ========================================================================


"""Suggest interview answer chips from the closest spec.json project and agents."""
import re
from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    pass
OTHER_CHIP = 'Other / describe in chat'
_INTEGRATION_LABELS: list[tuple[str, str]] = [('azure blob storage', 'Files from cloud document storage'), ('azure sql server', 'Corporate database records'), ('smtp', 'Email for notifications and follow-ups'), ('azure ai search', 'Search over indexed documents'), ('azure ai vision', 'Photos and image uploads'), ('google gemini', 'Google document AI'), ('google ai studio', 'Google document AI'), ('roboflow', 'Shelf or field image detection'), ('azure openai', 'AI processing (included in platform)')]
_HITL_FROM_NOTES: list[tuple[re.Pattern[str], str]] = [(re.compile('analyst reviews?/edits', re.I), 'Analyst reviews and edits before anything is sent'), (re.compile('human-in-the-loop', re.I), 'A person reviews key results before they go out'), (re.compile('analyst queue', re.I), 'Analysts work from a prioritized review queue'), (re.compile('blocks? risk', re.I), 'Automatic checks first, person only on exceptions')]

def _normalize_chip(text: str) -> str:
    """Keep full chip text — options must be complete, readable answers."""
    return re.sub('\\s+', ' ', (text or '').strip())

def _humanize_integration(raw: str) -> str:
    lowered = raw.lower()
    for needle, label in _INTEGRATION_LABELS:
        if needle in lowered:
            return label
    cleaned = re.sub('\\bazure\\b', '', raw, flags=re.I).strip(' -/')
    cleaned = re.sub('\\s+', ' ', cleaned)
    return _normalize_chip(cleaned or raw)

def _score_chip(query: str, chip: str) -> float:
    q = set(re.findall('[a-z0-9]{3,}', query.lower()))
    c = set(re.findall('[a-z0-9]{3,}', chip.lower()))
    if not q or not c:
        return 0.0
    return len(q & c) / max(len(q), 1)

def _dedupe_chips(chips: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for chip in chips:
        key = chip.lower().strip()
        if not key or key == OTHER_CHIP.lower():
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(_normalize_chip(chip))
    return [c for c in out if c]

def _rank_chips(query: str, chips: list[str], *, field_key: str='', turn_index: int=0) -> list[str]:
    """Stable ranking: relevance score, then alphabetical (same query → same order)."""
    del turn_index
    deduped = _dedupe_chips(chips)
    return sorted(deduped, key=lambda c: (-_score_chip(query, c), c.lower()))

def _interview_turn_index(messages: list['ChatMessage']) -> int:
    return sum((1 for m in messages if m.role == 'user' and m.content.strip()))

def _known_interview_values(spec: 'ArchitectureSpec') -> dict[str, str]:
    out: dict[str, str] = {}
    for key in USER_INTERVIEW_FIELD_KEYS:
        field = spec.fields.get(key)
        if field and field.value and str(field.value).strip():
            out[key] = str(field.value).strip()
    return out

def _latest_user_answer(messages: list['ChatMessage']) -> tuple[str | None, str | None]:
    for msg in reversed(messages):
        if msg.role != 'user' or not msg.content.strip():
            continue
        return (msg.field_key, msg.content.strip())
    return (None, None)

def contextual_chips_from_conversation(field_key: str, spec: 'ArchitectureSpec', messages: list['ChatMessage']) -> list[str]:
    """Prior user-confirmed values only — no synthesized templates."""
    chips: list[str] = []
    known = _known_interview_values(spec)
    for key, value in known.items():
        if key == field_key:
            continue
        text = value.strip()
        if text:
            chips.append(_normalize_chip(text[:160]))
    _, last_answer = _latest_user_answer(messages)
    if last_answer and len(last_answer.strip()) > 8:
        chips.append(_normalize_chip(last_answer.strip()[:160]))
    return _dedupe_chips(chips)[:5]
_FIELD_EASE_SCORE: dict[str, float] = {'integrations': 3.0, 'hitl_behavior': 2.6, 'architectural_flow': 2.3, 'core_components': 1.4, 'data_flow': 0.7, 'orchestration_model': 0.4}

def recommend_first_interview_field(spec: 'ArchitectureSpec', settings: Settings, open_gaps: list[str] | None=None) -> str:
    """
    Easiest interview topic that best matches the problem and closest catalog project.
    """
    gaps = [g for g in open_gaps or list(USER_INTERVIEW_FIELD_KEYS) if g in USER_INTERVIEW_FIELD_KEYS]
    if not gaps:
        return 'integrations'
    query = spec.problem_statement
    project, agents, fit = _top_project_context(query, settings)
    blob = query.lower()
    scores: dict[str, float] = {g: _FIELD_EASE_SCORE.get(g, 1.0) for g in gaps}
    if any((w in blob for w in ('email', 'upload', 'file', 'document', 'pdf', 'crm', 'database'))):
        scores['integrations'] = scores.get('integrations', 0) + 2.5
    if any((w in blob for w in ('review', 'approve', 'analyst', 'manual', 'human'))):
        scores['hitl_behavior'] = scores.get('hitl_behavior', 0) + 2.2
    if any((w in blob for w in ('step', 'process', 'workflow', 'order', 'pipeline'))):
        scores['architectural_flow'] = scores.get('architectural_flow', 0) + 2.0
    if project:
        summary = f"{project.solution_summary or ''} {project.outcomes or ''}".lower()
        boost = 0.8 + min(fit, 1.0)
        if any((w in summary for w in ('upload', 'email', 'extract', 'document'))):
            scores['integrations'] = scores.get('integrations', 0) + boost
        if any((w in summary for w in ('review', 'analyst', 'queue', 'approve'))):
            scores['hitl_behavior'] = scores.get('hitl_behavior', 0) + boost
        if len(_flow_steps_from_agents(agents)) >= 3:
            scores['architectural_flow'] = scores.get('architectural_flow', 0) + boost + 0.3
    return max(scores, key=lambda k: (scores[k], k))

def easy_question_for_project(spec: 'ArchitectureSpec', field_key: str, settings: Settings) -> str:
    """First interview question grounded in the closest catalog delivery pattern."""
    hook = spec.problem_statement.strip()
    if len(hook) > 72:
        hook = hook[:72].rsplit(' ', 1)[0]
    project, agents, _fit = _top_project_context(spec.problem_statement, settings)
    vertical = (project.vertical or '').strip() if project else ''
    if field_key == 'integrations':
        if project and vertical:
            return _normalize_chip(f'For ({hook}), which integrations match your {vertical} reference pattern — file ingest, API, email, or case management system?')
        return _normalize_chip(f'For ({hook}), which source and sink integrations are required (API, files, CRM, warehouse)?')
    if field_key == 'hitl_behavior':
        if project and 'review' in (project.solution_summary or '').lower():
            return _normalize_chip(f'For ({hook}), is a human approval gate required before downstream systems consume outputs?')
        return _normalize_chip(f'For ({hook}), what HITL policy applies — always-on review, threshold-based, or exception-only?')
    if field_key == 'architectural_flow':
        steps = _flow_steps_from_agents(agents)
        if len(steps) >= 3:
            chain = ' → '.join((_normalize_chip(s) for s in steps[:4]))
            return _normalize_chip(f'For ({hook}), does your target pipeline align with: {chain}?')
        return _normalize_chip(f'For ({hook}), what is the end-to-end sequence from trigger through completion?')
    if field_key == 'core_components':
        return _normalize_chip(f'For ({hook}), which logical components are required (ingestion, scoring, HITL, reporting)?')
    if field_key == 'data_flow':
        return _normalize_chip(f'For ({hook}), should stages use direct handoffs or a shared operational datastore?')
    if field_key == 'orchestration_model':
        return _normalize_chip(f'For ({hook}), should orchestration be sequential, parallel, event-driven, or manual?')
    label = field_key.replace('_', ' ')
    return _normalize_chip(f'For this work ({hook}), what should we know about {label}?')

def pick_suggested_chip(chips: list[str], messages: list['ChatMessage']) -> str | None:
    """Highlight the chip that best matches the latest user message (not always first)."""
    other = OTHER_CHIP.lower()
    candidates = [c for c in chips if c.lower().strip() != other]
    if not candidates:
        return None
    _, latest = _latest_user_answer(messages)
    if not latest:
        return candidates[0]
    query = latest.lower()
    return max(candidates, key=lambda c: _score_chip(query, c))

def _top_project_context(query: str, settings: Settings, preferred_agent_ids: list[str] | None=None) -> tuple[Optional[ProjectRecord], list[AgentRecord], float]:
    catalog = _load_catalog(settings)
    if not catalog.projects:
        return (None, catalog.agents[:8], 0.0)
    preferred = set(preferred_agent_ids or [])
    agents_by_project: dict[str, list[AgentRecord]] = {}
    for agent in catalog.agents:
        agents_by_project.setdefault(agent.origin_project or 'unknown', []).append(agent)
    best: tuple[Optional[ProjectRecord], list[AgentRecord], float] = (None, [], 0.0)
    for project in catalog.projects:
        project_agents = agents_by_project.get(project.name, [])[:10]
        if not project_agents:
            continue
        score = _project_score(query, project, project_agents)
        if preferred:
            score += 0.12 * sum((1 for a in project_agents if a.id in preferred))
        if score > best[2]:
            best = (project, project_agents, score)
    return best

def _flow_steps_from_agents(agents: list[AgentRecord]) -> list[str]:
    steps: list[str] = []
    for agent in agents:
        label = agent.name.replace(' Agent', '').strip()
        if label:
            steps.append(label)
    return steps[:7]

def _flow_steps_from_summary(project: ProjectRecord) -> list[str]:
    summary = project.solution_summary or ''
    if not summary:
        return []
    parts = re.split(',\\s+(?=[A-Z])|\\s+and\\s+', summary)
    steps: list[str] = []
    for part in parts[:7]:
        part = part.strip()
        if len(part) < 12:
            continue
        steps.append(_normalize_chip(part))
    return steps

def _hitl_chips_from_catalog(project: Optional[ProjectRecord], agents: list[AgentRecord]) -> list[str]:
    chips: list[str] = []
    blob = ''
    if project:
        blob += f"{project.solution_summary} {project.outcomes or ''}"
    for agent in agents:
        blob += f" {agent.notes or ''} {agent.function_summary}"
    for pattern, label in _HITL_FROM_NOTES:
        if pattern.search(blob):
            chips.append(label)
    low = blob.lower()
    if 'analyst' in low and 'review' in low:
        chips.append('Analyst reviews items in a work queue')
    if 'upload' in low and 'extract' in low:
        chips.append('Fully automatic until a policy check fails')
    if 'draft' in low and 'email' in low:
        chips.append('Review drafted emails before they go to clients')
    chips.extend(['A person checks every output before it is final', 'Only low-confidence or high-risk cases go to a person', 'No regular human review — fully automatic'])
    return chips

def _integration_chips_from_catalog(agents: list[AgentRecord]) -> list[str]:
    raw_ints: list[str] = []
    for agent in agents:
        for item in agent.integrations:
            if item and item.strip():
                raw_ints.append(item.strip())
    humanized = [_humanize_integration(x) for x in raw_ints]
    humanized = _dedupe_chips(humanized)
    combos: list[str] = []
    if len(humanized) >= 2:
        combos.append(f'{humanized[0]} and {humanized[1].lower()}')
    if len(humanized) >= 3:
        combos.append(f'{humanized[0]}, {humanized[1].lower()}, and {humanized[2].lower()}')
    singles = humanized[:5]
    chips = combos + singles
    chips.extend(['Uploaded documents only — no other systems yet', 'Email plus internal database', 'Spreadsheets or shared files for now'])
    return chips

def _flow_chips_from_catalog(project: Optional[ProjectRecord], agents: list[AgentRecord], draft_flow: list[str] | None=None) -> list[str]:
    steps = list(draft_flow or [])
    agent_steps = _flow_steps_from_agents(agents)
    if len(agent_steps) >= 3:
        steps = agent_steps
    elif len(steps) < 3 and project:
        steps = _flow_steps_from_summary(project)
    if len(steps) < 3:
        steps = agent_steps
    chips: list[str] = []
    if len(steps) >= 3:
        chain = ' → '.join((_normalize_chip(s) for s in steps[:5]))
        chips.append(_normalize_chip(f'Yes — use this order: {chain}'))
        chips.append('Close — same steps with small changes')
        partial = ' → '.join((_normalize_chip(s) for s in steps[:3]))
        chips.append(_normalize_chip(f'Partly — start like {partial}, then different steps'))
    chips.extend(['Different order — intake and review happen elsewhere', 'Fewer steps — skip automated checks', 'More steps — extra approval before final output'])
    return chips

def _component_chips_from_catalog(agents: list[AgentRecord]) -> list[str]:
    chips: list[str] = []
    for agent in agents[:6]:
        summary = (agent.function_summary or '').strip()
        if not summary:
            continue
        first = summary.split('.')[0].strip()
        if len(first) > 8:
            chips.append(_normalize_chip(first))
        else:
            chips.append(_normalize_chip(agent.name.replace(' Agent', '')))
    if len(chips) >= 2:
        chain = ' → '.join((_normalize_chip(c) for c in chips[:4]))
        chips.insert(0, _normalize_chip(f'Main blocks in order: {chain}'))
    chips.extend(['Intake, automated checks, human review, final report', 'Collect data, analyze, publish to a dashboard', 'Mostly automatic with one approval step'])
    return chips

def _data_flow_chips_from_catalog(project: Optional[ProjectRecord], agents: list[AgentRecord]) -> list[str]:
    chips = ['Each step passes results directly to the next step', 'One shared case or record that every step updates', 'Intake writes to storage, later steps read when ready', 'Results go to email or a dashboard at the end only']
    blob = ''
    if project:
        blob = f"{project.solution_summary} {project.outcomes or ''}"
    for agent in agents[:4]:
        blob += f" {agent.function_summary or ''}"
    low = blob.lower()
    if 'queue' in low or 'analyst' in low:
        chips.insert(0, 'Automated steps first, then a person picks up from a work queue')
    if 'email' in low:
        chips.insert(1, 'Documents in, summary or notification out by email')
    return chips

def _orchestration_chips_from_catalog(project: Optional[ProjectRecord], agents: list[AgentRecord]) -> list[str]:
    steps = _flow_steps_from_agents(agents)
    chips = ['Strict sequence — step two only after step one completes', 'Parallel where possible — independent checks run together', 'Manual trigger — a person starts the next major phase', 'Fully automatic chain once the first file arrives']
    if len(steps) >= 4:
        chain = ' → '.join((_normalize_chip(s) for s in steps[:4]))
        chips.insert(0, _normalize_chip(f'Automatic pipeline in this order: {chain}'))
    if project and 'review' in (project.solution_summary or '').lower():
        chips.insert(1, 'Automatic until review, then paused until a person approves')
    return chips

def suggest_chips_for_field(field_key: str, query: str, settings: Settings, *, preferred_agent_ids: list[str] | None=None, draft_flow: list[str] | None=None, limit: int=5, spec: Optional['ArchitectureSpec']=None, messages: Optional[list['ChatMessage']]=None, llm_chips: list[str] | None=None, clarifying_answers: dict[str, str] | None=None, workflow_answers: dict[str, str] | None=None) -> list[str]:
    """Chips from catalog rows filtered by all prior selections (cascading)."""
    del draft_flow
    result = generate_cascading_options(field_key, query, settings, clarifying_answers=clarifying_answers, workflow_answers=workflow_answers, spec=spec, preferred_agent_ids=preferred_agent_ids, limit=limit)
    catalog_core = [c for c in result.options if c != OTHER_CHIP]
    context: list[str] = []
    msgs = messages or []
    if spec is not None and msgs and (_interview_turn_index(msgs) >= 1):
        context = contextual_chips_from_conversation(field_key, spec, msgs)
    llm = llm_chips if llm_chips is not None else []
    return merge_catalog_chips(field_key, llm, catalog_core, context_chips=context)

def build_chip_query_context(spec: 'ArchitectureSpec', messages: list['ChatMessage'], target_field: str | None) -> str:
    """Query text for ranking catalog chips — includes answers so far and field focus."""
    parts: list[str] = [spec.problem_statement]
    if spec.transcript_summary:
        parts.append(spec.transcript_summary)
    for key in USER_INTERVIEW_FIELD_KEYS:
        field = spec.fields.get(key)
        if field and field.value and str(field.value).strip():
            parts.append(f'{key}: {str(field.value).strip()}')
    recent_user = [m.content.strip() for m in messages[-10:] if m.role == 'user' and m.content.strip()]
    if recent_user:
        parts.append('Recent answers: ' + ' | '.join(recent_user[-4:]))
    if target_field:
        field = spec.fields.get(target_field)
        label = field.label if field else target_field
        parts.append(f'Focus: {target_field} ({label})')
        draft_val = field.value if field and field.value else ''
        if field and field.notes:
            draft_val = f'{draft_val} {field.notes}'.strip()
        if draft_val:
            parts.append(f'Current draft: {draft_val}')
    return '\n'.join((p for p in parts if p)).strip()

def suggest_all_field_chips(query: str, settings: Settings, *, preferred_agent_ids: list[str] | None=None, draft_flow: list[str] | None=None, spec: Optional['ArchitectureSpec']=None, messages: Optional[list['ChatMessage']]=None, only_fields: list[str] | None=None) -> dict[str, list[str]]:
    """Chips per field — each list built for that topic and current conversation."""
    fields = only_fields or ['hitl_behavior', 'integrations', 'architectural_flow', 'data_flow', 'core_components', 'orchestration_model']
    out: dict[str, list[str]] = {}
    for key in fields:
        field_query = query
        if spec is not None and messages is not None:
            field_query = build_chip_query_context(spec, messages, target_field=key)
        out[key] = suggest_chips_for_field(key, field_query, settings, preferred_agent_ids=preferred_agent_ids, draft_flow=draft_flow if key == 'architectural_flow' else None, spec=spec, messages=messages)
    return out

def merge_catalog_chips(field_key: str, llm_chips: list[str], catalog_chips: list[str], *, context_chips: list[str] | None=None, input_name: str='', agent_summary: str='') -> list[str]:
    """Session-specific + model chips first; catalog templates fill gaps; quality gate."""
    catalog_core = [_normalize_chip(c) for c in catalog_chips if c != OTHER_CHIP]
    llm_core = [_normalize_chip(c) for c in llm_chips if c and c.lower() != OTHER_CHIP.lower()]
    context_core = [_normalize_chip(c) for c in context_chips or [] if c and c.lower() != OTHER_CHIP.lower()]
    return merge_and_gate_chips(deterministic=[], catalog=catalog_core, contextual=context_core, llm=llm_core, input_name=input_name or field_key, agent_summary=agent_summary)

def suggest_clarifying_chips(query: str, settings: Settings, *, preferred_agent_ids: list[str] | None=None, limit: int=4) -> list[str]:
    """Scope chips for pre-interview clarifying questions from the top catalog project."""
    project, agents, _score = _top_project_context(query, settings, preferred_agent_ids=preferred_agent_ids)
    chips: list[str] = []
    if project:
        chips.append(_normalize_chip(f"Same scope as {project.name.split('(')[0].strip()}"))
        if project.vertical and project.vertical != 'Other':
            chips.append(_normalize_chip(f'Same industry pattern ({project.vertical})'))
        first_sentence = (project.business_problem or '').split('.')[0].strip()
        if len(first_sentence) > 20:
            chips.append(_normalize_chip(first_sentence))
    chips.extend(_integration_chips_from_catalog(agents)[:2])
    chips.extend(_hitl_chips_from_catalog(project, agents)[:2])
    chips.extend(['Broader scope than similar past projects', 'Narrower — one team or document type only'])
    return _rank_chips(query, chips)[:max(limit - 1, 3)] + [OTHER_CHIP]

def catalog_suggestion_context(query: str, settings: Settings, preferred_agent_ids: list[str] | None=None) -> tuple[str, str]:
    """Reference project label and one-line reason for why_it_matters."""
    project, agents, score = _top_project_context(query, settings, preferred_agent_ids=preferred_agent_ids)
    if not project:
        return ('', '')
    name = project.name
    reason = f'Top match from our catalog ({name}, fit {score:.0%}) — first option is the closest pattern from spec.json.'
    if agents:
        reason += f' Based on {len(agents)} agents from that delivery.'
    return (name, reason)

def suggestion_reason_for_field(field_key: str, query: str, settings: Settings, *, preferred_agent_ids: list[str] | None=None) -> str:
    """Short user-facing reason explaining why the suggestion helps."""
    project, agents, _score = _top_project_context(query, settings, preferred_agent_ids=preferred_agent_ids)
    if not project:
        return ''
    if field_key == 'integrations':
        ints: list[str] = []
        for a in agents[:4]:
            ints.extend(a.integrations[:2])
        ints = [i for i in ints if i]
        if ints:
            return f"Suggested from {project.name}: similar solutions connect to {', '.join(ints[:3])}."
    if field_key == 'hitl_behavior':
        return f'Suggested from {project.name}: similar workflows keep a human review step when confidence is low.'
    if field_key == 'architectural_flow':
        return f'Suggested from {project.name}: this follows the closest delivery flow seen in spec.json.'
    if field_key == 'core_components':
        comps = [a.name.replace(' Agent', '') for a in agents[:3]]
        if comps:
            return f"Suggested from {project.name}: common building blocks are {', '.join(comps)}."
    return f'Suggested from {project.name} as the closest matching catalog pattern.'


# ========================================================================
# services/cascading_options.py
# ========================================================================


"""
Runtime option generation from spec.json catalog data.

All interview chips are derived from agent/project rows in the catalog.
Prior selections filter which rows are considered; options are distinct
values read from those rows (inputs, outputs, integrations, notes, etc.).
"""
import logging
import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional
if TYPE_CHECKING:
    pass
logger = logging.getLogger(__name__)
_TOKEN_RE = re.compile('[a-z0-9]{3,}')
_SLASH_ENUM_RE = re.compile('\\b([A-Z][A-Za-z0-9]*(?:/[A-Z][A-Za-z0-9]*)+)\\b')
_WIRED_INPUT_MARKERS = ('extracted json', 'document bytes', 'source document text', 'reason string', 'missing_item', 'from entity')
CLARIFYING_FIELD_PREFIX = 'clarifying:'
DISCOVERY_FIELD_PREFIX = 'discovery:'
AGENT_INPUT_PREFIX = 'agent_input:'

@dataclass
class CascadingSelectionState:
    problem_statement: str = ''
    clarifying_answers: dict[str, str] = field(default_factory=dict)
    workflow_answers: dict[str, str] = field(default_factory=dict)
    spec_field_answers: dict[str, str] = field(default_factory=dict)
    preferred_agent_ids: list[str] = field(default_factory=list)
    target_field: str = ''
    target_agent_id: str | None = None
    target_input_name: str | None = None

@dataclass
class CascadingOptionResult:
    options: list[str]
    debug: dict[str, Any]

def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or '').lower()))

def _selection_overlap(row_text: str, selection: str) -> bool:
    """True when catalog row text plausibly matches a prior user selection."""
    if not selection.strip():
        return True
    row_low = (row_text or '').lower()
    sel_low = selection.lower().strip()
    if sel_low in row_low or row_low in sel_low:
        return True
    rt, st = (_tokens(row_text), _tokens(selection))
    if not rt or not st:
        return False
    return len(rt & st) / max(len(st), 1) >= 0.25

def _agent_blob(agent: AgentRecord) -> str:
    return ' '.join(filter(None, [agent.name, agent.function_summary, agent.notes or '', agent.category, ' '.join(agent.inputs), ' '.join(agent.outputs), ' '.join(agent.integrations), ' '.join(agent.tech_stack)]))

def _projects_for_agents(catalog: CatalogLoadResult, agents: list[AgentRecord]) -> list[ProjectRecord]:
    names = {a.origin_project for a in agents if a.origin_project}
    return [p for p in catalog.projects if p.name in names]

def _score_agents(agents: list[AgentRecord], query: str, preferred_ids: list[str]) -> list[AgentRecord]:
    preferred = set(preferred_ids)
    scored: list[tuple[float, AgentRecord]] = []
    for agent in agents:
        score = _keyword_score(query, agent)
        if agent.id in preferred:
            score += 0.35
        scored.append((score, agent))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [a for _, a in scored]

def filter_catalog_rows(catalog: CatalogLoadResult, state: CascadingSelectionState) -> tuple[list[AgentRecord], list[ProjectRecord], dict[str, Any]]:
    """Apply cascading filters from all prior selections."""
    debug: dict[str, Any] = {'problem_statement': state.problem_statement[:200], 'prior_selections': {}, 'stages': []}
    agents = list(catalog.agents)
    debug['stages'].append({'stage': 'all_agents', 'count': len(agents)})
    agents = _score_agents(agents, state.problem_statement, state.preferred_agent_ids)
    clarifying = {k: v.strip() for k, v in state.clarifying_answers.items() if v.strip() and (not is_change_problem_statement_intent(v))}
    debug['prior_selections']['clarifying'] = clarifying
    if clarifying.get('q1'):
        sel = clarifying['q1']
        agents = [a for a in agents if _selection_overlap(' '.join(a.inputs), sel) or _selection_overlap(' '.join(a.integrations), sel) or _selection_overlap(_agent_blob(a), sel)]
        debug['stages'].append({'stage': 'after_q1', 'count': len(agents), 'selection': sel})
    if clarifying.get('q2'):
        sel = clarifying['q2']
        agents = [a for a in agents if _selection_overlap(a.notes or '', sel) or _selection_overlap(a.function_summary, sel) or _selection_overlap(' '.join(a.outputs), sel)]
        debug['stages'].append({'stage': 'after_q2', 'count': len(agents), 'selection': sel})
    if clarifying.get('q3'):
        sel = clarifying['q3']
        agents = [a for a in agents if _selection_overlap(' '.join(a.integrations), sel) or _selection_overlap(' '.join(a.tech_stack), sel)]
        debug['stages'].append({'stage': 'after_q3', 'count': len(agents), 'selection': sel})
    for key, value in state.spec_field_answers.items():
        if not value.strip():
            continue
        debug['prior_selections'].setdefault('spec_fields', {})[key] = value
        agents = [a for a in agents if _selection_overlap(_agent_blob(a), value)]
        debug['stages'].append({'stage': f'after_spec_{key}', 'count': len(agents), 'selection': value[:120]})
    for field_key, value in state.workflow_answers.items():
        if not value.strip() or is_change_problem_statement_intent(value):
            continue
        debug['prior_selections'].setdefault('workflow', {})[field_key] = value
        agents = [a for a in agents if _selection_overlap(_agent_blob(a), value)]
        debug['stages'].append({'stage': f'after_{field_key}', 'count': len(agents), 'selection': value[:120]})
    if not agents:
        agents = _score_agents(list(catalog.agents), state.problem_statement, state.preferred_agent_ids)[:12]
        debug['stages'].append({'stage': 'fallback_top_scored', 'count': len(agents)})
    projects = _projects_for_agents(catalog, agents)
    debug['agent_names'] = [a.name for a in agents[:12]]
    debug['project_names'] = [p.name for p in projects[:6]]
    return (agents, projects, debug)

def _parse_enum_values_from_input_name(input_name: str) -> list[str]:
    """Enum fragments embedded in catalog input labels (from dataset text)."""
    chips: list[str] = []
    for match in _SLASH_ENUM_RE.finditer(input_name or ''):
        for part in match.group(1).split('/'):
            part = part.strip()
            if part:
                chips.append(part)
    paren = re.search('\\(([^)]+)\\)', input_name or '')
    if paren:
        inner = paren.group(1)
        if '/' in inner or ',' in inner:
            parts = re.split('[/,]', inner)
        elif re.search('\\bor\\b', inner, re.I):
            parts = re.split('\\s+or\\s+', inner, flags=re.I)
        else:
            parts = [inner]
        for part in parts:
            part = part.strip()
            if part and 2 <= len(part) <= 80:
                chips.append(part)
    return chips

def _distinct_inputs(agents: list[AgentRecord], *, limit: int=8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for agent in agents:
        for inp in agent.inputs:
            low = inp.lower()
            if any((marker in low for marker in _WIRED_INPUT_MARKERS)):
                continue
            key = low.strip()
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(_normalize_chip(inp))
            if len(out) >= limit:
                return out
    return out

def _distinct_integrations(agents: list[AgentRecord], *, limit: int=8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for agent in agents:
        for item in agent.integrations:
            text = (item or '').strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            out.append(_normalize_chip(text))
            if len(out) >= limit:
                return out
    return out

def _note_is_chip_candidate(note: str) -> bool:
    text = (note or '').strip()
    if len(text) < 12 or len(text) > 90:
        return False
    low = text.lower()
    if re.search('\\benv\\b|_[a-z0-9_]{4,}\\b|falls back to|if azure|post /api', low):
        return False
    return True

def _distinct_notes(agents: list[AgentRecord], projects: list[ProjectRecord], *, limit: int=8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for agent in agents:
        note = (agent.notes or '').strip()
        if note and _note_is_chip_candidate(note) and (note.lower() not in seen):
            seen.add(note.lower())
            out.append(_normalize_chip(note[:90]))
    for project in projects:
        for blob in (project.outcomes, project.solution_summary):
            text = (blob or '').strip()
            if not text:
                continue
            for sentence in re.split('[.;]\\s+', text):
                sentence = sentence.strip()
                if len(sentence) < 16 or sentence.lower() in seen:
                    continue
                seen.add(sentence.lower())
                out.append(_normalize_chip(sentence[:160]))
                if len(out) >= limit:
                    return out
    return out[:limit]

def _distinct_outputs(agents: list[AgentRecord], *, limit: int=8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for agent in agents:
        for item in agent.outputs:
            text = (item or '').strip()
            key = text.lower()
            if not text or key in seen:
                continue
            seen.add(key)
            out.append(_normalize_chip(text[:160]))
            if len(out) >= limit:
                return out
    return out

def _distinct_agent_names(agents: list[AgentRecord], *, limit: int=8) -> list[str]:
    return _dedupe_chips([_normalize_chip(a.name) for a in agents[:limit]])

def _distinct_categories(agents: list[AgentRecord], *, limit: int=6) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for agent in agents:
        cat = (agent.category or '').strip()
        if cat and cat.lower() not in seen:
            seen.add(cat.lower())
            out.append(_normalize_chip(cat))
    return out[:limit]

def _workflow_domain_options(agents: list[AgentRecord]) -> list[str]:
    base = ['Fashion and apparel (virtual try-on)', 'Jewelry and accessories', 'Eyewear and frames', 'Retail shelf and planogram analytics', 'Documents and compliance (KYC, invoices)', 'Chat / data copilot']
    for vertical in _distinct_categories(agents, limit=4):
        if vertical not in base:
            base.append(vertical)
    for agent in agents[:6]:
        if agent.vertical and agent.vertical.strip():
            chip = _normalize_chip(agent.vertical)
            if chip not in base:
                base.append(chip)
    return _dedupe_chips(base)[:8]

def _deployment_options(agents: list[AgentRecord]) -> list[str]:
    opts = ['Azure cloud (Affine standard)', 'AWS cloud', 'Internal on-premises', 'Standalone SaaS app', 'Hybrid — cloud compute + on-prem data']
    for agent in agents:
        for stack in agent.tech_stack[:3]:
            if stack and 'azure' in stack.lower():
                opts.append('Azure-hosted services')
                break
    return _dedupe_chips(opts)[:6]

def _flow_chains_from_agents(agents: list[AgentRecord], *, limit: int=4) -> list[str]:
    names = _distinct_agent_names(agents, limit=6)
    if len(names) < 2:
        return names
    chains: list[str] = []
    if len(names) >= 3:
        chains.append(_normalize_chip(' → '.join(names[:5])))
    if len(names) >= 2:
        chains.append(_normalize_chip(' → '.join(names[:3])))
    return chains[:limit]

def _agent_input_options(agents: list[AgentRecord], input_name: str, target_agent: AgentRecord | None, *, catalog_agents: list[AgentRecord] | None=None, limit: int=8) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in _parse_enum_values_from_input_name(input_name):
        key = value.lower()
        if key not in seen:
            seen.add(key)
            out.append(_normalize_chip(value))
    target_low = input_name.lower()
    pool_ids = {a.id for a in agents}
    pool = list(agents)
    for agent in catalog_agents or []:
        if agent.id in pool_ids:
            continue
        if any((inp.lower() == target_low or _tokens(inp) & _tokens(input_name) for inp in agent.inputs)):
            pool.append(agent)
            pool_ids.add(agent.id)
    if target_agent:
        for value in list(target_agent.integrations) + list(target_agent.tech_stack) + ([target_agent.model_used] if target_agent.model_used else []):
            text = (value or '').strip()
            key = text.lower()
            if text and key not in seen:
                seen.add(key)
                out.append(_normalize_chip(text[:160]))
    for agent in pool:
        for inp in agent.inputs:
            if inp.lower() == target_low or _tokens(inp) & _tokens(input_name):
                for enum in _parse_enum_values_from_input_name(inp):
                    key = enum.lower()
                    if key not in seen:
                        seen.add(key)
                        out.append(_normalize_chip(enum))
                key = inp.lower()
                if key not in seen:
                    seen.add(key)
                    out.append(_normalize_chip(inp))
        for out_name in agent.outputs:
            if any((w in target_low for w in ('from', 'json', 'extracted', 'upstream', 'source'))):
                text = out_name.strip()
                key = text.lower()
                if text and key not in seen:
                    seen.add(key)
                    out.append(_normalize_chip(text[:160]))
        if target_agent and agent.id == target_agent.id:
            for sibling in agent.inputs:
                if sibling.lower() == target_low:
                    continue
                if any((m in sibling.lower() for m in _WIRED_INPUT_MARKERS)):
                    continue
                key = sibling.lower()
                if key not in seen:
                    seen.add(key)
                    out.append(_normalize_chip(sibling))
        note = (agent.notes or '').strip()
        if note and target_agent and (agent.id == target_agent.id):
            key = note.lower()
            if key not in seen:
                seen.add(key)
                out.append(_normalize_chip(note[:160]))
    return out[:limit]

def _options_for_field(field_key: str, agents: list[AgentRecord], projects: list[ProjectRecord], state: CascadingSelectionState, target_agent: AgentRecord | None, *, catalog_agents: list[AgentRecord] | None=None) -> list[str]:
    qid = field_key.split(':', 1)[1] if field_key.startswith(CLARIFYING_FIELD_PREFIX) else ''
    if field_key.startswith(DISCOVERY_FIELD_PREFIX):
        topic = field_key[len(DISCOVERY_FIELD_PREFIX):].split(':')[0]
        project = projects[0] if projects else None
        if topic in ('workflow_domain', 'domain'):
            opts = _workflow_domain_options(agents)
        elif topic in ('deployment_context', 'deployment'):
            opts = _deployment_options(agents)
        elif topic in ('hitl_review_policy', 'hitl', 'review'):
            opts = _hitl_chips_from_catalog(project, agents)
        elif topic in ('integrations_systems', 'integrations'):
            opts = _distinct_integrations(agents)
        elif topic in ('output_deliverables', 'outputs'):
            opts = _distinct_outputs(agents)
        elif topic in ('input_types', 'inputs', 'data_sources'):
            opts = _distinct_inputs(agents) + _distinct_integrations(agents, limit=3)
        else:
            opts = _distinct_inputs(agents) + _hitl_chips_from_catalog(project, agents)[:3] + _distinct_integrations(agents, limit=3)
    elif field_key.startswith(CLARIFYING_FIELD_PREFIX):
        if qid == 'q1':
            opts = _distinct_inputs(agents) + _distinct_integrations(agents, limit=4)
        elif qid == 'q2':
            project = projects[0] if projects else None
            opts = _hitl_chips_from_catalog(project, agents)
        elif qid == 'q3':
            opts = _distinct_integrations(agents)
        else:
            opts = _distinct_inputs(agents)
    elif field_key == 'hitl_behavior':
        project = projects[0] if projects else None
        opts = _hitl_chips_from_catalog(project, agents)
    elif field_key == 'integrations':
        opts = _distinct_integrations(agents)
    elif field_key == 'architectural_flow':
        opts = _flow_chains_from_agents(agents)
        for project in projects:
            summary = (project.solution_summary or '').strip()
            if summary:
                opts.append(_normalize_chip(summary[:160]))
    elif field_key == 'core_components':
        opts = _distinct_agent_names(agents) + _distinct_categories(agents)
    elif field_key == 'data_flow':
        opts = _distinct_outputs(agents)
    elif field_key == 'orchestration_model':
        opts = _flow_chains_from_agents(agents) + _distinct_agent_names(agents, limit=4)
    elif field_key.startswith(AGENT_INPUT_PREFIX) and state.target_input_name:
        opts = _agent_input_options(agents, state.target_input_name, target_agent, catalog_agents=catalog_agents)
    else:
        opts = _distinct_inputs(agents) + _distinct_integrations(agents, limit=3)
    return _dedupe_chips(opts)

def build_selection_state(*, problem_statement: str, target_field: str, clarifying_answers: dict[str, str] | None=None, workflow_answers: dict[str, str] | None=None, spec: Optional['ArchitectureSpec']=None, preferred_agent_ids: list[str] | None=None, target_agent_id: str | None=None, target_input_name: str | None=None) -> CascadingSelectionState:
    spec_answers: dict[str, str] = {}
    if spec:
        for key in USER_INTERVIEW_FIELD_KEYS:
            field = spec.fields.get(key)
            if field and field.value and str(field.value).strip():
                spec_answers[key] = str(field.value).strip()
    return CascadingSelectionState(problem_statement=problem_statement, clarifying_answers=dict(clarifying_answers or {}), workflow_answers=dict(workflow_answers or {}), spec_field_answers=spec_answers, preferred_agent_ids=list(preferred_agent_ids or []), target_field=target_field, target_agent_id=target_agent_id, target_input_name=target_input_name)

def generate_cascading_options(field_key: str, query: str, settings: Settings, *, clarifying_answers: dict[str, str] | None=None, workflow_answers: dict[str, str] | None=None, spec: Optional['ArchitectureSpec']=None, preferred_agent_ids: list[str] | None=None, target_agent_id: str | None=None, target_input_name: str | None=None, limit: int=5) -> CascadingOptionResult:
    """Generate runtime options for one interview field from filtered catalog rows."""
    catalog = _load_catalog(settings)
    state = build_selection_state(problem_statement=query, target_field=field_key, clarifying_answers=clarifying_answers, workflow_answers=workflow_answers, spec=spec, preferred_agent_ids=preferred_agent_ids, target_agent_id=target_agent_id, target_input_name=target_input_name)
    agents, projects, debug = filter_catalog_rows(catalog, state)
    target_agent = next((a for a in agents if a.id == target_agent_id), None)
    if target_agent_id and (not target_agent):
        target_agent = next((a for a in catalog.agents if a.id == target_agent_id), None)
    raw = _options_for_field(field_key, agents, projects, state, target_agent, catalog_agents=catalog.agents)
    ranked = _rank_chips(query, raw, field_key=field_key)[:max(limit, 1)]
    options = ranked[:limit] + [OTHER_CHIP]
    debug['target_field'] = field_key
    debug['generated_options'] = ranked[:limit]
    logger.info('cascading_options field=%s selections=%s rows=%d options=%s', field_key, debug.get('prior_selections'), len(agents), ranked[:limit])
    return CascadingOptionResult(options=options, debug=debug)

def generate_clarifying_options(question_id: str, query: str, settings: Settings, *, preferred_agent_ids: list[str] | None=None, prior_answers: dict[str, str] | None=None, limit: int=4) -> CascadingOptionResult:
    field_key = f'{CLARIFYING_FIELD_PREFIX}{question_id}'
    return generate_cascading_options(field_key, query, settings, clarifying_answers=prior_answers, preferred_agent_ids=preferred_agent_ids, limit=limit)


# ========================================================================
# services/question_planner.py
# ========================================================================


"""
Gap-driven question planner for workflow discovery.

Flow:
  understand_goal() → extract_knowns() → extract_unknowns() → rank_unknowns() → ask_best_question()
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional
logger = logging.getLogger(__name__)
REQUIREMENT_SLOTS: tuple[str, ...] = ('workflow_domain', 'input_types', 'data_sources', 'hitl_review_policy', 'integrations_systems', 'output_deliverables', 'deployment_context', 'domain_constraints')
_ARCHITECTURAL_IMPACT: dict[str, int] = {'workflow_domain': 95, 'input_types': 82, 'data_sources': 78, 'hitl_review_policy': 74, 'integrations_systems': 72, 'output_deliverables': 66, 'deployment_context': 52, 'domain_constraints': 58}
_UNLOCKS: dict[str, tuple[str, ...]] = {'workflow_domain': ('input_types', 'data_sources', 'integrations_systems', 'output_deliverables', 'domain_constraints'), 'input_types': ('integrations_systems', 'data_sources'), 'data_sources': ('integrations_systems',), 'output_deliverables': ('deployment_context', 'integrations_systems')}
_SOFT_DEPS: dict[str, tuple[str, ...]] = {'input_types': ('workflow_domain',), 'integrations_systems': ('input_types', 'data_sources'), 'hitl_review_policy': ('workflow_domain',), 'deployment_context': ('integrations_systems',)}
_SLOT_LABELS: dict[str, str] = {'workflow_domain': 'Business domain and use-case vertical', 'input_types': 'Input types and formats', 'data_sources': 'Where source data and images come from', 'hitl_review_policy': 'Human review and approval policy', 'integrations_systems': 'External systems to connect', 'output_deliverables': 'Final outputs and deliverables', 'deployment_context': 'Where the workflow will run', 'domain_constraints': 'Domain rules, compliance, and constraints'}
_QUESTION_TEMPLATES: dict[str, str] = {'workflow_domain': 'Which domain best describes this workflow — for example fashion and apparel, jewelry, eyewear, retail shelf analytics, documents/KYC, or something else?', 'input_types': 'What will users provide as inputs — for example person photos, product images, documents, chat messages, or data feeds?', 'data_sources': 'Where should the workflow pull its source data from today?', 'hitl_review_policy': 'When should a human review step be required — always, only on exceptions or low confidence, or fully automatic?', 'integrations_systems': 'Which systems must this workflow connect to for inputs and outputs?', 'output_deliverables': 'What should the workflow deliver when it finishes?', 'deployment_context': 'Where should this run — cloud SaaS, internal Azure/AWS, on-prem, or standalone?', 'domain_constraints': 'Are there domain rules we must follow — compliance, brand guidelines, latency limits, or data residency?'}
_WHY_TEMPLATES: dict[str, str] = {'workflow_domain': 'Domain drives which catalog agents, vision models, and pipeline patterns apply — fashion try-on differs sharply from jewelry, eyewear, or document workflows.', 'input_types': 'Input format determines ingestion agents and how images or files are validated.', 'data_sources': 'Knowing where data lives defines integrations and retrieval agents in the pipeline.', 'hitl_review_policy': 'Review policy sets human-in-the-loop gates in the architecture.', 'integrations_systems': 'Integrations define how the workflow talks to catalogs, CRMs, storage, and APIs.', 'output_deliverables': 'Outputs determine the last mile — notifications, files, APIs, or dashboards.', 'deployment_context': 'Deployment affects orchestration, security boundaries, and infrastructure agents.', 'domain_constraints': 'Constraints shape compliance checks, escalation rules, and acceptable trade-offs.'}
_DOMAIN_SIGNALS: dict[str, tuple[str, ...]] = {'fashion_apparel': ('try-on', 'try on', 'vto', 'virtual try', 'garment', 'apparel', 'fashion', 'clothing', 'outfit'), 'jewelry': ('jewelry', 'jewellery', 'ring', 'necklace', 'bracelet'), 'eyewear': ('eyewear', 'glasses', 'sunglasses', 'frames'), 'retail_shelf': ('shelf', 'planogram', 'out-of-stock', 'oos', 'retail audit'), 'documents_kyc': ('kyc', 'onboarding', 'compliance', 'pdf', 'invoice', 'document'), 'chat_copilot': ('chatbot', 'copilot', 'chat', 'assistant', 'q&a')}
_KNOWN_CONFIDENCE_THRESHOLD = 0.68

@dataclass
class GoalUnderstanding:
    raw_goal: str = ''
    inferred_domains: list[str] = field(default_factory=list)
    domain_confidence: float = 0.0
    signals: list[str] = field(default_factory=list)

@dataclass
class RequirementGap:
    key: str
    label: str
    architectural_impact: float
    uncertainty_reduction: float
    dependency_unlock: float
    composite_score: float
    question: str
    why: str
    blocked_by: list[str] = field(default_factory=list)

@dataclass
class PlannerResult:
    goal: GoalUnderstanding
    knowns: list[ExtractedRequirement]
    unknowns: list[RequirementGap]
    best: Optional[RequirementGap]
    is_complete: bool
    missing_labels: list[str] = field(default_factory=list)

def understand_goal(text: str) -> GoalUnderstanding:
    """Parse the user's goal and infer weak domain signals."""
    raw = (text or '').strip()
    low = raw.lower()
    hits: list[tuple[str, int]] = []
    for domain, patterns in _DOMAIN_SIGNALS.items():
        score = sum((1 for p in patterns if p in low))
        if score:
            hits.append((domain, score))
    hits.sort(key=lambda x: (-x[1], x[0]))
    inferred = [d for d, _ in hits[:3]]
    top_score = hits[0][1] if hits else 0
    confidence = min(0.9, 0.35 + top_score * 0.15) if top_score else 0.0
    return GoalUnderstanding(raw_goal=raw, inferred_domains=inferred, domain_confidence=confidence, signals=inferred)

def extract_knowns(state: DiscoveryState, goal: GoalUnderstanding) -> list[ExtractedRequirement]:
    """Requirements already established from goal, answers, or inference."""
    known: dict[str, ExtractedRequirement] = {}
    for req in state.extracted_requirements:
        if req.value.strip() and req.confidence >= _KNOWN_CONFIDENCE_THRESHOLD:
            known[req.key] = req
    for ans in state.answers:
        if ans.topic and ans.answer.strip() and (ans.answer != '(skipped)'):
            known[ans.topic] = ExtractedRequirement(key=ans.topic, value=ans.answer.strip(), confidence=0.92, source='user_answer')
    for topic in state.covered_topics:
        if topic not in known:
            known[topic] = ExtractedRequirement(key=topic, value='(covered)', confidence=0.75, source='inferred')
    if goal.inferred_domains and goal.domain_confidence >= _KNOWN_CONFIDENCE_THRESHOLD:
        known['workflow_domain'] = ExtractedRequirement(key='workflow_domain', value=', '.join(goal.inferred_domains), confidence=goal.domain_confidence, source='problem_statement')
    elif goal.inferred_domains and goal.domain_confidence >= 0.45:
        known.setdefault('workflow_domain', ExtractedRequirement(key='workflow_domain', value=', '.join(goal.inferred_domains), confidence=goal.domain_confidence, source='inferred'))
    low = goal.raw_goal.lower()
    for slot, patterns in _heuristic_patterns().items():
        if slot in known and known[slot].confidence >= _KNOWN_CONFIDENCE_THRESHOLD:
            continue
        hits = sum((1 for p in patterns if p in low))
        if hits >= 2 or (hits == 1 and len(low) > 70):
            prev = known.get(slot)
            conf = 0.5 + min(hits * 0.12, 0.3)
            if not prev or prev.confidence < conf:
                known[slot] = ExtractedRequirement(key=slot, value=goal.raw_goal[:180], confidence=conf, source='problem_statement')
    return list(known.values())

def _heuristic_patterns() -> dict[str, tuple[str, ...]]:
    return {'input_types': ('photo', 'image', 'upload', 'pdf', 'document', 'chat', 'message'), 'hitl_review_policy': ('review', 'human', 'analyst', 'approve', 'hitl'), 'integrations_systems': ('shopify', 'crm', 'email', 'database', 'blob', 'api', 'salesforce'), 'output_deliverables': ('deliver', 'output', 'report', 'notify', 'generate'), 'deployment_context': ('azure', 'aws', 'cloud', 'on-prem', 'saas', 'deploy')}

def _is_slot_satisfied(key: str, knowns: dict[str, ExtractedRequirement]) -> bool:
    req = knowns.get(key)
    if not req:
        return False
    if req.value == '(covered)':
        return True
    return req.confidence >= _KNOWN_CONFIDENCE_THRESHOLD

def extract_unknowns(goal: GoalUnderstanding, knowns: list[ExtractedRequirement]) -> list[str]:
    """Return requirement slot keys that are still missing."""
    known_map = {k.key: k for k in knowns}
    unknown: list[str] = []
    for slot in REQUIREMENT_SLOTS:
        if not _is_slot_satisfied(slot, known_map):
            unknown.append(slot)
    return unknown

def _uncertainty_score(slot: str, known: ExtractedRequirement | None) -> float:
    if known is None:
        return 92.0
    if known.confidence < 0.45:
        return 88.0
    if known.confidence < _KNOWN_CONFIDENCE_THRESHOLD:
        return 70.0
    return 25.0

def _dependency_unlock_score(slot: str, unknown_slots: set[str]) -> float:
    """How many still-unknown requirements does answering this slot unlock?"""
    unlocks = _UNLOCKS.get(slot, ())
    if not unlocks:
        return 35.0
    count = sum((1 for u in unlocks if u in unknown_slots))
    return min(100.0, 30.0 + count * 22.0)

def _dependency_penalty(slot: str, known_map: dict[str, ExtractedRequirement]) -> float:
    """Reduce score when soft prerequisites are still unknown."""
    deps = _SOFT_DEPS.get(slot, ())
    if not deps:
        return 0.0
    missing = sum((1 for d in deps if not _is_slot_satisfied(d, known_map)))
    return missing * 18.0

def rank_unknowns(goal: GoalUnderstanding, knowns: list[ExtractedRequirement], unknown_keys: list[str]) -> list[RequirementGap]:
    known_map = {k.key: k for k in knowns}
    unknown_set = set(unknown_keys)
    gaps: list[RequirementGap] = []
    for key in unknown_keys:
        impact = float(_ARCHITECTURAL_IMPACT.get(key, 60))
        uncertainty = _uncertainty_score(key, known_map.get(key))
        unlock = _dependency_unlock_score(key, unknown_set)
        penalty = _dependency_penalty(key, known_map)
        composite = 0.45 * impact + 0.35 * uncertainty + 0.2 * unlock - penalty
        blocked = [d for d in _SOFT_DEPS.get(key, ()) if not _is_slot_satisfied(d, known_map)]
        gaps.append(RequirementGap(key=key, label=_SLOT_LABELS.get(key, key), architectural_impact=impact, uncertainty_reduction=uncertainty, dependency_unlock=unlock, composite_score=composite, question=_QUESTION_TEMPLATES.get(key, f'Can you clarify {key}?'), why=_WHY_TEMPLATES.get(key, 'Reduces ambiguity for agent selection.'), blocked_by=blocked))
    gaps.sort(key=lambda g: (-g.composite_score, g.key))
    return gaps

def ask_best_question(ranked: list[RequirementGap]) -> Optional[RequirementGap]:
    return ranked[0] if ranked else None

def plan_discovery_question(state: DiscoveryState, *, problem_statement: str='') -> PlannerResult:
    """
    Full planner pipeline for one discovery turn.
    """
    goal = understand_goal(problem_statement or state.original_request)
    knowns = extract_knowns(state, goal)
    unknown_keys = extract_unknowns(goal, knowns)
    ranked = rank_unknowns(goal, knowns, unknown_keys)
    best = ask_best_question(ranked)
    core = {'workflow_domain', 'input_types', 'hitl_review_policy', 'integrations_systems'}
    known_map = {k.key: k for k in knowns}
    core_satisfied = all((_is_slot_satisfied(k, known_map) for k in core))
    is_complete = not ranked or (core_satisfied and len(unknown_keys) <= 1)
    missing_labels = [_SLOT_LABELS.get(k, k) for k in unknown_keys]
    if best:
        logger.info('question_planner best=%s score=%.1f impact=%.0f uncertainty=%.0f unlock=%.0f unknowns=%s', best.key, best.composite_score, best.architectural_impact, best.uncertainty_reduction, best.dependency_unlock, unknown_keys)
    return PlannerResult(goal=goal, knowns=knowns, unknowns=ranked, best=best, is_complete=is_complete, missing_labels=missing_labels)

def planner_result_to_plan_dict(result: PlannerResult) -> dict[str, Any]:
    """Convert planner output to discovery step plan format."""
    if result.is_complete or not result.best:
        return {'is_complete': True, 'current_understanding': result.goal.raw_goal[:400], 'missing_information': result.missing_labels, 'extracted_requirements': [r.model_dump() for r in result.knowns if r.confidence >= 0.5]}
    best = result.best
    return {'is_complete': False, 'current_understanding': result.goal.raw_goal[:400], 'missing_information': result.missing_labels, 'next_question': best.question, 'topic': best.key, 'why_this_question': best.why, 'skip_topics': [r.key for r in result.knowns if r.confidence >= _KNOWN_CONFIDENCE_THRESHOLD], 'extracted_requirements': [r.model_dump() for r in result.knowns if r.confidence >= 0.5], 'planner_scores': {'composite': best.composite_score, 'architectural_impact': best.architectural_impact, 'uncertainty_reduction': best.uncertainty_reduction, 'dependency_unlock': best.dependency_unlock, 'ranked_topics': [{'key': g.key, 'score': round(g.composite_score, 1), 'impact': g.architectural_impact} for g in result.unknowns[:6]]}}

def polish_question_with_llm(question: str, *, goal: str, topic: str, settings: Any, client: Any) -> str:
    """Optional: natural-language polish while keeping the same topic intent."""
    system = f'Rewrite this scoping question in one conversational sentence. Keep the same meaning and topic. Do not add new topics. Plain text only.\nTopic: {topic}\nWorkflow goal: {goal[:800]}'
    try:
        polished = call_llm(client, settings, system, question, temperature=0.3).strip()
        if polished and len(polished) > 15:
            return polished
    except Exception as exc:
        logger.debug('Question polish skipped: %s', exc)
    return question


# ========================================================================
# services/interview_intents.py
# ========================================================================


"""Detect meta-intents in free-text interview answers."""
import re
_CHANGE_PROBLEM_PATTERNS: tuple[re.Pattern[str], ...] = (re.compile('\\b(change|edit|update|revise|redo|replace|restart)\\s+(?:the\\s+|my\\s+|our\\s+|a\\s+)?(problem\\s*statement|workflow)\\b', re.I), re.compile('\\b(want|need)\\s+to\\s+(change|edit|update|revise|redo|replace|restart)\\s+(?:the\\s+|my\\s+|our\\s+)?(problem\\s*statement|workflow)\\b', re.I), re.compile('\\b(start\\s+over|begin\\s+again|new\\s+problem\\s*statement)\\b', re.I))
_EXTRACT_AFTER_MARKER = re.compile('(?:problem\\s*statement|new\\s+(?:prompt|description|request))\\s*[:—-]\\s*(.+)', re.I | re.S)
_HELP_QUESTION_PATTERNS: tuple[re.Pattern[str], ...] = (re.compile('^\\s*(what|how|can|could|should|which|where|when|why|is|are|do|does)\\b', re.I), re.compile('\\b(what\\s+(problem\\s+statement|should\\s+i|can\\s+i|do\\s+i)|help\\s+me|give\\s+me\\s+(an?\\s+)?example|any\\s+examples?|what\\s+to\\s+write|how\\s+to\\s+(write|describe))\\b', re.I), re.compile('\\?\\s*$'))
_GENERAL_HELP_PATTERNS: tuple[re.Pattern[str], ...] = (re.compile('\\bhelp\\b', re.I), re.compile('\\bexample\\b', re.I), re.compile('\\bexamples\\b', re.I), re.compile('\\bsample\\b', re.I), re.compile('\\bsamples\\b', re.I), re.compile('\\bguide\\b', re.I), re.compile('\\bguidance\\b', re.I), re.compile('\\bexplain\\b', re.I), re.compile('\\bmeaning\\b', re.I), re.compile('^\\s*what\\b', re.I), re.compile('^\\s*why\\b', re.I), re.compile('^\\s*how\\b', re.I), re.compile('^\\s*can\\b', re.I), re.compile('^\\s*could\\b', re.I), re.compile('^\\s*should\\b', re.I), re.compile('\\bwhat\\s+answers\\b', re.I), re.compile('\\bwhat\\s+can\\s+you\\b', re.I), re.compile('\\bwhat\\s+can\\s+i\\b', re.I), re.compile('\\bshow\\s+me\\b', re.I), re.compile('\\bgive\\s+me\\b', re.I), re.compile('\\bworkflow\\s+example\\b', re.I), re.compile('\\bworkflow\\s+examples\\b', re.I), re.compile('\\bproblem\\s+statement\\b', re.I))
_WORKFLOW_SIGNAL_WORDS: frozenset[str] = frozenset({'build', 'workflow', 'agent', 'agentic', 'automate', 'accept', 'generate', 'review', 'upload', 'process', 'extract', 'analyze', 'create', 'pipeline', 'integrate', 'validate', 'deliver', 'notify', 'chatbot', 'copilot', 'bot', 'data', 'structured', 'unstructured'})
_BUILD_GOAL_RE = re.compile('\\b(build|create|design|make|develop|automate)\\b.{0,60}\\b(chatbot|chat\\s*bot|copilot|workflow|pipeline|agent|bot|assistant)\\b', re.I)

def is_scoping_conversation_question(text: str) -> bool:
    """
    User is asking a question during scoping (not answering the pending question).
    E.g. "what is Shelf Layout Compliance?", "what do you mean by that?"
    """
    raw = (text or '').strip()
    if not raw:
        return False
    if is_change_problem_statement_intent(raw):
        return False
    if is_pending_question_help_request(raw):
        return False
    low = raw.lower()
    if any((phrase in low for phrase in ('what do you mean', "don't know what you mean", 'do not know what you mean', "i don't know what", 'what does that mean', 'what does this mean', 'can you explain', 'explain what', 'explain that'))):
        return True
    if re.search('^\\s*what (is|are|does|was)\\b', low):
        return True
    if re.search('^\\s*(who|why|how) (is|are|does|do)\\b', low) and '?' in raw:
        return True
    if low.endswith('?') and re.search('\\b(what|who|why|how|explain)\\b', low):
        return True
    return False

def is_decline_to_answer(text: str) -> bool:
    """User does not want to answer the current scoping question."""
    raw = (text or '').strip()
    if not raw:
        return False
    if is_scoping_conversation_question(raw):
        return False
    low = raw.lower()
    return any((phrase in low for phrase in ("don't want to say", 'do not want to say', "don't want to answer", 'prefer not to say', 'skip this', 'skip that', 'pass on this', 'rather not', 'no comment')))

def is_pending_question_help_request(text: str) -> bool:
    """User wants help or options for the current interview question."""
    raw = (text or '').strip()
    if not raw:
        return False
    low = raw.lower()
    if any((phrase in low for phrase in ('give me options', 'give options', 'show options', 'what are my options', 'what can i answer', 'what should i answer', 'what do i answer', 'how do i answer', 'what can i pick', 'what can i choose', 'you give me options'))):
        return True
    return bool(re.search('\\b(options?|choices?)\\b', low)) and '?' not in low

def is_revision_help_question(text: str) -> bool:
    """
    User is asking how to write a problem statement.
    """
    raw = (text or '').strip()
    if not raw:
        return False
    if is_pending_question_help_request(raw):
        return False
    low = raw.lower()
    if any((phrase in low for phrase in ('answer this', 'this question', 'current question', 'options'))):
        return False
    if any((p.search(raw) for p in _HELP_QUESTION_PATTERNS)):
        return True
    return '?' in raw and any((phrase in low for phrase in ('problem statement', 'what should', 'what can', 'example', 'help')))

def is_general_help_request(text: str) -> bool:
    """
    Detect generic help requests that should NOT
    modify workflow state.
    """
    raw = (text or '').strip()
    if not raw:
        return False
    if looks_like_problem_statement(raw):
        return False
    if is_change_problem_statement_intent(raw):
        return False
    low = raw.lower()
    if re.search('\\b(change|edit|update|revise|redo|replace|restart|start\\s+over)\\b', low) and re.search('\\bproblem\\b', low):
        return False
    return any((p.search(raw) for p in _GENERAL_HELP_PATTERNS))
_EXPLICIT_BUILD_PATTERNS: tuple[re.Pattern[str], ...] = (re.compile('\\b(build|create|design|automate|set\\s*up|scope)\\b.{0,40}\\b(workflow|pipeline|agent|agents|agentic|copilot|bot)\\b', re.I), re.compile("\\b(let'?s|i\\s+want\\s+to)\\s+(build|automate|scope|design)\\b", re.I))

def should_begin_workflow_building(text: str) -> bool:
    """True when the user is describing requirements, not just asking questions."""
    raw = (text or '').strip()
    if not raw:
        return False
    if is_revision_help_question(raw) or is_general_help_request(raw):
        return False
    if looks_like_problem_statement(raw):
        return True
    return any((pattern.search(raw) for pattern in _EXPLICIT_BUILD_PATTERNS))

def looks_like_problem_statement(text: str) -> bool:
    """
    Detect actual workflow descriptions.
    """
    raw = (text or '').strip()
    if len(raw) < 20:
        return False
    if is_revision_help_question(raw):
        return False
    if is_change_problem_statement_intent(raw):
        return False
    low = raw.lower()
    if _BUILD_GOAL_RE.search(raw):
        return True
    workflow_hits = sum((1 for word in _WORKFLOW_SIGNAL_WORDS if word in low))
    if workflow_hits >= 2:
        return True
    if workflow_hits >= 1 and len(raw) >= 25:
        return True
    if len(raw) >= 80 and '?' not in raw:
        return True
    return False

def is_problem_revision_submission(text: str) -> bool:
    """
    True when the user pasted a new workflow goal during problem revision.
    Permissive — revision mode should accept real goals, not loop on format.
    """
    raw = (text or '').strip()
    if len(raw) < 10:
        return False
    if is_revision_help_question(raw):
        return False
    if is_change_problem_statement_intent(raw) and len(raw) < 50:
        return False
    if raw.endswith('?') and len(raw) < 60 and (not looks_like_problem_statement(raw)):
        return False
    if looks_like_problem_statement(raw):
        return True
    low = raw.lower()
    if any((verb in low for verb in ('build', 'create', 'automate', 'design', 'make', 'develop'))):
        return True
    return len(raw) >= 20 and '?' not in raw

def is_change_problem_statement_intent(text: str) -> bool:
    """
    Only trigger when user EXPLICITLY wants
    to replace the workflow description.
    """
    raw = (text or '').strip()
    if not raw:
        return False
    return any((pattern.search(raw) for pattern in _CHANGE_PROBLEM_PATTERNS))

def extract_revised_problem_statement(text: str) -> str | None:
    """
    Only extract when user explicitly provides
    a new problem statement.
    """
    raw = (text or '').strip()
    if not raw:
        return None
    match = _EXTRACT_AFTER_MARKER.search(raw)
    if not match:
        return None
    body = match.group(1).strip()
    if looks_like_problem_statement(body):
        return body
    return None

def problem_statement_guidance_text() -> str:
    return "A problem statement is a short description of what you want automated — what goes in, what should happen, and what comes out (including human review if needed).\n\nExamples:\n• Build a workflow that accepts invoices, extracts fields, validates them against purchase orders, and routes exceptions to finance.\n• Build a workflow that accepts claim forms and accident photos, detects fraud indicators, and escalates suspicious claims for review.\n• Build a workflow that screens resumes, ranks candidates, and generates interview questions.\n\nPaste your workflow description below and I'll continue scoping."


# ========================================================================
# services/interview_turn_intent.py
# ========================================================================


"""
Classify user messages during scoping before advancing interview state.

Only ANSWER (and explicit FINISH / DECLINE) may progress the interview.
"""
import re
from enum import Enum
_FINISH_RE = re.compile('^\\s*(finish|done|complete|ready)\\s*\\.?\\s*$', re.I)
_GREETING_RE = re.compile('^\\s*(hi|hello|hey|good\\s+(morning|afternoon|evening)|howdy)\\b[!.?\\s]*$', re.I)
_CLARIFICATION_PHRASES: tuple[str, ...] = ('explain this', 'explain that', 'explain the question', 'explain it', 'what do you mean', 'what does this mean', 'what does that mean', 'why are you asking', 'why do you need', 'why does this matter', 'why is this important', 'can you explain', 'help me understand', "i don't understand", 'i dont understand', "don't know what you mean", 'do not know what you mean', 'what should i put', 'what should i say', 'give me examples', 'give examples', 'show examples', 'can you give examples', 'what are examples', 'not sure what to answer', 'unclear what you want')
_TECH_CHOICE_MARKERS: tuple[str, ...] = ('azure openai', 'gemini', 'gpt-', 'openai', 'model-version', 'httpx', 'env (', 'vectorize', 'embedding api')

class TurnIntent(str, Enum):
    ANSWER = 'ANSWER'
    CLARIFICATION_REQUEST = 'CLARIFICATION_REQUEST'
    QUESTION = 'QUESTION'
    UNKNOWN = 'UNKNOWN'
    GREETING = 'GREETING'
    DECLINE = 'DECLINE'
    FINISH = 'FINISH'
    CHANGE_PROBLEM = 'CHANGE_PROBLEM'

def _normalize(text: str) -> str:
    return (text or '').strip()

def is_clarification_request(text: str, session: InterviewSession | None=None) -> bool:
    raw = _normalize(text)
    if not raw:
        return False
    low = raw.lower()
    if any((phrase in low for phrase in _CLARIFICATION_PHRASES)):
        return True
    if is_pending_question_help_request(raw):
        return True
    if re.search('\\bexplain\\b', low) and len(raw.split()) <= 6:
        return True
    if re.search('^\\s*why\\b', low) and len(raw) < 80:
        return True
    if session and session.pending_question:
        if low in ('help', 'help?', '?', 'huh', 'huh?'):
            return True
    return False

def _looks_like_chip_answer(text: str, session: InterviewSession) -> bool:
    pq = session.pending_question
    if not pq or not pq.chips:
        return False
    low = text.lower().strip()
    for chip in pq.chips:
        c = chip.lower().strip()
        if not c or c == 'other / describe in chat':
            continue
        if low == c or low in c or c in low:
            return True
    return False

def _looks_like_substantive_answer(text: str, session: InterviewSession) -> bool:
    raw = _normalize(text)
    if len(raw) < 2:
        return False
    if raw.endswith('?') and len(raw) < 100:
        return False
    if is_clarification_request(raw, session):
        return False
    if is_scoping_conversation_question(raw):
        return False
    if is_revision_help_question(raw):
        return False
    return True

def classify_turn_intent(text: str, session: InterviewSession) -> TurnIntent:
    """Classify one user message during workflow scoping."""
    raw = _normalize(text)
    if not raw:
        return TurnIntent.UNKNOWN
    if _GREETING_RE.match(raw):
        return TurnIntent.GREETING
    if is_change_problem_statement_intent(raw):
        return TurnIntent.CHANGE_PROBLEM
    if _FINISH_RE.match(raw):
        return TurnIntent.FINISH
    if is_decline_to_answer(raw):
        return TurnIntent.DECLINE
    if is_clarification_request(raw, session):
        return TurnIntent.CLARIFICATION_REQUEST
    if is_scoping_conversation_question(raw):
        return TurnIntent.QUESTION
    if session.pending_question:
        if _looks_like_chip_answer(raw, session):
            return TurnIntent.ANSWER
        if _looks_like_substantive_answer(raw, session):
            return TurnIntent.ANSWER
        if raw.endswith('?'):
            return TurnIntent.QUESTION
        return TurnIntent.UNKNOWN
    if is_revision_help_question(raw):
        return TurnIntent.CLARIFICATION_REQUEST
    return TurnIntent.UNKNOWN


# ========================================================================
# services/interview_conversation.py
# ========================================================================


"""
Conversational interview turn handling — state machine + architect-style responses.
"""
import logging
import re
from typing import TYPE_CHECKING
from openai import AzureOpenAI
if TYPE_CHECKING:
    pass
logger = logging.getLogger(__name__)
_DOMAIN_INTEGRATION_EXAMPLES: dict[str, list[str]] = {'retail': ['Shopify product catalog', 'Internal product database', 'User-uploaded product images', 'Digital asset management (DAM) system', 'E-commerce platform APIs', 'Azure Blob Storage for image files'], 'documents': ['SharePoint document library', 'User PDF uploads', 'Email attachments', 'Internal case management system', 'S3 or Azure Blob for document storage'], 'chat': ['User chat messages in the app', 'Slack or Teams', 'Website widget', 'CRM contact records', 'Internal knowledge base API'], 'general': ['User uploads in the application', 'Existing internal database', 'REST API data source', 'Cloud blob storage', 'Third-party SaaS platform', 'Standalone — no external system']}
_TECH_NOISE_RE = re.compile('\\b(azure\\s+openai|gemini|gpt-|openai|model-version|httpx|vectorize|embedding\\s+api|env\\s*\\(|controlled\\s+by\\s+\\w+_env)\\b', re.I)

def detect_workflow_domain(problem: str) -> str:
    low = (problem or '').lower()
    if any((w in low for w in ('try-on', 'try on', 'vto', 'garment', 'product image', 'person photo', 'retail', 'shopify', 'catalog'))):
        return 'retail'
    if any((w in low for w in ('chatbot', 'copilot', 'chat', 'assistant'))):
        return 'chat'
    if any((w in low for w in ('pdf', 'document', 'kyc', 'invoice', 'filing'))):
        return 'documents'
    return 'general'

def filter_domain_options(chips: list[str], *, problem_statement: str, topic: str='') -> list[str]:
    """Drop implementation/model noise; prefer business-meaningful options."""
    domain = detect_workflow_domain(problem_statement)
    out: list[str] = []
    seen: set[str] = set()
    for chip in chips:
        text = (chip or '').strip()
        if not text or is_other_chip(text):
            continue
        if topic in ('integrations_systems', 'integrations', 'data_sources', 'input_types'):
            if _TECH_NOISE_RE.search(text) or re.search('(_env\\b|env\\s*\\(|controlled\\s+by)', text, re.I):
                continue
        if len(text) > 90:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    if len(out) < 3 and topic in ('integrations_systems', 'integrations', 'data_sources'):
        for example in _DOMAIN_INTEGRATION_EXAMPLES.get(domain, []):
            key = example.lower()
            if key not in seen:
                seen.add(key)
                out.append(example)
    return out[:6]

def build_understanding_lists(session: InterviewSession) -> tuple[list[str], list[str]]:
    """Known requirements vs still unclear — for architect-style summaries."""
    known: list[str] = []
    unclear: list[str] = []
    goal = session.spec.problem_statement.strip()
    goal_lower = goal.lower()
    if goal:
        trimmed = goal[:160] + ('…' if len(goal) > 160 else '')
        known.append(f'Workflow goal: {trimmed}')
    state = session.discovery
    if state:
        for req in state.extracted_requirements:
            if req.confidence >= 0.5 and req.value.strip():
                val = req.value.strip()
                val_lower = val.lower()
                if goal_lower and (val_lower in goal_lower or goal_lower in val_lower):
                    continue
                label = req.key.replace('_', ' ')
                known.append(f'{label}: {val[:100]}')
        for ans in state.answers:
            if ans.answer.strip() and ans.answer != '(skipped)':
                known.append(ans.answer[:120])
        unclear = list(state.missing_information)
    if session.agent_workflow:
        for fk, val in session.agent_workflow.answers.items():
            if val.strip() and val != 'Not specified':
                known.append(val[:120])
    if not unclear and state:
        unclear = list(state.missing_information)
    seen: set[str] = set()
    known_unique: list[str] = []
    for item in known:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            known_unique.append(item)
    return (known_unique[:8], unclear[:6])

def format_architect_message(*, question: str, why: str='', examples: list[str] | None=None, known: list[str] | None=None, unclear: list[str] | None=None, include_question: bool=True) -> str:
    """ChatGPT-style architect response for asking or clarifying."""
    parts: list[str] = []
    if known:
        lines = '\n'.join((f'✓ {item}' for item in known[:6]))
        parts.append(f'Current understanding:\n{lines}')
    if unclear:
        lines = '\n'.join((f'? {item}' for item in unclear[:5]))
        parts.append(f'Still unclear:\n{lines}')
    if why:
        parts.append(f"Why I'm asking:\n{why}")
    if examples:
        lines = '\n'.join((f'• {ex}' for ex in examples[:6]))
        parts.append(f'Examples:\n{lines}')
    if include_question and question.strip():
        parts.append(f'Question:\n{question.strip()}')
    return '\n\n'.join(parts)

def _set_interview_phase(session: InterviewSession, phase: InterviewPhase) -> None:
    if session.discovery:
        session.discovery.interview_phase = phase
    logger.info('interview_phase -> %s session=%s', phase, session.id)

def _domain_examples_for_question(session: InterviewSession) -> list[str]:
    pq = session.pending_question
    if not pq:
        domain = detect_workflow_domain(session.spec.problem_statement)
        return _DOMAIN_INTEGRATION_EXAMPLES.get(domain, [])[:6]
    topic = ''
    if pq.field_key and ':' in pq.field_key:
        topic = pq.field_key.split(':')[1].split(':')[0]
    chips = filter_domain_options([c for c in pq.chips if not is_other_chip(c)], problem_statement=session.spec.problem_statement, topic=topic)
    if chips:
        return chips
    domain = detect_workflow_domain(session.spec.problem_statement)
    return _DOMAIN_INTEGRATION_EXAMPLES.get(domain, [])[:6]

def generate_clarification_response(user_message: str, session: InterviewSession, settings: Settings, client: AzureOpenAI) -> str:
    """Explain the current question without advancing the interview."""
    pq = session.pending_question
    if not pq:
        return "I'm here to help scope your workflow. Describe what you want to automate and I'll ask focused follow-up questions."
    known, unclear = build_understanding_lists(session)
    examples = _domain_examples_for_question(session)
    why = (pq.why_it_matters or '').strip()
    if session.discovery and session.discovery.last_question_reason:
        why = why or session.discovery.last_question_reason
    system = load_prompt('clarification_response.txt').replace('{user_goal}', session.spec.problem_statement[:1500]).replace('{known_items}', '\n'.join((f'- {k}' for k in known)) or '(starting)').replace('{unclear_items}', '\n'.join((f'- {u}' for u in unclear)) or '(none)').replace('{current_question}', pq.question).replace('{why_it_matters}', why or 'Narrows agents and integration design.').replace('{example_options}', '\n'.join((f'- {e}' for e in examples)) or '(domain examples)').replace('{user_message}', user_message.strip())
    try:
        body = call_llm(client, settings, system, "Respond to the user's clarification request.", temperature=0.35).strip()
        if body:
            _set_interview_phase(session, 'waiting_for_answer')
            return body
    except Exception as exc:
        logger.warning('Clarification LLM failed: %s', exc)
    return format_architect_message(question=pq.question, why=why or 'This helps me choose the right catalog agents and data interfaces.', examples=examples, known=known, unclear=unclear, include_question=True)

def format_new_question_message(session: InterviewSession, question: 'InterviewQuestion', *, why: str='') -> str:
    """Plain question text for chat — explanations only on explicit user request."""
    del session, why
    return question.question.strip()

def handle_greeting(session: InterviewSession) -> str:
    pq = session.pending_question
    if pq:
        return f"Hi! We're scoping your workflow — when you're ready, answer the question below or ask me to explain it.\n\n{pq.question}"
    return "Hi! Tell me what workflow you'd like to build and I'll help scope it."

def should_advance_interview(intent: TurnIntent) -> bool:
    return intent == TurnIntent.ANSWER


# ========================================================================
# services/clarifying_questions.py
# ========================================================================


"""Deterministic clarifying questions before the agent workflow interview."""
import logging
from typing import Optional
logger = logging.getLogger(__name__)

def clarifying_field_key(question_id: str) -> str:
    return f'{CLARIFYING_FIELD_PREFIX}{question_id}'

def is_clarifying_field_key(field_key: Optional[str]) -> bool:
    return bool(field_key and field_key.startswith(CLARIFYING_FIELD_PREFIX))

def _detect_problem_domain(query: str) -> str:
    q = query.lower()
    if any((w in q for w in ('chatbot', 'chat bot', ' copilot', 'copilot ', 'conversation', 'assistant', ' bot', 'bot ', 'build a bot'))):
        return 'chat'
    if any((w in q for w in ('image', 'photo', 'shelf', 'planogram', 'video', 'vision'))):
        return 'vision'
    if any((w in q for w in ('pdf', 'kyc', 'document', 'filing', 'compliance', 'onboarding'))):
        return 'documents'
    if any((w in q for w in ('fashion', 'garment', 'try-on', 'vto', 'retail'))):
        return 'retail'
    return 'general'

def _deterministic_clarifying_questions(query: str) -> list[ClarifyingQuestionItem]:
    """Same problem statement always yields the same three scoping questions."""
    domain = _detect_problem_domain(query)
    if domain == 'chat':
        q1 = 'What inputs will the chatbot receive — user messages only, uploaded files, or both?'
        q1_why = 'Input channels determine ingestion agents and context handling.'
    elif domain == 'vision':
        q1 = 'What visual inputs will this workflow use — shelf photos, planogram images, or product reference photos?'
        q1_why = 'Image type selects the vision detection and search agents.'
    elif domain == 'documents':
        q1 = 'What document types will users upload — PDF, DOCX, TXT, or a mix?'
        q1_why = 'Document format drives extraction and validation agents.'
    elif domain == 'retail':
        q1 = 'What reference inputs are required — person photos, product images, or catalog metadata?'
        q1_why = 'Reference inputs define the vision and composition pipeline.'
    else:
        q1 = 'What is the primary input for this workflow — documents, images, data feeds, or chat messages?'
        q1_why = 'Input type determines which ingestion agents are selected.'
    q2 = 'When should a human review step be required — always, only on exceptions, or never?'
    q2_why = 'Review policy sets HITL gates in the architecture.'
    q3 = 'Which systems must this workflow connect to for inputs and outputs — email, CRM, database, or standalone only?'
    q3_why = 'Integrations define data interfaces between agents.'
    return [ClarifyingQuestionItem(id='q1', question=q1, why_it_matters=q1_why), ClarifyingQuestionItem(id='q2', question=q2, why_it_matters=q2_why), ClarifyingQuestionItem(id='q3', question=q3, why_it_matters=q3_why)]

def chips_for_clarifying_question(question_id: str, query: str, settings: Settings, *, preferred_agent_ids: list[str] | None=None, prior_answers: dict[str, str] | None=None) -> list[str]:
    """Runtime options from catalog rows filtered by prior clarifying selections."""
    result = generate_clarifying_options(question_id, query, settings, preferred_agent_ids=preferred_agent_ids, prior_answers=prior_answers)
    logger.debug('clarifying chips debug: %s', result.debug)
    return result.options

def generate_clarifying_questions(raw_query: str, settings: Settings, client=None, *, catalog_context: str='') -> list[ClarifyingQuestionItem]:
    """
    Return three deterministic scoping questions for the problem statement.

    Same query always produces the same questions (no LLM variance).
    """
    del settings, client, catalog_context
    statement = raw_query.strip()
    if len(statement) < 10:
        raise ValueError('Problem statement must be at least 10 characters')
    questions = _deterministic_clarifying_questions(statement)
    logger.info('Clarifying questions (deterministic, domain=%s): %d', _detect_problem_domain(statement), len(questions))
    return questions

def format_clarifying_summary(questions: list[ClarifyingQuestionItem], answers: dict[str, str]) -> str:
    """Build text block injected into spec context after clarifying phase."""
    lines = ['Business clarifications (pre-architecture):']
    for q in questions:
        ans = answers.get(q.id, '').strip() or '(no answer)'
        lines.append(f'- Q ({q.id}): {q.question}')
        lines.append(f'  A: {ans}')
        if q.why_it_matters:
            lines.append(f'  (shapes architecture because: {q.why_it_matters})')
    return '\n'.join(lines)

def pending_clarifying_question(questions: list[ClarifyingQuestionItem], answers: dict[str, str]) -> Optional[ClarifyingQuestionItem]:
    """Return the next clarifying question not yet answered."""
    for q in questions:
        if q.id not in answers or not answers[q.id].strip():
            return q
    return None


# ========================================================================
# services/discovery_engine.py
# ========================================================================


"""
State-driven discovery interview — ChatGPT-style scoping over catalog data.

Replaces fixed clarifying questionnaires with context-aware question planning.
"""
import json
import logging
import re
from typing import TYPE_CHECKING, Any, Optional
from openai import AzureOpenAI
if TYPE_CHECKING:
    pass
logger = logging.getLogger(__name__)
_TOKEN_RE = re.compile('[a-z0-9]{3,}')
_TOPIC_LABELS: dict[str, str] = {'workflow_domain': 'Domain', 'input_types': 'Inputs', 'output_deliverables': 'Outputs', 'hitl_review_policy': 'Human review', 'integrations_systems': 'Integrations', 'data_sources': 'Data sources', 'deployment_context': 'Deployment', 'domain_constraints': 'Constraints', 'other': 'Scope'}
_HEURISTIC_TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {'input_types': ('upload', 'document', 'pdf', 'image', 'photo', 'chat', 'message', 'file', 'feed', 'api'), 'hitl_review_policy': ('review', 'human', 'analyst', 'approve', 'hitl', 'manual', 'escalat'), 'integrations_systems': ('email', 'crm', 'salesforce', 'database', 'slack', 'teams', 'sap', 'azure', 'sharepoint'), 'output_deliverables': ('report', 'deliver', 'output', 'notify', 'dashboard', 'export', 'generate')}

def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or '').lower()))

def _log_debug(state: DiscoveryState, event: str, **payload: Any) -> None:
    entry = {'event': event, **payload}
    state.debug_entries.append(entry)
    logger.info('discovery.%s %s', event, payload)

def _format_transcript(messages: list[ChatMessage], *, limit: int=24) -> str:
    lines: list[str] = []
    for msg in messages[-limit:]:
        role = 'User' if msg.role == 'user' else 'Assistant'
        text = (msg.content or '').strip()
        if text:
            lines.append(f'{role}: {text[:600]}')
    return '\n'.join(lines) or '(no messages yet)'

def _format_requirements(state: DiscoveryState) -> str:
    if not state.extracted_requirements:
        return '(none yet)'
    return '\n'.join((f'- {r.key}: {r.value} (confidence {r.confidence:.2f}, {r.source})' for r in state.extracted_requirements))

def _merge_requirements(state: DiscoveryState, incoming: list[dict[str, Any]]) -> None:
    by_key: dict[str, ExtractedRequirement] = {r.key: r for r in state.extracted_requirements}
    for raw in incoming:
        if not isinstance(raw, dict):
            continue
        key = str(raw.get('key', '')).strip()
        value = str(raw.get('value', '')).strip()
        if not key or not value:
            continue
        try:
            conf = float(raw.get('confidence', 0.7))
        except (TypeError, ValueError):
            conf = 0.7
        source = raw.get('source', 'inferred')
        if source not in ('problem_statement', 'user_answer', 'inferred'):
            source = 'inferred'
        prev = by_key.get(key)
        if prev and prev.confidence >= conf:
            continue
        by_key[key] = ExtractedRequirement(key=key, value=value, confidence=conf, source=source)
    state.extracted_requirements = list(by_key.values())

def _heuristic_extract_from_text(text: str, *, source: str='problem_statement') -> list[ExtractedRequirement]:
    low = text.lower()
    out: list[ExtractedRequirement] = []
    for topic, patterns in _HEURISTIC_TOPIC_PATTERNS.items():
        hits = sum((1 for p in patterns if p in low))
        if hits >= 2 or (hits == 1 and len(low) > 80):
            snippet = text.strip()[:200]
            out.append(ExtractedRequirement(key=topic, value=snippet, confidence=0.55 + min(hits * 0.1, 0.25), source=source))
    return out

def _covered_topics(state: DiscoveryState) -> set[str]:
    covered = set(state.covered_topics)
    for ans in state.answers:
        if ans.topic:
            covered.add(ans.topic)
    for req in state.extracted_requirements:
        if req.confidence >= 0.55:
            covered.add(req.key)
    return covered

def _identify_gaps(state: DiscoveryState) -> list[str]:
    result = plan_discovery_question(state)
    return result.missing_labels

def _discovery_answers_dict(state: DiscoveryState) -> dict[str, str]:
    out: dict[str, str] = {}
    for ans in state.answers:
        out[ans.question_id] = ans.answer
        if ans.topic:
            out[f'topic:{ans.topic}'] = ans.answer
    for req in state.extracted_requirements:
        if req.confidence >= 0.5:
            out[f'req:{req.key}'] = req.value
    return out

def discovery_to_clarifying_answers(state: DiscoveryState) -> dict[str, str]:
    """Map discovery state to legacy q1/q2/q3 for agent matching filters."""
    mapping: dict[str, str] = {}
    topic_to_q = {'workflow_domain': 'q1', 'input_types': 'q1', 'data_sources': 'q1', 'hitl_review_policy': 'q2', 'integrations_systems': 'q3', 'output_deliverables': 'q3', 'deployment_context': 'q3'}
    for req in state.extracted_requirements:
        slot = topic_to_q.get(req.key)
        if slot and req.value.strip():
            mapping[slot] = req.value.strip()
    for ans in state.answers:
        slot = topic_to_q.get(ans.topic)
        if slot and ans.answer.strip():
            mapping[slot] = ans.answer.strip()
    return mapping

def discovery_to_transcript_summary(state: DiscoveryState) -> str:
    lines = ['Discovery conversation summary:']
    lines.append(f'Request: {state.original_request[:500]}')
    if state.current_understanding:
        lines.append(f'Understanding: {state.current_understanding}')
    for req in state.extracted_requirements:
        lines.append(f'- {req.key}: {req.value[:300]}')
    for ans in state.answers:
        lines.append(f'- Q: {ans.question[:200]}')
        lines.append(f'  A: {ans.answer[:300]}')
    return '\n'.join(lines)

def _is_discovery_complete(state: DiscoveryState) -> bool:
    if state.phase == 'complete':
        return True
    if state.question_count >= state.max_questions:
        return True
    result = plan_discovery_question(state)
    if result.is_complete and state.question_count >= 1:
        return True
    if not result.unknowns and state.question_count >= 1:
        return True
    return False

def _catalog_context_for_discovery(session: InterviewSession, settings: Settings) -> tuple[str, list[str]]:
    hints = session.spec.catalog_hints or build_catalog_hints_for_interview(session.spec.problem_statement, settings, top_k=12)
    agent_ids = [h.agent_id for h in hints if h.agent_id]
    brief = format_catalog_brief_for_interview(session.spec.problem_statement, settings, preferred_agent_ids=agent_ids)
    names = [h.name for h in hints[:8]]
    return (brief, names)

def generate_discovery_options(topic: str, session: InterviewSession, settings: Settings, state: DiscoveryState, *, limit: int=5) -> tuple[list[str], dict[str, Any]]:
    clarifying = discovery_to_clarifying_answers(state)
    field_key = f'{DISCOVERY_FIELD_PREFIX}{topic}'
    result = generate_cascading_options(field_key, session.spec.problem_statement, settings, clarifying_answers=clarifying, workflow_answers=_discovery_answers_dict(state), spec=session.spec, preferred_agent_ids=state.catalog_agent_ids, limit=limit)
    return (result.options, result.debug)

def plan_next_discovery_step(session: InterviewSession, settings: Settings, client: AzureOpenAI) -> dict[str, Any]:
    """Analyze full conversation state and plan the next question."""
    state = session.discovery
    if state is None:
        raise ValueError('Discovery state not initialized')
    planner = plan_discovery_question(state)
    gaps = planner.missing_labels
    state.missing_information = gaps
    if _is_discovery_complete(state):
        _log_debug(state, 'complete', gaps=gaps, question_count=state.question_count)
        return {'is_complete': True, 'current_understanding': state.current_understanding}
    _, agent_names = _catalog_context_for_discovery(session, settings)
    state.matched_agent_names = agent_names
    plan = planner_result_to_plan_dict(planner)
    if plan.get('extracted_requirements'):
        _merge_requirements(state, plan['extracted_requirements'])
    if plan.get('current_understanding'):
        state.current_understanding = str(plan['current_understanding']).strip()
    if plan.get('is_complete') and state.question_count >= 1:
        state.phase = 'complete'
        _log_debug(state, 'planner_complete', plan=plan)
        return {'is_complete': True, 'current_understanding': state.current_understanding}
    topic = str(plan.get('topic', 'other')).strip() or 'other'
    question = str(plan.get('next_question', '')).strip()
    why = str(plan.get('why_this_question', '')).strip()
    if question and client:
        question = polish_question_with_llm(question, goal=state.original_request, topic=topic, settings=settings, client=client)
    skip = plan.get('skip_topics')
    if isinstance(skip, list):
        state.covered_topics = list(set(state.covered_topics) | {str(s) for s in skip if str(s).strip()})
    state.last_topic = topic
    state.last_question_reason = why
    state.question_count += 1
    qid = f'q{state.question_count}'
    _log_debug(state, 'next_question', topic=topic, question=question[:200], why=why[:200], gaps=gaps, planner_scores=plan.get('planner_scores'), catalog_agents=agent_names, requirements=[r.model_dump() for r in state.extracted_requirements])
    return {'is_complete': False, 'question_id': qid, 'topic': topic, 'question': question, 'why': why, 'current_understanding': state.current_understanding, 'missing_information': state.missing_information}

def format_discovery_message(session: InterviewSession, question: InterviewQuestion, *, why: str='') -> str:
    """Architect-style message for a new discovery question."""
    if session.discovery:
        session.discovery.interview_phase = 'asking'
    return format_new_question_message(session, question, why=why)

def build_discovery_interview_question(plan: dict[str, Any], session: InterviewSession, settings: Settings, state: DiscoveryState) -> InterviewQuestion:
    topic = str(plan.get('topic', 'other'))
    qid = str(plan.get('question_id', f'q{state.question_count}'))
    question = str(plan.get('question', '')).strip()
    why = str(plan.get('why', '')).strip()
    chips, debug = generate_discovery_options(topic, session, settings, state)
    core = [c for c in chips if not is_other_chip(c)]
    filtered_core = filter_domain_options(core, problem_statement=session.spec.problem_statement, topic=topic)
    if filtered_core:
        other = [c for c in chips if is_other_chip(c)]
        chips = filtered_core + other
    suggested = pick_suggested_chip(chips, query=session.spec.problem_statement)
    _log_debug(state, 'generated_options', topic=topic, options=core, filter_debug=debug)
    return InterviewQuestion(field_key=discovery_field_key(topic, qid), topic_label=_TOPIC_LABELS.get(topic, 'Discovery'), question=question, chips=chips, why_it_matters=why or 'Reduces ambiguity before we wire catalog agents.', suggested_chip=suggested, catalog_reference=state.matched_agent_names[0] if state.matched_agent_names else None, suggestion_reason='Options are ranked from the agent catalog based on your workflow description.')

def initialize_discovery_state(session: InterviewSession, settings: Settings) -> DiscoveryState:
    statement = session.spec.problem_statement.strip()
    hints = session.spec.catalog_hints or build_catalog_hints_for_interview(statement, settings, top_k=12)
    agent_ids = [h.agent_id for h in hints if h.agent_id]
    state = DiscoveryState(original_request=statement, catalog_agent_ids=agent_ids, matched_agent_names=[h.name for h in hints[:8]])
    reqs = _heuristic_extract_from_text(statement, source='problem_statement')
    state.extracted_requirements = reqs
    state.current_understanding = statement[:400] if len(statement) > 20 else 'Starting discovery from your request.'
    _log_debug(state, 'initialized', requirements=[r.model_dump() for r in reqs], catalog_agents=state.matched_agent_names)
    return state

def begin_discovery_phase(session: InterviewSession, settings: Settings, client: AzureOpenAI, *, intro_prefix: str='first') -> InterviewSession:
    """Start state-driven discovery (replaces fixed clarifying questionnaire)."""
    statement = session.spec.problem_statement
    session.spec.catalog_hints = build_catalog_hints_for_interview(statement, settings, top_k=12)
    session.discovery = initialize_discovery_state(session, settings)
    session.clarifying_questions = []
    session.clarifying_answers = {}
    plan = plan_next_discovery_step(session, settings, client)
    if plan.get('is_complete'):
        return complete_discovery_phase(session, settings, client)
    question = build_discovery_interview_question(plan, session, settings, session.discovery)
    session.pending_question = question
    body = format_discovery_message(session, question, why=plan.get('why', ''))
    if session.discovery:
        session.discovery.interview_phase = 'waiting_for_answer'
    session.messages.append(ChatMessage(role='assistant', content=body, field_key=question.field_key))
    return session

def record_discovery_answer(session: InterviewSession, field_key: str, answer: str) -> None:
    state = session.discovery
    if state is None:
        return
    topic, qid = parse_discovery_field_key(field_key)
    pq = session.pending_question
    question_text = pq.question if pq else ''
    state.answers.append(DiscoveryAnswer(question_id=qid, question=question_text, answer=answer.strip(), topic=topic, turn_index=len(session.messages)))
    if topic and topic not in state.covered_topics:
        state.covered_topics.append(topic)
    _merge_requirements(state, [{'key': topic, 'value': answer.strip(), 'confidence': 0.9, 'source': 'user_answer'}])
    _log_debug(state, 'answer_recorded', topic=topic, answer=answer[:200], covered=state.covered_topics)

def skip_discovery_turn(session: InterviewSession, settings: Settings, client: AzureOpenAI, *, field_key: str) -> InterviewSession:
    """Skip the current discovery topic and move on."""
    state = session.discovery
    if state is None:
        return session
    topic, qid = parse_discovery_field_key(field_key)
    pq = session.pending_question
    question_text = pq.question if pq else ''
    if topic and topic not in state.covered_topics:
        state.covered_topics.append(topic)
    state.answers.append(DiscoveryAnswer(question_id=qid, question=question_text, answer='(skipped)', topic=topic, turn_index=len(session.messages)))
    _log_debug(state, 'topic_skipped', topic=topic)
    session.clarifying_answers = discovery_to_clarifying_answers(state)
    plan = plan_next_discovery_step(session, settings, client)
    if plan.get('is_complete'):
        return complete_discovery_phase(session, settings, client)
    question = build_discovery_interview_question(plan, session, settings, state)
    session.pending_question = question
    body = format_discovery_message(session, question)
    state.interview_phase = 'waiting_for_answer'
    session.messages.append(ChatMessage(role='assistant', content=body, field_key=question.field_key))
    return session

def advance_discovery_turn(session: InterviewSession, settings: Settings, client: AzureOpenAI, answer: str, *, field_key: str) -> InterviewSession:
    record_discovery_answer(session, field_key, answer)
    session.clarifying_answers = discovery_to_clarifying_answers(session.discovery)
    plan = plan_next_discovery_step(session, settings, client)
    if plan.get('is_complete'):
        return complete_discovery_phase(session, settings, client)
    question = build_discovery_interview_question(plan, session, settings, session.discovery)
    session.pending_question = question
    body = format_discovery_message(session, question, why=plan.get('why', ''))
    if session.discovery:
        session.discovery.interview_phase = 'waiting_for_answer'
    session.messages.append(ChatMessage(role='assistant', content=body, field_key=question.field_key))
    return session

def complete_discovery_phase(session: InterviewSession, settings: Settings, client: AzureOpenAI) -> InterviewSession:
    """Finalize discovery and hand off to agent workflow interview."""
    state = session.discovery
    if state:
        state.phase = 'complete'
        state.interview_phase = 'ready_for_architecture'
        session.clarifying_answers = discovery_to_clarifying_answers(state)
        session.spec.transcript_summary = discovery_to_transcript_summary(state)
        _log_debug(state, 'phase_complete', understanding=state.current_understanding, requirements=[r.model_dump() for r in state.extracted_requirements], answers=len(state.answers))
    session.pending_question = None
    return begin_agent_workflow_interview(session, settings, client)

def refresh_discovery_question_chips(session: InterviewSession, settings: Settings) -> None:
    pq = session.pending_question
    state = session.discovery
    if not pq or not state or (not is_discovery_field_key(pq.field_key)):
        return
    topic, _ = parse_discovery_field_key(pq.field_key)
    chips, debug = generate_discovery_options(topic, session, settings, state)
    suggested = pick_suggested_chip(chips, query=session.spec.problem_statement)
    session.pending_question = pq.model_copy(update={'chips': chips, 'suggested_chip': suggested, 'suggestion_reason': f"Refreshed from catalog ({(debug.get('stages', [])[-1] if debug.get('stages') else 'filtered')})."})

def discovery_context_blob(session: InterviewSession) -> str:
    """Enriched query string for agent question filtering."""
    state = session.discovery
    if not state:
        return session.spec.problem_statement
    parts = [session.spec.problem_statement]
    if state.current_understanding:
        parts.append(state.current_understanding)
    for req in state.extracted_requirements:
        parts.append(f'{req.key}: {req.value}')
    for ans in state.answers:
        parts.append(ans.answer)
    return '\n'.join(parts)

def topic_covered_in_discovery(state: DiscoveryState | None, input_name: str) -> bool:
    """True when discovery already resolved this agent input topic."""
    if not state:
        return False
    low = input_name.lower()
    blob = discovery_context_blob_from_state(state).lower()
    if 'pdf' in low or 'docx' in low:
        return any((w in blob for w in ('pdf', 'docx', 'document upload')))
    if 'image' in low or 'photo' in low:
        return any((w in blob for w in ('image', 'photo', 'vision', 'jpeg', 'png')))
    if 'review' in low or 'blocking' in low:
        return any((w in blob for w in ('review', 'human', 'analyst', 'hitl', 'approve')))
    if 'integration' in low or 'email' in low:
        return any((w in blob for w in ('email', 'crm', 'integration', 'slack', 'database')))
    return False

def discovery_context_blob_from_state(state: DiscoveryState) -> str:
    parts = [state.original_request, state.current_understanding]
    for req in state.extracted_requirements:
        parts.append(req.value)
    for ans in state.answers:
        parts.append(ans.answer)
    return ' '.join((p for p in parts if p))


# ========================================================================
# services/agent_input_chips.py
# ========================================================================


"""Catalog-grounded chips for agent setup questions (spec.json inputs)."""
import json
import logging
import os
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING
from openai import AzureOpenAI
if TYPE_CHECKING:
    pass
logger = logging.getLogger(__name__)
_TOKEN_RE = re.compile('[a-z0-9]{3,}')
MIN_TIER_CHIPS_BEFORE_LLM = 3

def interview_uses_fast_chips() -> bool:
    """When true, skip per-question LLM chip generation (much faster chat turns)."""
    return os.getenv('INTERVIEW_FAST_CHIPS', '1').strip().lower() not in ('0', 'false', 'no')

@dataclass
class LlmChipGeneration:
    chips: list[str]
    suggested_index: int = 0
    grounding: list[str] | None = None

def _tokens(text: str) -> set[str]:
    return set(_TOKEN_RE.findall((text or '').lower()))
_SLASH_ENUM_RE = re.compile('\\b([A-Z][A-Za-z0-9]*(?:/[A-Z][A-Za-z0-9]*)+)\\b')
_WIRED_INPUT_MARKERS = ('extracted json', 'from entity', 'document bytes', 'source document text', 'candidate entity', 'missing_item', 'reason string')

def parse_enum_values_from_input_name(input_name: str) -> list[str]:
    """Pull slash- or paren-delimited enums from spec.json input labels."""
    chips: list[str] = []
    for match in _SLASH_ENUM_RE.finditer(input_name or ''):
        for part in match.group(1).split('/'):
            part = part.strip()
            if part and len(part) <= 32:
                chips.append(part)
    paren = re.search('\\(([^)]+)\\)', input_name or '')
    if paren:
        inner = paren.group(1)
        if '/' in inner or ',' in inner:
            for part in re.split('[/,]', inner):
                part = part.strip()
                if part and 2 <= len(part) <= 40:
                    chips.append(part)
    return _dedupe_chips(chips)

def _chips_from_agent_notes(agent: AgentRecord, input_name: str) -> list[str]:
    notes = (agent.notes or '').lower()
    low = (input_name or '').lower()
    chips: list[str] = []
    if 'search' in low:
        for mode in ('local', 'global', 'drift', 'basic'):
            if mode in notes:
                chips.append(_normalize_chip(f'Use {mode} search mode for this workflow'))
    if 'boolean' in notes or any((x in low for x in ('is_blocking', 'blocking'))):
        chips.extend(['Block pipeline until required fields are complete', 'Flag issues but continue with partial results'])
    if 'human-in-the-loop' in notes or 'analyst reviews' in notes:
        if any((x in low for x in ('email', 'draft', 'send', 'body'))):
            chips.extend(['Draft only — analyst reviews and sends manually', 'Send automatically after analyst approval'])
    if 'json response_format' in notes and 'json' in low:
        chips.append('Use structured JSON matching the agent output schema')
    return chips

def _chips_from_agent_integrations(agent: AgentRecord, input_name: str) -> list[str]:
    low = (input_name or '').lower()
    if not any((w in low for w in ('source', 'connect', 'integration', 'api', 'database', 'email', 'storage', 'client', 'project', 'filename'))):
        return []
    return [_normalize_chip(f'Pull from {_humanize_integration(item)}') for item in agent.integrations[:4] if item and item.strip()]

def _chips_from_sibling_inputs(agent: AgentRecord, input_name: str) -> list[str]:
    chips: list[str] = []
    for inp in agent.inputs:
        if inp == input_name:
            continue
        if any((marker in inp.lower() for marker in _WIRED_INPUT_MARKERS)):
            continue
        label = human_input_label(inp)
        chips.append(_normalize_chip(f'Derive from {label} configured earlier on this agent'))
    return chips[:2]

def _chips_from_upstream_outputs(agent: AgentRecord, input_name: str) -> list[str]:
    low = (input_name or '').lower()
    if not any((w in low for w in ('from', 'json', 'extracted', 'upstream', 'source', 'missing'))):
        return []
    chips: list[str] = []
    for out in agent.outputs[:3]:
        label = out.split('(')[0].strip()
        if label:
            chips.append(_normalize_chip(f'Wire from upstream output: {label[:90]}'))
    return chips

def catalog_chips_for_agent_input(agent: AgentRecord, input_name: str, catalog: CatalogLoadResult, query: str, *, limit: int=5) -> list[str]:
    """Mine answer options from spec.json metadata for one agent input."""
    chips: list[str] = []
    for value in parse_enum_values_from_input_name(input_name):
        if value.upper() in ('PDF', 'DOCX', 'TXT', 'JSON', 'CSV'):
            chips.append(_normalize_chip(f'Accept {value} as the primary format'))
        elif value.lower() in ('low', 'medium', 'high'):
            chips.append(_normalize_chip(f'Use {value} tier threshold for this workflow'))
        else:
            chips.append(_normalize_chip(f'Use {value} for {human_input_label(input_name)}'))
    chips.extend(_chips_from_agent_notes(agent, input_name))
    chips.extend(_chips_from_agent_integrations(agent, input_name))
    chips.extend(_chips_from_sibling_inputs(agent, input_name))
    chips.extend(_chips_from_upstream_outputs(agent, input_name))
    chips.extend(catalog_values_for_input(catalog, agent, input_name, limit=3))
    if agent.function_summary:
        summary = agent.function_summary.strip()
        first = summary.split('.')[0].strip()
        if len(first) > 12:
            chips.append(_normalize_chip(f'Match {agent.name} default: {first[:100]}'))
    ranked = _rank_chips(query, chips, field_key=input_name)
    return ranked[:limit]

def contextual_chips_from_workflow(agent: AgentRecord, input_name: str, *, spec: ArchitectureSpec | None, messages: list[ChatMessage] | None, workflow_answers: dict[str, str] | None=None, clarifying_answers: dict[str, str] | None=None, questions_by_key: dict[str, 'AgentSetupQuestionItem'] | None=None) -> list[str]:
    """Options shaped by clarifying answers and prior agent-input selections."""
    chips: list[str] = []
    clarifying = clarifying_answers or {}
    answers = workflow_answers or {}
    questions = questions_by_key or {}
    low_input = (input_name or '').lower()
    q1 = clarifying.get('q1', '').strip()
    q2 = clarifying.get('q2', '').strip()
    q3 = clarifying.get('q3', '').strip()
    if is_change_problem_statement_intent(q1):
        q1 = ''
    if is_change_problem_statement_intent(q2):
        q2 = ''
    if is_change_problem_statement_intent(q3):
        q3 = ''
    if q1 and any((w in low_input for w in ('document', 'pdf', 'docx', 'txt', 'format', 'file'))):
        chips.append(_normalize_chip(f'Align document intake with scope: {q1[:110]}'))
    if q2 and any((w in low_input for w in ('blocking', 'review', 'email', 'draft', 'override', 'hitl'))):
        chips.append(_normalize_chip(f'Apply review policy from earlier: {q2[:110]}'))
    if q3 and any((w in low_input for w in ('integration', 'source', 'client', 'project', 'database', 'email', 'api'))):
        chips.append(_normalize_chip(f'Connect using systems chosen earlier: {q3[:110]}'))
    for field_key, answer in answers.items():
        if not answer.strip() or is_change_problem_statement_intent(answer):
            continue
        q_item = questions.get(field_key)
        if not q_item or q_item.agent_id != agent.id:
            continue
        if q_item.input_name == input_name:
            continue
        prior_label = human_input_label(q_item.input_name)
        chips.append(_normalize_chip(f'Use {prior_label} setting already chosen: {answer[:100]}'))
    for field_key, answer in answers.items():
        if not answer.strip() or is_change_problem_statement_intent(answer):
            continue
        q_item = questions.get(field_key)
        if not q_item or q_item.agent_id == agent.id:
            continue
        if not any((w in low_input for w in ('extracted', 'from', 'upstream', 'source', 'json'))):
            break
        chips.append(_normalize_chip(f'Pass output from {q_item.agent_name} ({q_item.input_name}): {answer[:90]}'))
        break
    if messages:
        for msg in reversed(messages):
            if msg.role != 'user' or not msg.content.strip():
                continue
            if msg.field_key and msg.field_key.endswith(f':{input_name}'):
                continue
            prior = msg.content.strip()
            if 12 < len(prior) <= 200:
                chips.append(_normalize_chip(f'Continue from your last answer: {prior[:120]}'))
            break
    if spec and spec.transcript_summary and (not clarifying):
        hook = spec.transcript_summary.strip()[:100]
        if hook:
            chips.append(_normalize_chip(f'Fit clarifications already captured: {hook}'))
    return _dedupe_chips(chips)[:5]

def catalog_values_for_input(catalog: CatalogLoadResult, agent: AgentRecord, input_name: str, *, limit: int=4) -> list[str]:
    """Values seen in spec.json for the same input name (cross-agent patterns)."""
    target = _tokens(input_name)
    if not target:
        return []
    chips: list[str] = []
    for other in catalog.agents:
        if other.id == agent.id:
            continue
        if other.vertical != agent.vertical and agent.vertical != 'Other':
            continue
        for inp in other.inputs:
            if _tokens(inp) & target or inp.lower() == input_name.lower():
                for out in other.outputs[:2]:
                    if out.strip():
                        chips.append(_normalize_chip(f'Same pattern as {other.name}: {out[:100]}'))
                if other.function_summary:
                    chips.append(_normalize_chip(f"Align with {other.name} — {(other.function_summary or '')[:90]}"))
                break
        if len(chips) >= limit:
            break
    return _dedupe_chips(chips)[:limit]

def _format_history(messages: list[ChatMessage] | None, limit: int=8) -> str:
    if not messages:
        return '(none)'
    lines = [f'{m.role}: {m.content[:280]}' for m in messages[-limit:] if m.content and m.content.strip()]
    return '\n'.join(lines) if lines else '(none)'

def _format_prior_answers(spec: ArchitectureSpec | None) -> str:
    if not spec:
        return '(none)'
    parts: list[str] = []
    if spec.transcript_summary:
        parts.append(spec.transcript_summary.strip()[:1200])
    for key, field in spec.fields.items():
        if field.value and str(field.value).strip():
            parts.append(f'{key}: {str(field.value).strip()[:200]}')
    return '\n'.join(parts) if parts else '(none)'

def _tier12_gated_count(*, deterministic: list[str], catalog: list[str], contextual: list[str], input_name: str, agent_summary: str) -> int:
    """How many quality-gated chips tiers 1–2 produce (before LLM)."""
    pre = merge_and_gate_chips(deterministic=deterministic, catalog=catalog, contextual=contextual, llm=[], input_name=input_name, agent_summary=agent_summary)
    return len([c for c in pre if not is_other_chip(c)])

def generate_llm_chips_for_input(agent: AgentRecord, input_name: str, question: str, query: str, settings: Settings, client: AzureOpenAI, *, spec: ArchitectureSpec | None=None, messages: list[ChatMessage] | None=None, existing_chips: list[str] | None=None) -> LlmChipGeneration | None:
    """
  P3: Small dedicated LLM call for chip options when catalog tiers are thin.
    """
    existing = [c for c in existing_chips or [] if c.strip() and (not is_other_chip(c))]
    system = load_prompt('agent_input_chips.txt').replace('{agent_name}', agent.name).replace('{agent_summary}', (agent.function_summary or '')[:500]).replace('{input_name}', input_name).replace('{input_label}', human_input_label(input_name)).replace('{problem_statement}', query[:1500]).replace('{history}', _format_history(messages)).replace('{prior_answers}', _format_prior_answers(spec)).replace('{question}', question[:500]).replace('{existing_chips}', '\n'.join((f'- {c}' for c in existing[:6])) if existing else '(none)')
    try:
        raw = call_llm(client, settings, system, 'Return the JSON object with chips for this agent input.', json_mode=True, temperature=0.2)
        parsed = json.loads(strip_json_fences(raw))
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning('LLM chip generation parse failed: %s', exc)
        return None
    raw_chips = parsed.get('chips') if isinstance(parsed, dict) else None
    if not isinstance(raw_chips, list):
        return None
    chips: list[str] = []
    for item in raw_chips:
        text = _normalize_chip(str(item).strip())
        if text and (not is_other_chip(text)):
            chips.append(text)
    gated = gate_chip_list(chips, input_name=input_name, agent_summary=agent.function_summary or '')
    if len(gated) < 2:
        return None
    idx = parsed.get('suggested_index', 0)
    try:
        suggested_index = int(idx)
    except (TypeError, ValueError):
        suggested_index = 0
    if suggested_index < 0 or suggested_index >= len(gated):
        suggested_index = 0
    grounding = parsed.get('grounding')
    ground_list = [str(g).strip() for g in grounding if str(g).strip()] if isinstance(grounding, list) else None
    return LlmChipGeneration(chips=gated, suggested_index=suggested_index, grounding=ground_list)

def build_agent_input_chips(agent: AgentRecord, input_name: str, query: str, settings: Settings, *, deterministic: list[str] | None=None, spec: ArchitectureSpec | None=None, messages: list[ChatMessage] | None=None, llm_chips: list[str] | None=None, turn_index: int=0, client: AzureOpenAI | None=None, question_text: str='', workflow_answers: dict[str, str] | None=None, clarifying_answers: dict[str, str] | None=None, questions_by_key: dict[str, 'AgentSetupQuestionItem'] | None=None, field_key: str | None=None) -> tuple[list[str], str | None, str]:
    """
    Runtime chips for one agent input from cascading catalog filters.
    Returns (chips, suggested_chip, suggestion_reason).
    """
    del turn_index, questions_by_key, deterministic
    fk = field_key or f'{AGENT_INPUT_PREFIX}{agent.id}:{slugify(input_name)}'
    hint_ids = [h.agent_id for h in spec.catalog_hints or [] if h.agent_id] if spec else []
    result = generate_cascading_options(fk, query, settings, clarifying_answers=clarifying_answers, workflow_answers=workflow_answers, spec=spec, preferred_agent_ids=hint_ids, target_agent_id=agent.id, target_input_name=input_name)
    catalog_core = [c for c in result.options if not is_other_chip(c)]
    agent_summary = agent.function_summary or ''
    interview_llm = [c.strip() for c in llm_chips or [] if c.strip() and (not is_other_chip(c))]
    llm_tier: list[str] = []
    if not interview_uses_fast_chips() and len(catalog_core) < MIN_TIER_CHIPS_BEFORE_LLM and (client is not None):
        gen = generate_llm_chips_for_input(agent, input_name, question_text or f'How should we configure {human_input_label(input_name)}?', query, settings, client, spec=spec, messages=messages, existing_chips=catalog_core)
        if gen:
            llm_tier = gen.chips
    merged = merge_and_gate_chips(deterministic=[], catalog=catalog_core, contextual=[], llm=interview_llm + llm_tier, input_name=input_name, agent_summary=agent_summary)
    core_merged = [c for c in merged if not is_other_chip(c)]
    filtered = filter_domain_options(core_merged, problem_statement=query, topic=input_name)
    if filtered:
        merged = filtered + [c for c in merged if is_other_chip(c)]
    suggested = pick_suggested_chip(merged, query=query)
    reason = f"From spec.json rows ({(result.debug.get('stages', [])[-1] if result.debug.get('stages') else 'filtered')}) for `{input_name}` on {agent.name}."
    return (merged, suggested, reason)

def human_input_label(input_name: str) -> str:
    """Plain label for questions (not raw field ids)."""
    text = (input_name or '').replace('_', ' ').strip()
    if not text:
        return 'this setting'
    return text[0].upper() + text[1:]


# ========================================================================
# services/agent_workflow_interview.py
# ========================================================================


"""Spec-first agent workflow interview (cursor-agent-prompt style)."""
import json
import logging
import re
from typing import Optional
from openai import AzureOpenAI
logger = logging.getLogger(__name__)
_ALLOWED_PHASE_TRANSITIONS: dict[WorkflowPhase, set[WorkflowPhase]] = {'start': {'interview', 'completion_check'}, 'interview': {'completion_check', 'handover'}, 'completion_check': {'handover', 'interview'}, 'handover': set()}

def _set_phase(state: AgentWorkflowState, new_phase: WorkflowPhase, *, context: str) -> bool:
    old_phase = state.current_phase
    if old_phase == new_phase:
        return True
    allowed = _ALLOWED_PHASE_TRANSITIONS.get(old_phase, set())
    if new_phase not in allowed:
        logger.warning('Ignored invalid phase transition: %s -> %s (%s)', old_phase, new_phase, context)
        return False
    state.current_phase = new_phase
    logger.info('Phase transition: %s -> %s (%s)', old_phase, new_phase, context)
    return True
AGENT_INPUT_PREFIX = 'agent_input:'
MAX_AGENT_QUESTIONS_SAFETY = 18
MAX_QUESTIONS_PER_AGENT = 3
OTHER_CHIP = 'Other / describe in chat'
EXPLICIT_FINISH_KEYWORDS = ('ready', 'finish', 'complete', 'generate', 'done')
MIN_ANSWERS_BEFORE_AUTO_COMPLETE = 6
_SKIP_INPUT_SUBSTRINGS = ('extracted json', 'from entity extraction', 'source document text', 'document bytes', 'candidate entity names', 'missing_item_explanations', 'extracted_policy_fields', 'source_doc', 'reason string')

def _normalize_input_name(name: str) -> str:
    return re.sub('\\s+', ' ', (name or '').lower().strip())

def _topic_aligned_chip(input_name: str) -> str:
    """A direct quick option matching the exact current topic/input."""
    low = _normalize_input_name(input_name)
    if 'filename' in low:
        return 'Use the uploaded file name as identifier'
    if 'project_id' in low or 'client_summary' in low:
        return 'Use the existing customer or case identifier'
    if 'policy json' in low or 'ingestion policy' in low:
        return 'Use our current policy file'
    if 'riskfactorscores' in low or 'geography_score' in low:
        return 'Use our default section scoring method'
    return f'Configure: {input_name.strip()}'

def _question_fingerprint(q: AgentSetupQuestionItem) -> str:
    return _normalize_input_name(f'{q.agent_id}|{q.input_name}|{q.question}')

def _should_skip_input(input_name: str, query: str) -> bool:
    if _input_satisfied_by_query(input_name, query):
        return True
    low = _normalize_input_name(input_name)
    return any((part in low for part in _SKIP_INPUT_SUBSTRINGS))

def _input_priority(input_name: str) -> int:
    low = _normalize_input_name(input_name)
    if any((x in low for x in ('pdf', 'docx', 'txt', 'document', 'format', 'client', 'filename'))):
        return 0
    if any((x in low for x in ('policy', 'blocking', 'missing', 'threshold', 'score'))):
        return 1
    if any((x in low for x in ('search', 'mode', 'image', 'photo'))):
        return 2
    return 3

def _cluster_for_input(input_name: str) -> str:
    low = _normalize_input_name(input_name)
    if any((x in low for x in ('policy', 'compliance', 'override', 'blocking', 'sanction', 'pep'))):
        return 'Security & Compliance'
    if any((x in low for x in ('score', 'threshold', 'tier', 'riskfactor'))):
        return 'Risk Scoring Configuration'
    if any((x in low for x in ('project_id', 'client', 'filename', 'source_document_id'))):
        return 'Identity & Tracking'
    if any((x in low for x in ('image', 'photo', 'vision', 'layout', 'planogram'))):
        return 'Vision Inputs'
    if any((x in low for x in ('search', 'query', 'method'))):
        return 'Retrieval & Search'
    return 'General Configuration'

def _score_components(input_name: str, chips: list[str]) -> tuple[int, int, int, int]:
    """
    Scores are 0..100. Combined rank uses 40/30/20/10 weighting.
    """
    low = _normalize_input_name(input_name)
    impact = 50
    dependency = 45
    uncertainty = 35
    criticality = 40
    if any((x in low for x in ('policy', 'override', 'blocking', 'sanction', 'pep'))):
        impact, criticality = (92, 94)
        dependency = 78
    elif any((x in low for x in ('riskfactor', 'score', 'threshold', 'tier'))):
        impact, criticality = (86, 88)
        dependency = 72
    elif any((x in low for x in ('project_id', 'client', 'identifier'))):
        impact, dependency, criticality = (76, 81, 74)
    elif any((x in low for x in ('document', 'format', 'filename', 'source_document_id'))):
        impact, dependency, criticality = (70, 68, 64)
    elif any((x in low for x in ('image', 'layout', 'planogram'))):
        impact, dependency, criticality = (74, 66, 70)
    if len(chips) <= 2:
        uncertainty = 76
    elif any(('default' in c.lower() for c in chips)):
        uncertainty = 62
    else:
        uncertainty = 42
    return (impact, dependency, uncertainty, criticality)

def _rank_score(impact: int, dependency: int, uncertainty: int, criticality: int) -> float:
    return 0.4 * impact + 0.3 * dependency + 0.2 * uncertainty + 0.1 * criticality

def _dedupe_question_queue(questions: list[AgentSetupQuestionItem]) -> list[AgentSetupQuestionItem]:
    out: list[AgentSetupQuestionItem] = []
    seen_keys: set[str] = set()
    seen_semantic: set[tuple[str, str]] = set()
    seen_text: set[str] = set()
    for q in questions:
        if q.field_key in seen_keys:
            continue
        sem = (q.agent_id, _normalize_input_name(q.input_name))
        if sem in seen_semantic:
            continue
        fp = _question_fingerprint(q)
        if fp in seen_text:
            continue
        seen_keys.add(q.field_key)
        seen_semantic.add(sem)
        seen_text.add(fp)
        out.append(q)
    return out

def _cap_per_agent(questions: list[AgentSetupQuestionItem]) -> list[AgentSetupQuestionItem]:
    counts: dict[str, int] = {}
    out: list[AgentSetupQuestionItem] = []
    ranked = sorted(questions, key=lambda q: _input_priority(q.input_name))
    for q in ranked:
        n = counts.get(q.agent_id, 0)
        if n >= MAX_QUESTIONS_PER_AGENT:
            continue
        counts[q.agent_id] = n + 1
        out.append(q)
        if len(out) >= MAX_AGENT_QUESTIONS_SAFETY:
            break
    return out

def _finalize_question_queue(questions: list[AgentSetupQuestionItem], query: str, session: InterviewSession | None=None) -> list[AgentSetupQuestionItem]:
    discovery = session.discovery if session else None
    filtered = [q for q in questions if not _should_skip_input(q.input_name, query) and (not topic_covered_in_discovery(discovery, q.input_name))]
    return _cap_per_agent(_dedupe_question_queue(filtered))

def _dependency_rank_boost(q: AgentSetupQuestionItem, state: AgentWorkflowState) -> float:
    """Prefer prerequisites on the same agent (e.g. policy before scores)."""
    answered = {k for k, v in state.answers.items() if str(v).strip()}
    boost = 0.0
    low = _normalize_input_name(q.input_name)
    for other in state.questions:
        if other.agent_id != q.agent_id or other.field_key in answered:
            continue
        if other.field_key == q.field_key:
            continue
        other_low = _normalize_input_name(other.input_name)
        if any((x in low for x in ('score', 'threshold', 'tier', 'riskfactor'))):
            if any((x in other_low for x in ('policy', 'document', 'client', 'project'))):
                boost += 18.0
        if 'override' in low and 'policy' in other_low:
            boost += 14.0
    return boost

def _pending_questions(state: AgentWorkflowState) -> list[AgentSetupQuestionItem]:
    answered = {k for k, v in state.answers.items() if str(v).strip()}
    pending = [q for q in state.questions if q.field_key not in answered]
    return sorted(pending, key=lambda q: (-(q.rank_score + _dependency_rank_boost(q, state)), -q.impact_score, -q.dependency_score, q.agent_id, q.input_name, q.field_key))

def _compute_required_input_count(agents: list[AgentRecord], query: str) -> int:
    count = 0
    for agent in agents:
        for input_name in agent.inputs:
            if _should_skip_input(input_name, query):
                continue
            count += 1
    return count

def _prior_context_block(session: InterviewSession) -> str:
    parts: list[str] = []
    if session.spec.transcript_summary:
        parts.append('CLARIFYING / PRIOR SUMMARY:\n' + session.spec.transcript_summary.strip())
    if session.clarifying_answers:
        parts.append('CLARIFYING ANSWERS:\n' + json.dumps(session.clarifying_answers, indent=2, ensure_ascii=False))
    if session.agent_workflow and session.agent_workflow.answers:
        parts.append('AGENT INPUT ANSWERS:\n' + json.dumps(session.agent_workflow.answers, indent=2, ensure_ascii=False))
    return '\n\n'.join(parts) if parts else '(none)'

def _polish_question_text(question: str, agent_name: str, input_name: str) -> str:
    text = ' '.join((question or '').split())
    if not text:
        text = f'What configuration should {agent_name} use for {human_input_label(input_name)} in this workflow?'
    if '?' not in text:
        text = text.rstrip('.') + '?'
    if text.count('?') > 1:
        text = text.split('?')[0].strip() + '?'
    label = human_input_label(input_name)
    if len(label) < 48 and label.lower() not in text.lower():
        text = text[:-1] + f' (for {label})?'
    if len(text) > 240:
        text = text[:237].rsplit(' ', 1)[0] + '?'
    return text

def _refresh_metrics(state: AgentWorkflowState) -> None:
    pending = _pending_questions(state)
    total = max(state.required_input_count or len(state.questions), 1)
    answered_count = sum((1 for q in state.questions if str(state.answers.get(q.field_key, '')).strip()))
    state.coverage_score = round(answered_count / total * 100, 1)
    state.critical_items = [f'{q.agent_name} — {q.input_name}' for q in pending if q.impact_score > 65][:8]
    state.risk_score = round(min(10.0, sum((q.impact_score for q in pending)) / max(len(pending), 1) / 10.0), 1) if pending else 0.0

def _explicit_finish_requested(user_answer: str | None) -> bool:
    if not user_answer:
        return False
    low = user_answer.lower()
    return bool(re.search("\\b(we are|i am|i'm)?\\s*(ready to (finish|complete|generate)|finish (the )?interview|complete (the )?interview|generate (the )?(result|report|recommendation)|done)\\b", low)) or any((re.search(f'\\b{k}\\b', low) for k in EXPLICIT_FINISH_KEYWORDS))

def _completion_gate(state: AgentWorkflowState, *, user_answer: str | None=None) -> tuple[bool, str | None]:
    pending = _pending_questions(state)
    high_impact_left = [q for q in pending if q.impact_score > 65]
    answered_count = sum((1 for v in state.answers.values() if str(v).strip()))
    if answered_count < MIN_ANSWERS_BEFORE_AUTO_COMPLETE and (not _explicit_finish_requested(user_answer)):
        return (False, None)
    if not high_impact_left:
        return (True, 'no_high_impact_inputs_remaining')
    if state.question_count >= min(state.question_budget, state.hard_cap):
        return (True, 'question_budget_reached')
    if _explicit_finish_requested(user_answer):
        return (True, 'user_requested_finish')
    return (False, None)

def _workflow_is_complete(state: AgentWorkflowState, *, user_answer: str | None=None) -> bool:
    done, reason = _completion_gate(state, user_answer=user_answer)
    if done:
        state.completion_reason = reason
        return True
    return len(_pending_questions(state)) == 0

def _record_answer(state: AgentWorkflowState, field_key: str, answer: str) -> None:
    text = answer.strip()
    if not text or not field_key:
        return
    state.answers[field_key] = text
    sem: tuple[str, str] | None = None
    for q in state.questions:
        if q.field_key == field_key:
            sem = (q.agent_id, _normalize_input_name(q.input_name))
            break
    if sem:
        for q in state.questions:
            if (q.agent_id, _normalize_input_name(q.input_name)) == sem:
                state.answers.setdefault(q.field_key, text)
    answered_count = len([k for k in state.answers if state.answers[k].strip()])
    state.next_index = answered_count
    state.question_count = max(state.question_count, answered_count)
    _refresh_metrics(state)

def is_agent_input_field_key(field_key: str | None) -> bool:
    return bool(field_key and field_key.startswith(AGENT_INPUT_PREFIX))

def agent_input_field_key(agent_id: str, input_name: str) -> str:
    return f'{AGENT_INPUT_PREFIX}{agent_id}:{slugify(input_name)}'

def _detect_vertical(query: str) -> str | None:
    q = query.lower()
    if any((w in q for w in ('kyc', 'ubo', 'onboarding', 'compliance', 'sanction', 'corporate client', 'jpmc', 'finance'))):
        return 'Finance'
    if any((w in q for w in ('shelf', 'planogram', 'mars', 'cpg', 'retail', 'store', 'facings', 'vto', 'fashion'))):
        return 'Retail'
    if 'cpg' in q or 'consumer packaged' in q:
        return 'CPG'
    return None

def _match_agents(query: str, catalog: CatalogLoadResult, *, limit: int=6) -> list[AgentRecord]:
    """Match catalog agents; data copilot queries pin Quin + Eryl + intent classifier."""
    pinned = pinned_copilot_agents(query, catalog.agents)
    if pinned:
        logger.info('Data copilot query — pinned agents: %s', [a.name for a in pinned])
        return pinned[:limit]
    vertical = _detect_vertical(query)
    scored: list[tuple[float, AgentRecord]] = []
    for agent in catalog.agents:
        score = _keyword_score(query, agent)
        if vertical and agent.vertical not in (vertical, 'Other'):
            score *= 0.35
        if score <= 0.05:
            continue
        scored.append((score, agent))
    scored.sort(key=lambda x: (-x[0], x[1].id))
    seen: set[str] = set()
    out: list[AgentRecord] = []
    for _, agent in scored:
        if agent.id in seen:
            continue
        seen.add(agent.id)
        out.append(agent)
        if len(out) >= limit:
            break
    return out

def _input_satisfied_by_query(input_name: str, query: str) -> bool:
    """Skip asking when the problem statement already implies this input."""
    low_q = query.lower()
    low_i = input_name.lower()
    if 'pdf' in low_i or 'docx' in low_i or 'document' in low_i:
        if any((w in low_q for w in ('pdf', 'upload', 'document', 'filing', 'docx'))):
            return True
    if 'client_name' in low_i.replace(' ', '_') and 'client' in low_q:
        return True
    if 'filename' in low_i and ('file' in low_q or 'upload' in low_q):
        return True
    return False

def _chips_for_input(agent: AgentRecord, input_name: str, catalog: CatalogLoadResult | None=None, query: str='') -> list[str]:
    """Catalog chips for ranking (runtime chips rebuilt per turn via cascading_options)."""
    del catalog
    settings = get_settings()
    field_key = agent_input_field_key(agent.id, input_name)
    result = generate_cascading_options(field_key, query, settings, target_agent_id=agent.id, target_input_name=input_name, limit=4)
    return result.options

def _question_for_input(agent: AgentRecord, input_name: str, query: str) -> str:
    hook = query.strip()
    if len(hook) > 60:
        hook = hook[:60].rsplit(' ', 1)[0]
    templates = {'document': f'What document format should {agent.name} accept?', 'pdf': f'What document format should {agent.name} accept?', 'json': f'What JSON payload should {agent.name} receive?', 'policy': f'Which policy or rules should {agent.name} apply?', 'client': f'What client identifier should {agent.name} use?', 'missing': f'When fields are missing, how should {agent.name} behave?', 'image': f'What image input does {agent.name} need?', 'search': f'Which search mode should {agent.name} use?'}
    low = input_name.lower()
    if 'project_id' in low or 'client_summary' in low:
        return f'What customer or case identifier should {agent.name} use for this risk assessment?'
    if 'overrideflags' in low or ('override' in low and 'flag' in low):
        return f'Which override policy should {agent.name} apply when high-risk signals appear?'
    if 'riskfactorscores' in low or 'geography_score' in low:
        return f'How should {agent.name} get the four section scores before calculating final risk?'
    if 'policy json' in low or 'ingestion policy' in low:
        return f'Which KYC policy should {agent.name} use to validate required fields?'
    for key, tmpl in templates.items():
        if key in low:
            return tmpl.replace('**', '')
    return f'For {hook}, what should {agent.name} use for {human_input_label(input_name)}?'

def _build_questions_deterministic(agents: list[AgentRecord], query: str, catalog: CatalogLoadResult | None=None) -> list[AgentSetupQuestionItem]:
    items: list[AgentSetupQuestionItem] = []
    for agent in agents:
        for input_name in agent.inputs:
            if len(items) >= MAX_AGENT_QUESTIONS_SAFETY:
                logger.warning('Agent workflow question list hit safety cap (%d)', MAX_AGENT_QUESTIONS_SAFETY)
                return items
            if _should_skip_input(input_name, query):
                continue
            field_key = agent_input_field_key(agent.id, input_name)
            base_chips = _chips_for_input(agent, input_name, catalog, query)
            impact, dependency, uncertainty, criticality = _score_components(input_name, base_chips)
            items.append(AgentSetupQuestionItem(field_key=field_key, agent_id=agent.id, agent_name=agent.name, input_name=input_name, question=_question_for_input(agent, input_name, query), chips=base_chips, cluster=_cluster_for_input(input_name), impact_score=impact, dependency_score=dependency, uncertainty_score=uncertainty, business_criticality_score=criticality, rank_score=_rank_score(impact, dependency, uncertainty, criticality)))
    return items

def _parse_llm_workflow(raw: str, catalog: CatalogLoadResult, query: str) -> AgentWorkflowState | None:
    try:
        parsed = json.loads(strip_json_fences(raw))
    except json.JSONDecodeError:
        return None
    by_id = {a.id: a for a in catalog.agents}
    by_id.update({slugify(a.name): a for a in catalog.agents})
    matched: list[MatchedAgentSummary] = []
    for row in parsed.get('matched_agents') or []:
        if not isinstance(row, dict):
            continue
        aid = str(row.get('agent_id') or '').strip()
        agent = by_id.get(aid) or by_id.get(slugify(str(row.get('name') or '')))
        if not agent:
            continue
        matched.append(MatchedAgentSummary(agent_id=agent.id, name=agent.name, reason=str(row.get('reason') or agent.function_summary[:120])))
    questions: list[AgentSetupQuestionItem] = []
    for row in parsed.get('questions') or []:
        if not isinstance(row, dict) or len(questions) >= MAX_AGENT_QUESTIONS_SAFETY:
            break
        aid = str(row.get('agent_id') or '').strip()
        agent = by_id.get(aid)
        if not agent:
            continue
        input_name = str(row.get('input_name') or '').strip()
        if not input_name:
            continue
        qtext = str(row.get('question') or '').strip()
        raw_chips = [str(c).strip() for c in row.get('chips') or [] if str(c).strip()]
        if not qtext:
            qtext = _question_for_input(agent, input_name, query)
        det = _chips_for_input(agent, input_name, catalog, query)
        chips = merge_and_gate_chips(deterministic=det, llm=raw_chips, input_name=input_name, agent_summary=agent.function_summary or '')
        impact, dependency, uncertainty, criticality = _score_components(input_name, chips)
        questions.append(AgentSetupQuestionItem(field_key=agent_input_field_key(agent.id, input_name), agent_id=agent.id, agent_name=agent.name, input_name=input_name, question=qtext, chips=chips, cluster=_cluster_for_input(input_name), impact_score=impact, dependency_score=dependency, uncertainty_score=uncertainty, business_criticality_score=criticality, rank_score=_rank_score(impact, dependency, uncertainty, criticality)))
    return AgentWorkflowState(query_understood=str(parsed.get('query_understood') or query[:200]), matched_agents=matched, questions=_dedupe_question_queue(questions), next_index=0)

def _merge_question_queues(primary: list[AgentSetupQuestionItem], supplemental: list[AgentSetupQuestionItem], query: str, session: InterviewSession | None=None) -> list[AgentSetupQuestionItem]:
    """Keep LLM wording first; add any unknown inputs the model skipped."""
    merged = list(primary)
    seen = {q.field_key for q in primary}
    for q in supplemental:
        if q.field_key in seen:
            continue
        merged.append(q)
        seen.add(q.field_key)
        if len(merged) >= MAX_AGENT_QUESTIONS_SAFETY:
            break
    return _finalize_question_queue(merged, query, session)

def _sync_answers_from_messages(state: AgentWorkflowState, messages: list[ChatMessage]) -> None:
    """Rebuild answers from chat history so we never re-ask after refresh."""
    for msg in messages:
        if msg.role != 'user' or not msg.field_key:
            continue
        if not is_agent_input_field_key(msg.field_key):
            continue
        text = msg.content.strip()
        if text and (not is_custom_describe_placeholder(text)):
            _record_answer(state, msg.field_key, text)

def _agents_for_matched(matched: list[MatchedAgentSummary], catalog: CatalogLoadResult) -> list[AgentRecord]:
    by_id = {a.id: a for a in catalog.agents}
    by_id.update({slugify(a.name): a for a in catalog.agents})
    out: list[AgentRecord] = []
    seen: set[str] = set()
    for m in matched:
        agent = by_id.get(m.agent_id)
        if agent and agent.id not in seen:
            seen.add(agent.id)
            out.append(agent)
    return out

def _init_workflow_state(session: InterviewSession, settings: Settings, client: AzureOpenAI) -> AgentWorkflowState:
    """Match agents and build the question queue deterministically (no LLM variance)."""
    del client
    query = discovery_context_blob(session)
    catalog = _load_catalog(settings)
    hint_ids = [h.agent_id for h in session.spec.catalog_hints or [] if h.agent_id]
    agents = _match_agents(query, catalog)
    if hint_ids:
        by_id = {a.id: a for a in catalog.agents}
        pinned = [by_id[aid] for aid in hint_ids if aid in by_id]
        if pinned:
            seen = {a.id for a in agents}
            for agent in pinned:
                if agent.id not in seen:
                    agents.insert(0, agent)
                    seen.add(agent.id)
    if not agents:
        agents = _load_spec_agents(settings)[:3]
    matched = [MatchedAgentSummary(agent_id=a.id, name=a.name, reason=(a.function_summary or '')[:140]) for a in agents]
    state = AgentWorkflowState(query_understood=query[:200], matched_agents=matched, questions=_finalize_question_queue(_build_questions_deterministic(agents, query, catalog), query, session), next_index=0, required_input_count=_compute_required_input_count(agents, query))
    _set_phase(state, 'interview', context='_init_workflow_state:deterministic')
    _refresh_metrics(state)
    return state

def format_workflow_intro(state: AgentWorkflowState) -> str:
    if not state.matched_agents:
        return "I'll ask a few setup questions so we can wire a realistic agent pipeline for your workflow. Pick the closest option or type your own answer."
    names = ', '.join((a.name for a in state.matched_agents[:6]))
    extra = ''
    if len(state.matched_agents) > 6:
        extra = f' (+{len(state.matched_agents) - 6} more)'
    return f"Based on your problem, I matched {len(state.matched_agents)} catalog agents for this pipeline: {names}{extra}.\n\nNext I'll ask setup questions for each agent's inputs — select the closest option or describe your own."

def _format_progress_summary(state: AgentWorkflowState) -> str:
    pending = _pending_questions(state)
    return f'Progress: Coverage {state.coverage_score:.1f}% · Risk {state.risk_score:.1f}/10 · Pending {len(pending)}'

def _format_readiness_report(state: AgentWorkflowState) -> str:
    critical = '\n'.join((f'- {c}' for c in state.critical_items)) if state.critical_items else '- None'
    return f"Readiness Report:\n- Coverage Score: {state.coverage_score:.1f}%\n- Risk Score: {state.risk_score:.1f}/10\n- Completion Reason: {state.completion_reason or 'n/a'}\n- Critical Items:\n{critical}"

def format_workflow_configured(state: AgentWorkflowState, settings: Settings) -> str:
    catalog = _load_catalog(settings)
    by_id = {a.id: a for a in catalog.agents}
    lines = ['Workflow configured:', '', f"Agents: {', '.join((a.name for a in state.matched_agents))}", 'Inputs:']
    for q in state.questions:
        val = state.answers.get(q.field_key, '—')
        lines.append(f'  - {q.agent_name} / {q.input_name}: {val}')
    lines.append('')
    for a in state.matched_agents:
        agent = by_id.get(a.agent_id)
        if agent:
            lines.append(f"Tech stack ({a.name}): {', '.join(agent.tech_stack[:6])}")
            lines.append(f"Integrations ({a.name}): {', '.join(agent.integrations[:6])}")
    lines.append('')
    lines.append('Ready to scaffold architecture in the workflow builder.')
    return '\n'.join(lines)

def _question_item_to_interview(q: AgentSetupQuestionItem, settings: Settings | None=None, session: InterviewSession | None=None, client: AzureOpenAI | None=None) -> InterviewQuestion:
    """Build question with chips derived from catalog data and prior selections."""
    agent: AgentRecord | None = None
    if settings:
        for row in _load_spec_agents(settings):
            if row.id == q.agent_id:
                agent = row
                break
    query = session.spec.problem_statement if session else ''
    messages = session.messages if session else []
    spec = session.spec if session else None
    state = session.agent_workflow if session else None
    workflow_answers = dict(state.answers) if state else {}
    clarifying_answers = dict(session.clarifying_answers) if session else {}
    questions_by_key = {item.field_key: item for item in state.questions} if state else {}
    turn_index = sum((1 for m in messages if m.role == 'user' and m.content.strip()))
    reason = f'Options for `{q.input_name}` on {q.agent_name}.' if agent else f'Maps to spec.json input: {q.input_name}.'
    suggested: str | None = None
    if agent and settings:
        chips, suggested, reason = build_agent_input_chips(agent, q.input_name, query, settings, spec=spec, messages=messages, turn_index=turn_index, client=client, question_text=q.question, workflow_answers=workflow_answers, clarifying_answers=clarifying_answers, questions_by_key=questions_by_key, field_key=q.field_key)
    elif q.chips:
        chips = list(q.chips)
    else:
        chips = [OTHER_CHIP]
    if not suggested:
        suggested = pick_suggested_chip(chips, query=query, rank_hint=q.rank_score)
    topic = q.cluster or q.agent_name
    why = f'Defines {human_input_label(q.input_name)} for {q.agent_name} so the deployed workflow is executable end-to-end.'
    return InterviewQuestion(field_key=q.field_key, topic_label=topic, question=_polish_question_text(q.question, q.agent_name, q.input_name), chips=chips, why_it_matters=why, suggested_chip=suggested, catalog_reference=q.agent_name, suggestion_reason=reason)

def _append_assistant_turn(session: InterviewSession, content: str, question: InterviewQuestion | None) -> None:
    body = content
    if question and session.agent_workflow is not None:
        body = format_new_question_message(session, question, why=question.why_it_matters or '')
    session.messages.append(ChatMessage(role='assistant', content=body, field_key=question.field_key if question else None))

def _catalog_hints_for_workflow(session: InterviewSession, state: AgentWorkflowState, settings: Settings):
    """Catalog context for the interview — matched agents only when fast mode is on."""
    if interview_uses_fast_chips():
        catalog = _load_catalog(settings)
        by_id = _agent_by_id(catalog.agents)
        hints = []
        for m in state.matched_agents:
            agent = by_id.get(m.agent_id)
            if agent:
                hints.append(_hint_from_agent(agent, 0.9))
        return hints[:8]
    hint_ids = [a.agent_id for a in state.matched_agents]
    return build_catalog_hints_for_interview(session.spec.problem_statement, settings, top_k=8, preferred_agent_ids=hint_ids)

def begin_agent_workflow_interview(session: InterviewSession, settings: Settings, client: AzureOpenAI) -> InterviewSession:
    session.agent_workflow = _init_workflow_state(session, settings, client)
    state = session.agent_workflow
    state.current_phase = 'start'
    _sync_answers_from_messages(state, session.messages)
    _refresh_metrics(state)
    session.spec.catalog_hints = _catalog_hints_for_workflow(session, state, settings)
    pending = _pending_questions(state)
    if not pending:
        _set_phase(state, 'completion_check', context='begin:no_pending')
        session.spec.transcript_summary = format_workflow_configured(state, settings)
        session.spec.status = 'ready'
        session.messages.append(ChatMessage(role='assistant', content=_format_readiness_report(state) + '\n\n' + session.spec.transcript_summary))
        _set_phase(state, 'handover', context='begin:finalize_no_pending')
        return _finalize_session(session, settings, client)
    _set_phase(state, 'interview', context='begin:first_question')
    q = pending[0]
    interview_q = _question_item_to_interview(q, settings, session, client)
    session.pending_question = interview_q
    state.current_cluster = q.cluster
    intro = format_workflow_intro(state)
    _append_assistant_turn(session, f'{intro}\n\n{interview_q.question}' if intro else interview_q.question, interview_q)
    return session

def advance_agent_workflow_turn(session: InterviewSession, settings: Settings, user_answer: str | None, client: AzureOpenAI, *, answered_field_key: str | None=None) -> InterviewSession:
    if session.agent_workflow is None:
        return begin_agent_workflow_interview(session, settings, client)
    state = session.agent_workflow
    _sync_answers_from_messages(state, session.messages)
    _refresh_metrics(state)
    if user_answer is not None:
        answer = user_answer.strip()
        field_key = answered_field_key or (session.pending_question.field_key if session.pending_question else None)
        if not field_key:
            logger.warning('Agent workflow answer without field_key — ignored')
        else:
            _record_answer(state, field_key, answer)
        session.pending_question = None
    if _workflow_is_complete(state, user_answer=user_answer):
        _set_phase(state, 'completion_check', context='advance:completion_gate')
        session.spec.transcript_summary = format_workflow_configured(state, settings)
        session.spec = update_spec(session.spec, session.messages, settings, client=client)
        session.messages.append(ChatMessage(role='assistant', content=_format_readiness_report(state) + '\n\n' + format_workflow_configured(state, settings)))
        session.spec.status = 'ready'
        _set_phase(state, 'handover', context='advance:finalize_after_completion')
        return _finalize_session(session, settings, client)
    pending = _pending_questions(state)
    if not pending:
        session.spec.status = 'ready'
        _set_phase(state, 'handover', context='advance:no_pending')
        return _finalize_session(session, settings, client)
    _set_phase(state, 'interview', context='advance:next_question')
    q = pending[0]
    interview_q = _question_item_to_interview(q, settings, session, client)
    session.pending_question = interview_q
    state.current_cluster = q.cluster
    _append_assistant_turn(session, interview_q.question, interview_q)
    return session


# ========================================================================
# services/chat_assistant.py
# ========================================================================


import logging
from openai import AzureOpenAI
logger = logging.getLogger(__name__)
_OPEN_CHAT_HISTORY_LIMIT = 14

def answer_help_request(question: str, session: InterviewSession) -> str:
    """Rule-based fallback when the LLM is unavailable."""
    q = question.lower().strip()
    if 'what answers' in q or 'what can you generate' in q or 'what can you do' in q or (q == 'help'):
        return "You can ask me anything — workflow ideas, architecture concepts, integration options, or how to write a problem statement.\n\nWhen you're ready to build, describe what you want automated (inputs, process, outputs) and I'll switch into workflow scoping."
    if 'problem statement' in q or 'workflow idea' in q or 'workflow ideas' in q or ('examples' in q) or ('example' in q):
        return 'Example workflow ideas:\n\n1. Invoice processing automation\n2. Resume screening assistant\n3. Customer support copilot\n4. Insurance claim verification\n5. Virtual try-on with human review on low confidence\n6. KYC document pre-screening with analyst queue\n\nPick one to discuss, or describe your own in a few sentences.'
    if 'chatbot' in q or 'copilot' in q:
        return 'A data copilot workflow often: accepts user questions, retrieves context from SQL and documents, generates answers with an LLM, routes low-confidence responses to a reviewer, and logs conversations.'
    if 'hitl' in q:
        return 'HITL (Human-In-The-Loop) means a person reviews, approves, or corrects AI output before the workflow continues.'
    if 'integration' in q or 'integrations' in q:
        return 'Common integrations: CRM, email, blob storage, SQL databases, REST APIs, Slack/Teams, and ERP systems.'
    if session.pending_question:
        return f'I can explain the current scoping question:\n\n{session.pending_question.question}\n\nAsk why it matters, for examples, or what typical answers look like.'
    return 'Ask me anything about workflows, agents, or architecture. When you want to build, describe the automation you need in 2–4 sentences.'

def answer_open_chat_turn(message: str, session: InterviewSession, settings: Settings, client: AzureOpenAI | None=None) -> str:
    """Natural multi-turn chat — does not advance workflow state."""
    llm_client = client or make_client(settings)
    system = load_prompt('open_chat_assistant.txt')
    history: list[dict[str, str]] = [{'role': 'system', 'content': system}]
    for msg in session.messages[-_OPEN_CHAT_HISTORY_LIMIT:]:
        if not msg.content.strip():
            continue
        role = 'assistant' if msg.role == 'assistant' else 'user'
        history.append({'role': role, 'content': msg.content.strip()})
    if not history or history[-1].get('content') != message.strip():
        history.append({'role': 'user', 'content': message.strip()})
    try:
        response = llm_client.chat.completions.create(model=settings.azure_openai_chat_deployment, messages=history, temperature=0.65)
        content = (response.choices[0].message.content or '').strip()
        if content:
            return content
    except Exception as exc:
        logger.warning('Open chat LLM failed, using fallback: %s', exc)
    return answer_help_request(message, session)

def _catalog_explanation_for_message(message: str, settings: Settings) -> str | None:
    """Rule-based explanation when an agent or project name appears in the question."""
    low = message.lower()
    catalog = _load_catalog(settings)
    for agent in catalog.agents:
        name_low = agent.name.lower()
        if name_low in low or any((part in low for part in name_low.split() if len(part) > 4)):
            summary = (agent.function_summary or '').strip()
            if summary:
                return f"{agent.name} is a catalog agent: {summary} Typical inputs: {', '.join(agent.inputs[:3]) or 'see spec'}."
    return None

def answer_scoping_turn(message: str, session: InterviewSession, settings: Settings, client: AzureOpenAI) -> str:
    """Answer the user's question during scoping without advancing the interview."""
    pq = session.pending_question
    hint_ids = [h.agent_id for h in session.spec.catalog_hints or [] if h.agent_id]
    if not hint_ids:
        session.spec.catalog_hints = build_catalog_hints_for_interview(session.spec.problem_statement, settings, top_k=12)
        hint_ids = [h.agent_id for h in session.spec.catalog_hints or [] if h.agent_id]
    catalog_block = format_catalog_brief_for_interview(session.spec.problem_statement, settings, preferred_agent_ids=hint_ids)
    pending = pq.question.strip() if pq else '(none)'
    system = f"You are Launchpad inside AgentForge. The user is scoping a workflow but asked a clarifying question.\n\nRules:\n- Answer their question directly in plain language.\n- Use the catalog context below when relevant.\n- Do NOT repeat the scoping question or dump numbered option lists.\n- Do NOT use markdown headers like 'What I understand'.\n- Keep the reply under 120 words.\n\nWorkflow goal:\n{session.spec.problem_statement[:1500]}\n\nCurrent scoping question (for context only — do not re-ask it):\n{pending}\n\nCatalog context:\n{catalog_block[:4000]}"
    try:
        return call_llm(client, settings, system, message.strip(), temperature=0.4).strip()
    except Exception as exc:
        logger.warning('Scoping chat LLM failed: %s', exc)
    fallback = _catalog_explanation_for_message(message, settings)
    if fallback:
        return fallback
    return answer_help_request(message, session)


# ========================================================================
# services/architecture_validator.py
# ========================================================================


"""Validate Phase 3 architecture plans against spec and catalog evidence."""
import re
from collections import defaultdict
from typing import Literal, Optional
ValidationLevel = Literal['pass', 'warn', 'fail']
_LEVEL_RANK = {'pass': 0, 'warn': 1, 'fail': 2}
SPEC_COVERAGE_CHECKS: list[tuple[str, str, tuple[str, ...]]] = [('latency_target', 'latency', ('latency', 'ms', 'second', 'minute', 'real-time', 'batch', 'sla')), ('accuracy_target', 'accuracy', ('accuracy', 'precision', 'recall', 'f1', 'percent', '%')), ('deployment_platform', 'deployment', ('azure', 'aws', 'gcp', 'kubernetes', 'cloud', 'on-prem', 'deploy')), ('data_volume', 'data volume', ('volume', 'gb', 'tb', 'records', 'rows', 'throughput', 'scale'))]

def _worst(a: ValidationLevel, b: ValidationLevel) -> ValidationLevel:
    return a if _LEVEL_RANK[a] >= _LEVEL_RANK[b] else b

def _tokens(text: str) -> set[str]:
    return {t for t in re.findall('[a-z0-9]{3,}', text.lower()) if len(t) >= 3}

def _spec_value(spec: ArchitectureSpec, key: str) -> str:
    field = spec.fields.get(key)
    if field and field.is_known and field.value:
        return field.value.strip()
    return ''

def _graph_text(graph: GraphDraft) -> str:
    parts: list[str] = []
    for node in graph.nodes:
        parts.append(node.label)
        if node.description:
            parts.append(node.description)
    for edge in graph.edges:
        if edge.label:
            parts.append(edge.label)
    return ' '.join(parts).lower()

def _forward_reachable(graph: GraphDraft, starts: list[str]) -> set[str]:
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        adj[edge.from_id].append(edge.to_id)
    seen: set[str] = set()
    stack = [s for s in starts if s]
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        for nxt in adj.get(nid, []):
            if nxt not in seen:
                stack.append(nxt)
    return seen

def _backward_reachable(graph: GraphDraft, starts: list[str]) -> set[str]:
    rev: dict[str, list[str]] = defaultdict(list)
    for edge in graph.edges:
        rev[edge.to_id].append(edge.from_id)
    seen: set[str] = set()
    stack = [s for s in starts if s]
    while stack:
        nid = stack.pop()
        if nid in seen:
            continue
        seen.add(nid)
        for prev in rev.get(nid, []):
            if prev not in seen:
                stack.append(prev)
    return seen

def _undirected_components(graph: GraphDraft) -> list[set[str]]:
    """Connected components treating edges as undirected."""
    parent: dict[str, str] = {}

    def find(x: str) -> str:
        parent.setdefault(x, x)
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]

    def union(a: str, b: str) -> None:
        ra, rb = (find(a), find(b))
        if ra != rb:
            parent[rb] = ra
    for node in graph.nodes:
        find(node.id)
    for edge in graph.edges:
        if edge.from_id in parent or edge.to_id in parent:
            find(edge.from_id)
            find(edge.to_id)
            union(edge.from_id, edge.to_id)
    groups: dict[str, set[str]] = defaultdict(set)
    for node in graph.nodes:
        groups[find(node.id)].add(node.id)
    return list(groups.values())

def make_finding_key(code: str, message: str, node_id: Optional[str]=None, *, edge_from: Optional[str]=None, edge_to: Optional[str]=None, spec_key: Optional[str]=None, question_index: Optional[int]=None) -> str:
    if code == 'open_question' and question_index is not None:
        return f'open_question:{question_index}'
    if code == 'dangling_edge' and edge_from and edge_to:
        return f'dangling_edge:{edge_from}:{edge_to}'
    if spec_key:
        return f'{code}:{spec_key}'
    return f"{code}:{node_id or '_'}"

def finding_id_from_item(item: dict) -> str:
    """Stable id used by remediation and resolutions."""
    return item.get('finding_key') or make_finding_key(item['code'], item['message'], item.get('node_id'))

class ValidationItem:
    """Single validation finding."""
    __slots__ = ('level', 'code', 'message', 'node_id', 'finding_key', 'blocks_approval', 'help_text')

    def __init__(self, level: ValidationLevel, code: str, message: str, node_id: Optional[str]=None, *, finding_key: Optional[str]=None, blocks_approval: Optional[bool]=None, help_text: str='', edge_from: Optional[str]=None, edge_to: Optional[str]=None, spec_key: Optional[str]=None, question_index: Optional[int]=None) -> None:
        self.level = level
        self.code = code
        self.message = message
        self.node_id = node_id
        self.finding_key = finding_key or make_finding_key(code, message, node_id, edge_from=edge_from, edge_to=edge_to, spec_key=spec_key, question_index=question_index)
        self.blocks_approval = blocks_approval if blocks_approval is not None else level == 'fail'
        self.help_text = help_text

    def to_dict(self) -> dict:
        out = {'level': self.level, 'code': self.code, 'message': self.message, 'node_id': self.node_id, 'finding_key': self.finding_key, 'blocks_approval': self.blocks_approval, 'help_text': self.help_text}
        return out

def validate_architecture_plan(spec: ArchitectureSpec, plan: ArchitecturePlan) -> dict:
    """
    Run rule-based validation on a planned architecture.

    Returns:
        JSON-serializable report with overall status, counts, items, and per-node status.
    """
    items: list[ValidationItem] = []
    graph = plan.graph
    node_ids = {n.id for n in graph.nodes}
    id_list = [n.id for n in graph.nodes]
    if len(id_list) != len(node_ids):
        dupes = [nid for nid in id_list if id_list.count(nid) > 1]
        items.append(ValidationItem('fail', 'duplicate_node_id', f"Duplicate component ids: {', '.join(sorted(set(dupes))[:5])}.", blocks_approval=True, help_text='Regenerate architecture or fix duplicate ids in the plan.'))
    decisions_by_node = {d.node_id: d for d in plan.reuse_decisions}
    catalog_ids = {m.agent_id for m in plan.catalog_matches}
    catalog_by_id = {m.agent_id: m for m in plan.catalog_matches}
    graph_blob = _graph_text(graph)
    if not plan.catalog_matches:
        items.append(ValidationItem('warn', 'catalog_empty', 'No catalog agents were matched — reuse options may be limited.', help_text='Refresh catalog search or regenerate architecture after indexing.'))
    for dec in plan.reuse_decisions:
        if dec.node_id not in node_ids:
            items.append(ValidationItem('fail', 'stale_decision', f"Reuse decision references missing component '{dec.node_id}' ({dec.node_label}).", node_id=dec.node_id, finding_key=f'stale_decision:{dec.node_id}', help_text='Remove stale decision or regenerate the graph.'))
    if not graph.nodes:
        items.append(ValidationItem('fail', 'empty_graph', 'Architecture has no components.', help_text='Regenerate architecture from your specification.'))
    else:
        items.append(ValidationItem('pass', 'has_nodes', f'Graph has {len(graph.nodes)} components and {len(graph.edges)} connections.'))
    for edge in graph.edges:
        if edge.from_id not in node_ids:
            items.append(ValidationItem('fail', 'dangling_edge', f"Connection references missing source '{edge.from_id}'.", edge_from=edge.from_id, edge_to=edge.to_id or '_', help_text='Remove invalid edge or restore the missing component.'))
        if edge.to_id not in node_ids:
            items.append(ValidationItem('fail', 'dangling_edge', f"Connection references missing target '{edge.to_id}'.", edge_from=edge.from_id or '_', edge_to=edge.to_id, help_text='Remove invalid edge or restore the missing component.'))
    in_degree = {nid: 0 for nid in node_ids}
    out_degree = {nid: 0 for nid in node_ids}
    for edge in graph.edges:
        if edge.from_id in out_degree:
            out_degree[edge.from_id] += 1
        if edge.to_id in in_degree:
            in_degree[edge.to_id] += 1
    sources = [nid for nid in node_ids if in_degree[nid] == 0]
    sinks = [nid for nid in node_ids if out_degree[nid] == 0]
    if not sources and node_ids:
        items.append(ValidationItem('warn', 'no_entry', 'No clear entry point — every step has an incoming connection.', help_text='Add an entry gateway or confirm a cyclic flow is intentional.'))
    if not sinks and node_ids:
        items.append(ValidationItem('warn', 'no_exit', 'No clear exit point — every step has an outgoing connection.', help_text='Confirm the flow is intentional or add a terminal step.'))
    if graph.edges and node_ids:
        fwd = _forward_reachable(graph, sources if sources else list(node_ids)[:1])
        bwd = _backward_reachable(graph, sinks if sinks else list(node_ids)[:1])
        on_path = fwd & bwd
        for node in graph.nodes:
            if node.id not in on_path:
                items.append(ValidationItem('warn', 'orphan_node', f"'{node.label}' is not on any entry→exit path.", node_id=node.id, help_text='Connect this step to the main flow or remove it.'))
    components = _undirected_components(graph)
    if len(components) > 1 and graph.nodes:
        sizes = sorted((len(c) for c in components), reverse=True)
        items.append(ValidationItem('warn', 'disconnected_subgraph', f"Graph has {len(components)} disconnected groups (sizes: {', '.join(map(str, sizes[:5]))}).", help_text='Add connections between groups or split into separate diagrams.'))
    for node in graph.nodes:
        dec = decisions_by_node.get(node.id)
        if not dec and node.type in ('agent', 'custom', 'gateway', 'human'):
            items.append(ValidationItem('warn', 'missing_decision', f"No reuse decision recorded for '{node.label}' ({node.type}).", node_id=node.id, help_text='Assign reuse, adapt, or build for this step.'))
        if not dec:
            continue
        if dec.decision in ('reuse', 'adapt'):
            if not dec.agent_id:
                items.append(ValidationItem('fail', 'reuse_no_agent', f"'{node.label}' marked {dec.decision} but no catalog agent id.", node_id=node.id, help_text='Pick a catalog agent or mark as custom build.'))
            elif dec.agent_id not in catalog_ids:
                items.append(ValidationItem('fail', 'unknown_agent_id', f"Agent id '{dec.agent_id}' was not in catalog search results.", node_id=node.id, help_text='Refresh catalog search or choose another agent.'))
            else:
                match = catalog_by_id.get(dec.agent_id)
                if match and match.score < 0.3:
                    items.append(ValidationItem('warn', 'low_catalog_score', f"Catalog match score is low ({match.score:.2f}) for '{match.name}'.", node_id=node.id))
                node_tokens = _tokens(f"{node.label} {node.description or ''} {dec.rationale}")
                agent_text = match.function_summary if match else dec.agent_name or ''
                agent_tokens = _tokens(agent_text)
                if node_tokens and agent_tokens:
                    overlap = len(node_tokens & agent_tokens) / max(len(node_tokens), 1)
                    if overlap < 0.08:
                        items.append(ValidationItem('warn', 'weak_catalog_fit', f"'{node.label}' may not match catalog agent capabilities (review fit).", node_id=node.id))
                    else:
                        items.append(ValidationItem('pass', 'catalog_fit', f"Catalog agent '{dec.agent_name or dec.agent_id}' aligns with this step.", node_id=node.id))
        if dec.decision == 'build':
            items.append(ValidationItem('pass', 'build_ok', f"Custom build for '{node.label}' — confirm no catalog alternative.", node_id=node.id))
    for field_key, label, hint_tokens in SPEC_COVERAGE_CHECKS:
        text = _spec_value(spec, field_key)
        if not text or len(text) < 8:
            continue
        field_tokens = _tokens(text)
        hint_hits = [t for t in hint_tokens if t in graph_blob]
        token_hits = len(field_tokens & _tokens(graph_blob))
        if len(field_tokens) >= 2 and token_hits < 1 and (len(hint_hits) < 1):
            items.append(ValidationItem('warn', 'spec_coverage_gap', f"Spec '{label}' may not be reflected on the architecture diagram.", spec_key=field_key, help_text=f'Add components or labels referencing {label}, or acknowledge.'))
    hitl = _spec_value(spec, 'hitl_behavior').lower()
    if hitl and any((w in hitl for w in ('human', 'analyst', 'approval', 'review', 'hitl'))):
        has_human = any((n.type == 'human' for n in graph.nodes))
        if not has_human:
            items.append(ValidationItem('warn', 'hitl_missing', "Spec requires human-in-the-loop but no 'human' step appears on the graph.", help_text='Add a human approval step or acknowledge HITL is external.'))
        else:
            items.append(ValidationItem('pass', 'hitl_present', 'Human-in-the-loop step present as specified.'))
    integrations = _spec_value(spec, 'integrations')
    if integrations:
        int_tokens = _tokens(integrations)
        found = [t for t in int_tokens if t in graph_blob]
        if len(int_tokens) >= 2 and len(found) < max(1, len(int_tokens) // 3):
            items.append(ValidationItem('warn', 'integrations_gap', f"Integrations in spec may not appear on the graph (found: {', '.join(found[:5]) or 'none'}).", help_text='Add integration gateway/labels or acknowledge implicit integrations.'))
        elif found:
            items.append(ValidationItem('pass', 'integrations_reflected', 'Key integrations from spec appear in the architecture.'))
    use_case = _spec_value(spec, 'use_case')
    if use_case and len(use_case) > 20:
        uc_tokens = _tokens(use_case)
        overlap_graph = len(uc_tokens & _tokens(graph_blob)) / max(len(uc_tokens), 1)
        if overlap_graph < 0.05:
            items.append(ValidationItem('warn', 'use_case_drift', 'Use case text has little overlap with component names — verify flow matches intent.', help_text='Compare canvas to specification use case.'))
        else:
            items.append(ValidationItem('pass', 'use_case_aligned', 'Architecture text overlaps with stated use case.'))
    flow_spec = _spec_value(spec, 'architectural_flow_feedback') or _spec_value(spec, 'architectural_flow')
    if flow_spec and len(graph.nodes) >= 2:
        items.append(ValidationItem('pass', 'flow_documented', 'Architectural flow was confirmed in the interview — compare visually to canvas.', help_text='Validation checks structure and spec overlap, not full business correctness.'))
    for idx, q in enumerate(plan.open_questions):
        items.append(ValidationItem('warn', 'open_question', q, question_index=idx, help_text='Resolve or acknowledge open planning questions.'))
    items.append(ValidationItem('pass', 'validation_scope', 'Automated checks cover structure, catalog ids, and spec overlap — not full business proof.', blocks_approval=False))
    node_status: dict[str, ValidationLevel] = {}
    for node in graph.nodes:
        node_status[node.id] = 'pass'
    pass_count = warn_count = fail_count = 0
    structural_fail_count = 0
    overall: ValidationLevel = 'pass'
    for item in items:
        if item.level == 'pass':
            pass_count += 1
        elif item.level == 'warn':
            warn_count += 1
        else:
            fail_count += 1
            if item.blocks_approval:
                structural_fail_count += 1
        overall = _worst(overall, item.level)
        if item.node_id and item.node_id in node_status:
            node_status[item.node_id] = _worst(node_status[item.node_id], item.level)
    if fail_count > 0:
        overall = 'fail'
    elif warn_count > 0 and overall == 'pass':
        overall = 'warn'
    return {'overall': overall, 'pass_count': pass_count, 'warn_count': warn_count, 'fail_count': fail_count, 'structural_fail_count': structural_fail_count, 'items': [i.to_dict() for i in items], 'node_status': node_status}


# ========================================================================
# pipeline/chunker.py
# ========================================================================


"""Split document sections into project-level chunks for LLM extraction."""
import logging
import re
from dataclasses import dataclass
logger = logging.getLogger(__name__)
MAX_WORDS = int(6000 * 0.75)
WARN_TOKEN_THRESHOLD = 5000
PROJECT_BOUNDARY_KEYWORDS = re.compile('\\b(project|engagement|case study|solution|client)\\b', re.IGNORECASE)
CLIENT_LINE = re.compile('^(client|customer|for)\\s*:\\s*(.+)$', re.IGNORECASE | re.MULTILINE)

@dataclass
class ProjectChunk:
    """A text chunk describing one client project, ready for extraction."""
    raw_text: str
    estimated_start_page: int
    estimated_end_page: int
    title: str = ''

def estimate_token_count(text: str) -> int:
    """
    Estimate token count from word count.

    Uses heuristic: word_count * 1.33.
    """
    return int(len(text.split()) * 1.33)

def _split_at_paragraphs(text: str, max_words: int) -> list[str]:
    """Split text at paragraph boundaries when it exceeds max_words."""
    paragraphs = re.split('\\n\\s*\\n', text)
    chunks: list[str] = []
    current: list[str] = []
    current_words = 0
    for para in paragraphs:
        para_words = len(para.split())
        if current_words + para_words > max_words and current:
            chunks.append('\n\n'.join(current))
            current = [para]
            current_words = para_words
        else:
            current.append(para)
            current_words += para_words
    if current:
        chunks.append('\n\n'.join(current))
    return chunks if chunks else [text]

def _is_project_boundary(section: Section) -> bool:
    """Return True if a section likely starts a new project."""
    title_match = PROJECT_BOUNDARY_KEYWORDS.search(section.title)
    text_intro = section.combined_text[:500]
    has_client = bool(CLIENT_LINE.search(text_intro))
    use_case = bool(re.search('\\b(use case|challenge|business problem|objective)\\b', text_intro, re.IGNORECASE))
    return bool(title_match or has_client or use_case)

def chunk_into_projects(sections: list[Section]) -> list[ProjectChunk]:
    """
    Group sections into project-level chunks suitable for LLM extraction.

    Args:
        sections: Document sections from detect_section_boundaries.

    Returns:
        List of ProjectChunk instances, each within the max token budget.

    Side effects:
        Logs WARNING for chunks exceeding WARN_TOKEN_THRESHOLD estimated tokens.
    """
    if not sections:
        return []
    chunks: list[ProjectChunk] = []
    buffer_text: list[str] = []
    buffer_start = sections[0].start_page
    buffer_end = sections[0].end_page
    buffer_title = sections[0].title

    def flush_buffer() -> None:
        nonlocal buffer_text, buffer_start, buffer_end, buffer_title
        if not buffer_text:
            return
        combined = '\n\n'.join(buffer_text)
        for part in _split_at_paragraphs(combined, MAX_WORDS):
            est_tokens = estimate_token_count(part)
            if est_tokens > WARN_TOKEN_THRESHOLD:
                logger.warning("Chunk '%s' (pages %d-%d) estimated at %d tokens", buffer_title, buffer_start, buffer_end, est_tokens)
            chunks.append(ProjectChunk(raw_text=part, estimated_start_page=buffer_start, estimated_end_page=buffer_end, title=buffer_title))
        buffer_text = []
    for i, section in enumerate(sections):
        if i > 0 and _is_project_boundary(section) and buffer_text:
            flush_buffer()
            buffer_start = section.start_page
            buffer_title = section.title
        buffer_text.append(section.combined_text)
        buffer_end = section.end_page
    flush_buffer()
    logger.info('Created %d project chunks from %d sections', len(chunks), len(sections))
    return chunks

def chunk_whole_document(pages: list) -> list[ProjectChunk]:
    """
    Treat the entire PDF as a single extraction unit (no section splitting).

    Use when you want one LLM pass over the full document.
    """
    if not pages:
        return []
    text = whole_document_text(pages)
    chunk = ProjectChunk(raw_text=text, estimated_start_page=pages[0].page_number, estimated_end_page=pages[-1].page_number, title='Full document')
    logger.info('Whole-document mode: 1 chunk, pages %d-%d, ~%d words', chunk.estimated_start_page, chunk.estimated_end_page, len(text.split()))
    return [chunk]


# ========================================================================
# pipeline/embedder.py
# ========================================================================


"""Compute vector embeddings for agent records via Azure OpenAI."""
import logging
import time
from openai import AzureOpenAI
logger = logging.getLogger(__name__)
BATCH_SIZE = 16
BATCH_SLEEP_SECONDS = 1

def _build_embed_text(record: AgentRecord) -> str:
    """Construct the text blob to embed for a single agent record."""
    return f"\nAgent: {record.name}\nFunction: {record.function_summary}\nInputs: {', '.join(record.inputs)}\nOutputs: {', '.join(record.outputs)}\nCategory: {record.category}\nIntegrations: {', '.join(record.integrations)}\nTech: {', '.join(record.tech_stack)}\n".strip()

def embed_query(query: str, settings: Settings, client: AzureOpenAI | None=None) -> list[float]:
    """
    Embed a search query string for vector search.

    Args:
        query: Natural language search query.
        settings: Application settings.
        client: Optional pre-configured Azure OpenAI client.

    Returns:
        Embedding vector (dimension count from config.EMBEDDING_DIMENSIONS).

    Side effects:
        One Azure OpenAI embeddings API call.
    """
    if client is None:
        client = AzureOpenAI(azure_endpoint=settings.azure_openai_endpoint, api_key=settings.azure_openai_api_key, api_version=settings.azure_openai_api_version)
    response = client.embeddings.create(input=query, model=settings.azure_openai_embedding_deployment, dimensions=EMBEDDING_DIMENSIONS)
    return response.data[0].embedding

def compute_embeddings(records: list[AgentRecord], settings: Settings, client: AzureOpenAI | None=None) -> list[AgentRecord]:
    """
    Compute and attach embeddings to each AgentRecord.

    Args:
        records: Agent records without embeddings.
        settings: Application settings.
        client: Optional pre-configured Azure OpenAI client.

    Returns:
        Same records with embedding field populated.

    Side effects:
        Azure OpenAI embeddings API calls in batches of 16 with 1s pause between batches.
    """
    if not records:
        return records
    if client is None:
        client = AzureOpenAI(azure_endpoint=settings.azure_openai_endpoint, api_key=settings.azure_openai_api_key, api_version=settings.azure_openai_api_version)
    total_batches = (len(records) + BATCH_SIZE - 1) // BATCH_SIZE
    logger.info('Embedding %d agents in %d batches', len(records), total_batches)
    for batch_idx in range(0, len(records), BATCH_SIZE):
        batch = records[batch_idx:batch_idx + BATCH_SIZE]
        texts = [_build_embed_text(r) for r in batch]
        response = client.embeddings.create(input=texts, model=settings.azure_openai_embedding_deployment, dimensions=EMBEDDING_DIMENSIONS)
        for record, item in zip(batch, response.data):
            record.embedding = item.embedding
        batch_num = batch_idx // BATCH_SIZE + 1
        if batch_num < total_batches:
            time.sleep(BATCH_SLEEP_SECONDS)
        logger.info('Embedded batch %d/%d (%d agents)', batch_num, total_batches, len(batch))
    return records


# ========================================================================
# pipeline/pdf_reader.py
# ========================================================================


"""PDF text extraction and section boundary detection using PyMuPDF."""
import logging
import re
from dataclasses import dataclass, field
import fitz
logger = logging.getLogger(__name__)
SECTION_KEYWORDS = re.compile('\\b(project|engagement|case study|solution)\\b', re.IGNORECASE)
NUMBERED_HEADER = re.compile('^(\\d+\\.|\\d+\\))\\s+\\S', re.IGNORECASE)
PROJECT_PREFIX = re.compile('^(project|case study|engagement):\\s*', re.IGNORECASE)

@dataclass
class PageContent:
    """Text and metadata extracted from a single PDF page."""
    page_number: int
    raw_text: str
    block_text: list[tuple]
    has_tables: bool
    word_count: int

@dataclass
class Section:
    """A contiguous range of pages grouped under a section header."""
    title: str
    start_page: int
    end_page: int
    combined_text: str
    pages: list[PageContent] = field(default_factory=list)

def _detect_tables(text: str) -> bool:
    """
    Heuristic: page has tables if ≥3 lines look like numeric data rows.

    A row matches if it has multiple whitespace-separated number groups.
    """
    numeric_rows = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        number_groups = sum((1 for p in parts if re.match('^[\\d,.$%-]+$', p)))
        if number_groups >= 3:
            numeric_rows += 1
            if numeric_rows >= 3:
                return True
    return False

def extract_pages(pdf_path: str) -> list[PageContent]:
    """
    Extract raw text and metadata from each page of a PDF.

    Args:
        pdf_path: Filesystem path to the PDF file.

    Returns:
        List of PageContent instances, one per page (1-indexed page numbers).

    Side effects:
        Opens and closes the PDF via PyMuPDF; logs page count at INFO.
    """
    doc = fitz.open(pdf_path)
    pages: list[PageContent] = []
    try:
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            raw_text = page.get_text('text') or ''
            blocks = page.get_text('blocks') or []
            block_text = [(b[0], b[1], b[2], b[3], b[4]) for b in blocks if len(b) >= 5 and isinstance(b[4], str) and b[4].strip()]
            word_count = len(raw_text.split())
            has_tables = _detect_tables(raw_text)
            pages.append(PageContent(page_number=page_idx + 1, raw_text=raw_text, block_text=block_text, has_tables=has_tables, word_count=word_count))
    finally:
        doc.close()
    logger.info('Extracted %d pages from %s', len(pages), pdf_path)
    return pages

def _is_section_header(line: str, next_line: str | None) -> bool:
    """Return True if a line looks like a section header."""
    stripped = line.strip()
    if not stripped or len(stripped) >= 60:
        return False
    if NUMBERED_HEADER.match(stripped) or PROJECT_PREFIX.match(stripped):
        return True
    if SECTION_KEYWORDS.search(stripped) and len(stripped.split()) <= 8:
        return True
    is_caps = stripped == stripped.upper() and any((c.isalpha() for c in stripped))
    is_title = stripped == stripped.title() and len(stripped.split()) <= 8
    if not (is_caps or is_title):
        return False
    if next_line is None:
        return True
    next_stripped = next_line.strip()
    if not next_stripped:
        return True
    if next_stripped.startswith(('  ', '\t')) or len(next_stripped) > len(stripped) + 20:
        return True
    return is_caps and len(stripped.split()) <= 6

def _combine_page_text(page: PageContent) -> str:
    """Prefer block-ordered text when blocks are available, else raw text."""
    if page.block_text:
        sorted_blocks = sorted(page.block_text, key=lambda b: (b[1], b[0]))
        parts = [b[4].strip() for b in sorted_blocks if b[4].strip()]
        if parts:
            return '\n'.join(parts)
    return page.raw_text

def detect_section_boundaries(pages: list[PageContent]) -> list[Section]:
    """
    Group pages into sections based on detected headers.

    Args:
        pages: PageContent list from extract_pages.

    Returns:
        List of Section objects. Falls back to 3-page windows if no headers found.

    Side effects:
        Logs WARNING when falling back to fixed windows.
    """
    if not pages:
        return []
    headers_found = 0
    sections: list[Section] = []
    current_title = 'Introduction'
    current_pages: list[PageContent] = []
    for page in pages:
        lines = [ln for ln in page.raw_text.splitlines() if ln.strip()]
        header_on_page: str | None = None
        for i, line in enumerate(lines):
            next_line = lines[i + 1] if i + 1 < len(lines) else None
            if _is_section_header(line, next_line):
                header_on_page = line.strip()
                headers_found += 1
                break
        if header_on_page and current_pages:
            combined = '\n\n'.join((_combine_page_text(p) for p in current_pages))
            sections.append(Section(title=current_title, start_page=current_pages[0].page_number, end_page=current_pages[-1].page_number, combined_text=combined, pages=list(current_pages)))
            current_pages = []
            current_title = header_on_page
        current_pages.append(page)
    if current_pages:
        combined = '\n\n'.join((_combine_page_text(p) for p in current_pages))
        sections.append(Section(title=current_title, start_page=current_pages[0].page_number, end_page=current_pages[-1].page_number, combined_text=combined, pages=list(current_pages)))
    if headers_found < 2:
        logger.warning('Few section headers detected (%d); falling back to 3-page windows', headers_found)
        return _fallback_page_windows(pages, window_size=3)
    logger.info('Detected %d sections across %d pages', len(sections), len(pages))
    return sections

def _fallback_page_windows(pages: list[PageContent], window_size: int=3) -> list[Section]:
    """Split pages into fixed-size windows when section detection fails."""
    sections: list[Section] = []
    for i in range(0, len(pages), window_size):
        chunk = pages[i:i + window_size]
        combined = '\n\n'.join((_combine_page_text(p) for p in chunk))
        sections.append(Section(title=f'Pages {chunk[0].page_number}-{chunk[-1].page_number}', start_page=chunk[0].page_number, end_page=chunk[-1].page_number, combined_text=combined, pages=list(chunk)))
    return sections

def whole_document_text(pages: list[PageContent]) -> str:
    """Concatenate all pages into one text blob (no chunking)."""
    parts = []
    for page in pages:
        parts.append(f'--- Page {page.page_number} ---\n{_combine_page_text(page)}')
    return '\n\n'.join(parts)


# ========================================================================
# pipeline/extractor.py
# ========================================================================


"""LLM-based extraction of project and agent records from text chunks."""
import json
import logging
import time
from pathlib import Path
from openai import APIError, APITimeoutError, AzureOpenAI, RateLimitError
from pydantic import ValidationError
logger = logging.getLogger(__name__)
PROMPTS_DIR = BACKEND_ROOT / 'prompts'
MAX_RETRIES = 3
BACKOFF_SECONDS = (2, 4, 8)

def _load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    return (PROMPTS_DIR / filename).read_text(encoding='utf-8')

def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped JSON in them."""
    text = text.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines[0].startswith('```'):
            lines = lines[1:]
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        text = '\n'.join(lines)
    return text.strip()

def _call_llm(client: AzureOpenAI, settings: Settings, system_prompt: str, user_message: str) -> str:
    """
    Call Azure OpenAI chat completion with retry and exponential backoff.

    Raises the last exception after MAX_RETRIES failures.
    """
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(model=settings.azure_openai_chat_deployment, messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_message}], temperature=0.1)
            content = response.choices[0].message.content
            if not content:
                raise ValueError('Empty response from chat completion')
            return content
        except (RateLimitError, APITimeoutError, APIError) as exc:
            last_error = exc
            wait = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
            logger.warning('API error (attempt %d/%d): %s — retrying in %ds', attempt + 1, MAX_RETRIES, exc, wait)
            time.sleep(wait)
    raise last_error or RuntimeError('LLM call failed after retries')

def _parse_project(raw: dict, source_page: int) -> ProjectRecord:
    """Parse and validate a project dict into a ProjectRecord."""
    raw['source_page'] = raw.get('source_page', source_page)
    name = raw.get('name') or 'unknown-project'
    record = ProjectRecord(id=slugify(name), name=name, client=raw.get('client') or '', vertical=normalize_vertical(raw.get('vertical')), business_problem=raw.get('business_problem') or '', solution_summary=raw.get('solution_summary') or '', agents_used=raw.get('agents_used') or [], tech_stack=raw.get('tech_stack') or [], outcomes=raw.get('outcomes'), source_page=int(raw['source_page']))
    return record

def _parse_agents(raw_list: list, source_page: int, origin_project: str, origin_client: str) -> list[AgentRecord]:
    """Parse and validate a list of agent dicts into AgentRecords."""
    agents: list[AgentRecord] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        item['source_page'] = item.get('source_page', source_page)
        item.setdefault('origin_project', origin_project)
        item.setdefault('origin_client', origin_client)
        name = item.get('name') or 'unknown-agent'
        version = item.get('version') or '1.0'
        agent_id = slugify(name)
        if version and version != '1.0':
            agent_id = f"{agent_id}-v{version.replace('.', '-')}"
        record = AgentRecord(id=agent_id, name=name, version=version, category=item['category'], function_summary=item.get('function_summary') or '', inputs=item.get('inputs') or [], outputs=item.get('outputs') or [], model_used=item.get('model_used') or 'Unknown', tech_stack=item.get('tech_stack') or [], integrations=item.get('integrations') or [], origin_project=item.get('origin_project') or origin_project, origin_client=item.get('origin_client') or origin_client, vertical=normalize_vertical(item.get('vertical')), status=item.get('status') or 'available', typical_accuracy=item.get('typical_accuracy'), notes=item.get('notes'), source_page=int(item['source_page']))
        agents.append(record)
    return agents

def extract_project_and_agents(chunk: ProjectChunk, settings: Settings, client: AzureOpenAI | None=None) -> ExtractionOutput:
    """
    Extract ProjectRecord and AgentRecords from a project chunk via two LLM calls.

    Args:
        chunk: Project text chunk with page metadata.
        settings: Application settings with Azure OpenAI credentials.
        client: Optional pre-configured AzureOpenAI client.

    Returns:
        ExtractionOutput with project, agents, and any non-fatal errors.

    Side effects:
        Makes up to 6 Azure OpenAI API calls (2 per chunk, 3 retries each).
    """
    if client is None:
        client = AzureOpenAI(azure_endpoint=settings.azure_openai_endpoint, api_key=settings.azure_openai_api_key, api_version=settings.azure_openai_api_version)
    errors: list[str] = []
    chunk_id = f'pages-{chunk.estimated_start_page}-{chunk.estimated_end_page}'
    project_prompt = _load_prompt('project_extraction.txt')
    agent_prompt = _load_prompt('agent_extraction.txt')
    project: ProjectRecord | None = None
    agents: list[AgentRecord] = []
    user_project = f'Extract the ProjectRecord from this text. Source page: {chunk.estimated_start_page}\n\nTEXT:\n{chunk.raw_text}'
    raw_project_response = ''
    try:
        raw_project_response = _call_llm(client, settings, project_prompt, user_project)
        parsed = json.loads(_strip_json_fences(raw_project_response))
        project = _parse_project(parsed, chunk.estimated_start_page)
    except json.JSONDecodeError as exc:
        msg = f'[{chunk_id}] Project JSON parse error: {exc}'
        logger.error('%s — raw response logged at DEBUG', msg)
        logger.debug('Raw project response: %s', raw_project_response)
        errors.append(msg)
    except ValidationError as exc:
        msg = f'[{chunk_id}] Project validation error: {exc}'
        logger.error(msg)
        errors.append(msg)
    except Exception as exc:
        msg = f'[{chunk_id}] Project extraction failed: {exc}'
        logger.error(msg)
        errors.append(msg)
    project_name = project.name if project else chunk.title or 'Unknown Project'
    project_client = project.client if project else ''
    user_agents = f'Project name: {project_name}\nClient: {project_client}\n\nExtract all AgentRecords from this text. Source page: {chunk.estimated_start_page}\n\nTEXT:\n{chunk.raw_text}'
    try:
        raw_agents = _call_llm(client, settings, agent_prompt, user_agents)
        parsed_agents = json.loads(_strip_json_fences(raw_agents))
        if not isinstance(parsed_agents, list):
            raise ValueError('Agent extraction must return a JSON array')
        agents = _parse_agents(parsed_agents, chunk.estimated_start_page, project_name, project_client)
    except json.JSONDecodeError as exc:
        msg = f'[{chunk_id}] Agent JSON parse error: {exc}'
        logger.error(msg)
        errors.append(msg)
    except ValidationError as exc:
        msg = f'[{chunk_id}] Agent validation error: {exc}'
        logger.error(msg)
        errors.append(msg)
    except Exception as exc:
        msg = f'[{chunk_id}] Agent extraction failed: {exc}'
        logger.error(msg)
        errors.append(msg)
    return ExtractionOutput(project=project, agents=agents, errors=errors)


# ========================================================================
# pipeline/indexer.py
# ========================================================================


"""Index agent records into Azure AI Search and run hybrid queries."""
import logging
from dataclasses import dataclass, field
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
logger = logging.getLogger(__name__)
BATCH_SIZE = 50

@dataclass
class IndexResult:
    """Summary of a bulk index operation."""
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: list[str] = field(default_factory=list)

def _get_search_client(settings: Settings) -> SearchClient:
    """Create an Azure AI Search client for the agent catalog index."""
    return SearchClient(endpoint=settings.azure_search_endpoint, index_name=settings.azure_search_index_name, credential=AzureKeyCredential(settings.azure_search_api_key))

def _record_to_document(record: AgentRecord) -> dict:
    """Serialize an AgentRecord to an Azure AI Search document."""
    return {'id': record.id, 'name': record.name, 'function_summary': record.function_summary, 'version': record.version, 'category': record.category, 'vertical': record.vertical, 'status': record.status, 'origin_client': record.origin_client, 'origin_project': record.origin_project, 'inputs_text': ', '.join(record.inputs), 'outputs_text': ', '.join(record.outputs), 'tech_stack_text': ', '.join(record.tech_stack), 'integrations_text': ', '.join(record.integrations), 'model_used': record.model_used, 'typical_accuracy': record.typical_accuracy or '', 'notes': record.notes or '', 'source_page': record.source_page, 'embedding': record.embedding}

def index_agents(records: list[AgentRecord], settings: Settings) -> IndexResult:
    """
    Upload or merge agent records into Azure AI Search.

    Args:
        records: Agent records with embeddings populated.
        settings: Application settings.

    Returns:
        IndexResult with success and failure counts.

    Side effects:
        Writes documents to Azure AI Search via merge_or_upload_documents (idempotent).
    """
    if not records:
        logger.warning('No records to index')
        return IndexResult()
    client = _get_search_client(settings)
    result = IndexResult(total=len(records))
    errors: list[str] = []
    for batch_start in range(0, len(records), BATCH_SIZE):
        batch = records[batch_start:batch_start + BATCH_SIZE]
        documents = [_record_to_document(r) for r in batch]
        upload_result = client.merge_or_upload_documents(documents=documents)
        for item in upload_result:
            if item.succeeded:
                result.succeeded += 1
            else:
                result.failed += 1
                err_msg = f'Failed to index document {item.key}: {item.error_message}'
                errors.append(err_msg)
                logger.error(err_msg)
    result.errors = errors
    logger.info('Indexing complete: %d succeeded, %d failed of %d total', result.succeeded, result.failed, result.total)
    return result

def _search_agents_vector(client: SearchClient, query: str, query_vector: list[float], top_k: int) -> list[dict]:
    """Keyword + vector search without semantic ranker."""
    vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields='embedding')
    results = client.search(search_text=query, vector_queries=[vector_query], top=top_k, select=['id', 'name', 'function_summary', 'category', 'status', 'origin_client', 'origin_project', 'version'])
    output: list[dict] = []
    for result in results:
        doc = dict(result)
        doc['score'] = result.get('@search.score', 0.0)
        output.append(doc)
    return output

def search_agents(query: str, settings: Settings, top_k: int=5) -> list[dict]:
    """
    Run hybrid (keyword + vector + semantic) search against the agent catalog.

    Args:
        query: Natural language search query.
        settings: Application settings.
        top_k: Maximum number of results to return.

    Returns:
        List of result dicts with id, name, function_summary, category, status,
        origin_client, version, and search score.

    Side effects:
        Azure OpenAI embedding call plus Azure AI Search query.
    """
    from azure.search.documents.models import QueryType
    client = _get_search_client(settings)
    query_vector = embed_query(query, settings)
    vector_query = VectorizedQuery(vector=query_vector, k_nearest_neighbors=top_k, fields='embedding')
    select = ['id', 'name', 'function_summary', 'category', 'status', 'origin_client', 'origin_project', 'version']
    try:
        results = client.search(search_text=query, vector_queries=[vector_query], query_type=QueryType.SEMANTIC, semantic_configuration_name='affine-semantic', top=top_k, select=select)
        output: list[dict] = []
        for result in results:
            doc = dict(result)
            doc['score'] = result.get('@search.score', 0.0)
            output.append(doc)
        return output
    except Exception as exc:
        logger.warning('Semantic search failed, falling back to vector+keyword: %s', exc)
        return _search_agents_vector(client, query, query_vector, top_k)


# ========================================================================
# services/architecture_planner.py
# ========================================================================


"""Phase 3: plan architecture graph with catalog reuse decisions."""
import json
import logging
import re
from typing import Optional
from openai import AzureOpenAI
from pydantic import ValidationError
logger = logging.getLogger(__name__)
MIN_SPEC_STATUS = ('sufficient', 'ready')

def _field_value(spec: ArchitectureSpec, key: str) -> str:
    field = spec.fields.get(key)
    if field and field.is_known and field.value:
        return field.value.strip()
    return ''

def _enriched_problem_context(spec: ArchitectureSpec) -> str:
    """Problem statement plus clarifying summary — same signal as Phase 2 catalog hints."""
    parts: list[str] = []
    if spec.problem_statement.strip():
        parts.append(spec.problem_statement.strip())
    if spec.transcript_summary and spec.transcript_summary.strip():
        parts.append(spec.transcript_summary.strip())
    return '\n\n'.join(parts)

def _build_search_queries(spec: ArchitectureSpec) -> list[str]:
    """Derive catalog search queries from confirmed spec fields."""
    queries: list[str] = []
    enriched = _enriched_problem_context(spec)
    if enriched:
        queries.append(enriched[:800])
    use_case = _field_value(spec, 'use_case')
    if use_case:
        queries.append(use_case[:400])
    for key in ('core_components', 'architectural_flow', 'architectural_flow_feedback', 'data_flow'):
        text = _field_value(spec, key)
        if text and len(text) > 20:
            queries.append(text[:400])
    if not queries:
        queries.append(enriched[:800] if enriched else spec.problem_statement[:500])
    if is_data_copilot_query(spec.problem_statement):
        queries.insert(0, 'Quin SQL Eryl semantic RAG copilot structured unstructured data bot')
    return queries[:4]

def _fetch_catalog_matches(spec: ArchitectureSpec, settings: Settings, *, top_k_per_query: int=5) -> list[CatalogMatch]:
    """
    Run multiple catalog searches and merge by best score per agent id.

    Side effects:
        Azure OpenAI embeddings + Azure AI Search queries.
    """
    by_id: dict[str, CatalogMatch] = {}
    for query in _build_search_queries(spec):
        try:
            rows = search_agents(query, settings, top_k=top_k_per_query)
        except Exception as exc:
            logger.warning('Catalog search failed for query snippet: %s', exc)
            continue
        for row in rows:
            agent_id = str(row.get('id') or '').strip()
            if not agent_id:
                continue
            score = float(row.get('score') or 0.0)
            existing = by_id.get(agent_id)
            if existing and existing.score >= score:
                continue
            by_id[agent_id] = CatalogMatch(agent_id=agent_id, name=str(row.get('name') or 'Unknown'), category=str(row.get('category') or ''), origin_client=str(row.get('origin_client') or ''), origin_project=str(row.get('origin_project') or ''), function_summary=str(row.get('function_summary') or '')[:300], score=score, matched_for=query[:80])
    matches = sorted(by_id.values(), key=lambda m: m.score, reverse=True)
    matches = _ensure_copilot_catalog_matches(spec, settings, matches)
    logger.info('Catalog matches for planning: %d agents', len(matches))
    return matches[:20]

def _ensure_copilot_catalog_matches(spec: ArchitectureSpec, settings: Settings, matches: list[CatalogMatch]) -> list[CatalogMatch]:
    """Pin Quin + Eryl + intent classifier for data copilot problems."""
    if not is_data_copilot_query(spec.problem_statement):
        return matches
    catalog = _load_catalog(settings)
    by_agent = _agent_by_id(catalog.agents)
    by_id = {m.agent_id: m for m in matches}
    for aid in DATA_COPILOT_AGENT_IDS:
        agent = by_agent.get(aid)
        if not agent:
            continue
        existing = by_id.get(aid)
        if existing:
            existing.score = max(existing.score, 0.92)
            continue
        by_id[aid] = CatalogMatch(agent_id=agent.id, name=agent.name, category=agent.category, origin_client=agent.origin_client, origin_project=agent.origin_project, function_summary=(agent.function_summary or '')[:300], score=0.92, matched_for='data copilot routing (Quin SQL + Eryl RAG)')
    return sorted(by_id.values(), key=lambda m: m.score, reverse=True)

def refresh_catalog_matches(spec: ArchitectureSpec, settings: Settings) -> list[CatalogMatch]:
    """Re-query Azure AI Search for planning/remediation (fresh catalog evidence)."""
    return _fetch_catalog_matches(spec, settings)

def _format_matches_for_prompt(matches: list[CatalogMatch]) -> str:
    if not matches:
        return '(no catalog matches — index empty or search unavailable)'
    lines = []
    for m in matches:
        lines.append(f'- id={m.agent_id} | {m.name} | {m.category} | score={m.score:.2f} | {m.function_summary[:120]}')
    return '\n'.join(lines)

def _format_spec_for_plan(spec: ArchitectureSpec) -> str:
    known = spec.compact_known_json()
    return json.dumps({'problem_statement': spec.problem_statement, 'status': spec.status, 'transcript_summary': spec.transcript_summary, 'known_fields': known, 'architecture_blueprint_excerpt': (spec.architecture_blueprint or '')[:2000]}, indent=2)

def _validate_graph(graph: GraphDraft) -> list[str]:
    """Return validation warnings for the planned graph."""
    warnings: list[str] = []
    node_ids = {n.id for n in graph.nodes}
    if not graph.nodes:
        warnings.append('Graph has no nodes')
        return warnings
    for edge in graph.edges:
        if edge.from_id not in node_ids:
            warnings.append(f'Edge from unknown node: {edge.from_id}')
        if edge.to_id not in node_ids:
            warnings.append(f'Edge to unknown node: {edge.to_id}')
    out_degree = {nid: 0 for nid in node_ids}
    in_degree = {nid: 0 for nid in node_ids}
    for edge in graph.edges:
        out_degree[edge.from_id] = out_degree.get(edge.from_id, 0) + 1
        in_degree[edge.to_id] = in_degree.get(edge.to_id, 0) + 1
    sources = [nid for nid in node_ids if in_degree.get(nid, 0) == 0]
    sinks = [nid for nid in node_ids if out_degree.get(nid, 0) == 0]
    if not sources:
        warnings.append('No clear entry node (all nodes have incoming edges)')
    if not sinks:
        warnings.append('No clear exit node (all nodes have outgoing edges)')
    return warnings

def _normalize_node_id(raw: str) -> str:
    return normalize_node_id(raw)

def _apply_catalog_ids(graph: GraphDraft, matches: list[CatalogMatch]) -> GraphDraft:
    """Ensure agent_id on nodes references a known catalog id when possible."""
    valid_ids = {m.agent_id for m in matches}
    by_name = {m.name.lower(): m.agent_id for m in matches}
    old_to_new: dict[str, str] = {}
    nodes: list[GraphNode] = []
    for node in graph.nodes:
        new_id = _normalize_node_id(node.id)
        old_to_new[node.id] = new_id
        agent_id = node.agent_id
        if agent_id and agent_id not in valid_ids:
            agent_id = None
        if not agent_id and node.type == 'agent':
            agent_id = by_name.get(node.label.lower())
        if agent_id and agent_id not in valid_ids:
            agent_id = None
        nodes.append(node.model_copy(update={'id': new_id, 'agent_id': agent_id}))
    edges: list[GraphEdge] = []
    for edge in graph.edges:
        edges.append(GraphEdge(from_id=old_to_new.get(edge.from_id, _normalize_node_id(edge.from_id)), to_id=old_to_new.get(edge.to_id, _normalize_node_id(edge.to_id)), label=edge.label))
    return sanitize_graph(GraphDraft(nodes=nodes, edges=edges))

def _ensure_reuse_decisions(graph: GraphDraft, decisions: list[ReuseDecision], matches: list[CatalogMatch]) -> list[ReuseDecision]:
    """One reuse decision per graph node; fill gaps after LLM output."""
    by_id = {d.node_id: d for d in decisions}
    out: list[ReuseDecision] = []
    for node in graph.nodes:
        existing = by_id.get(node.id)
        if existing:
            out.append(existing.model_copy(update={'node_label': node.label}))
            continue
        agent_name = None
        if node.agent_id:
            agent_name = next((m.name for m in matches if m.agent_id == node.agent_id), None)
        out.append(ReuseDecision(node_id=node.id, node_label=node.label, decision='reuse' if node.agent_id else 'build', agent_id=node.agent_id, agent_name=agent_name, rationale='Auto-filled for graph step.'))
    return out

def _fallback_from_graph_draft(spec: ArchitectureSpec, matches: list[CatalogMatch]) -> ArchitecturePlan:
    """Use interview graph_draft when LLM planning fails."""
    graph = sanitize_graph(spec.graph_draft or GraphDraft())
    graph = _apply_catalog_ids(graph, matches)
    decisions = [ReuseDecision(node_id=n.id, node_label=n.label, decision='reuse' if n.agent_id else 'build', agent_id=n.agent_id, agent_name=next((m.name for m in matches if m.agent_id == n.agent_id), None), rationale='From interview graph draft (LLM plan unavailable).') for n in graph.nodes]
    return ArchitecturePlan(graph=graph, reuse_decisions=decisions, catalog_matches=matches, summary_markdown=spec.architecture_blueprint or 'Architecture plan from interview draft.', open_questions=['LLM planner failed — review graph draft manually.'])

def plan_architecture(session: InterviewSession, settings: Settings, client: AzureOpenAI | None=None) -> ArchitecturePlan:
    """
    Build a Phase 3 architecture plan from a completed interview session.

    Args:
        session: Interview session with spec status sufficient or ready.
        settings: Azure settings.
        client: Optional OpenAI client.

    Returns:
        ArchitecturePlan with graph, reuse decisions, and summary.

    Raises:
        ValueError: If spec is not complete enough for planning.
    """
    spec = session.spec
    if spec.status not in MIN_SPEC_STATUS:
        raise ValueError(f"Specification status must be 'sufficient' or 'ready' (got '{spec.status}'). Complete more of the interview first.")
    if client is None:
        client = make_client(settings)
    matches = _fetch_catalog_matches(spec, settings)
    system = load_prompt('architecture_plan.txt')
    draft_json = spec.graph_draft.model_dump_json(indent=2) if spec.graph_draft else '{"nodes":[],"edges":[]}'
    user = f'PROBLEM STATEMENT:\n{spec.problem_statement}\n\nSPEC:\n{_format_spec_for_plan(spec)}\n\nINTERVIEW GRAPH_DRAFT:\n{draft_json}\n\nCATALOG MATCHES:\n{_format_matches_for_prompt(matches)}'
    try:
        raw = call_llm(client, settings, system, user, json_mode=True, temperature=0.15)
        parsed = json.loads(strip_json_fences(raw))
        graph = GraphDraft.model_validate(parsed.get('graph') or {})
        graph = sanitize_graph(graph)
        graph = _apply_catalog_ids(graph, matches)
        decisions_raw = parsed.get('reuse_decisions') or []
        decisions: list[ReuseDecision] = []
        for item in decisions_raw:
            if isinstance(item, dict):
                try:
                    decisions.append(ReuseDecision.model_validate(item))
                except ValidationError:
                    continue
        decisions = _ensure_reuse_decisions(graph, decisions, matches)
        plan = ArchitecturePlan(graph=graph, reuse_decisions=decisions, catalog_matches=matches, summary_markdown=(parsed.get('summary_markdown') or '').strip(), open_questions=[str(q) for q in parsed.get('open_questions') or [] if str(q).strip()])
    except Exception as exc:
        logger.error('Architecture planning LLM failed: %s', exc)
        plan = _fallback_from_graph_draft(spec, matches)
    for warning in _validate_graph(plan.graph):
        logger.warning('Graph validation: %s', warning)
        if warning not in plan.open_questions:
            plan.open_questions.append(warning)
    validation_raw = validate_architecture_plan(spec, plan)
    enriched = enrich_validation_report(spec, plan, validation_raw)
    plan.validation = ArchitectureValidationReport.model_validate(enriched)
    logger.info('Architecture validation: overall=%s pass=%d warn=%d fail=%d', plan.validation.overall, plan.validation.pass_count, plan.validation.warn_count, plan.validation.fail_count)
    logger.info('Architecture plan: %d nodes, %d edges, %d reuse decisions', len(plan.graph.nodes), len(plan.graph.edges), len(plan.reuse_decisions))
    return plan


# ========================================================================
# services/architecture_remediation.py
# ========================================================================


"""Remediation options and apply-actions for architecture validation findings."""
import re
import uuid
from typing import Any, Optional
RemediationOption = dict[str, Any]
ResolutionRecord = dict[str, Any]

def _normalize_resolution(resolution: Any) -> Optional[ResolutionRecord]:
    """Coerce ValidationResolution or dict to a plain dict."""
    if resolution is None:
        return None
    if hasattr(resolution, 'model_dump'):
        return resolution.model_dump()
    if isinstance(resolution, dict):
        return resolution
    return None

def _resolution_action(resolution: Any) -> str:
    data = _normalize_resolution(resolution)
    return (data or {}).get('action', '')

def _resolutions_as_dicts(plan: ArchitecturePlan) -> dict[str, ResolutionRecord]:
    out: dict[str, ResolutionRecord] = {}
    for k, v in (plan.validation_resolutions or {}).items():
        data = _normalize_resolution(v)
        if data:
            out[k] = data
    return out

def resolve_remediation_option(plan: ArchitecturePlan, finding_id_str: str, option_id: str, spec: Optional[ArchitectureSpec]=None) -> RemediationOption:
    """
    Look up the remediation option from the current plan validation report.
    Falls back to rebuilding options for the finding.
    """
    if not plan.validation:
        raise ValueError('No validation report on plan. Generate architecture first.')
    for item in plan.validation.items:
        raw = item.model_dump() if hasattr(item, 'model_dump') else dict(item)
        fid = finding_id_from_item(raw)
        if fid != finding_id_str:
            continue
        for opt in item.remediations:
            oid = opt.id if hasattr(opt, 'id') else opt.get('id')
            if oid == option_id:
                return opt.model_dump() if hasattr(opt, 'model_dump') else dict(opt)
        raw_level = item.level
        level = raw_level if raw_level in ('warn', 'fail') else 'fail'
        rebuilt = build_remediations(item.code, item.message, level, plan, spec, item.node_id, finding_key=fid)
        for opt in rebuilt:
            if opt.get('id') == option_id:
                return opt
        raise ValueError(f"Option '{option_id}' is not valid for finding '{finding_id_str}'.")
    raise ValueError(f"Finding '{finding_id_str}' not found. Refresh validation or regenerate.")

def _new_node_id(prefix: str) -> str:
    return f'{prefix}_{uuid.uuid4().hex[:8]}'

def _decision_index(plan: ArchitecturePlan) -> dict[str, ReuseDecision]:
    return {d.node_id: d for d in plan.reuse_decisions}

def _upsert_decision(plan: ArchitecturePlan, node_id: str, node_label: str, decision: str, agent_id: Optional[str]=None, agent_name: Optional[str]=None, rationale: str='', catalog_score: Optional[float]=None) -> None:
    existing = _decision_index(plan)
    if node_id in existing:
        d = existing[node_id]
        d.decision = decision
        d.agent_id = agent_id
        d.agent_name = agent_name
        d.rationale = rationale or d.rationale
        d.catalog_score = catalog_score
        d.node_label = node_label
    else:
        plan.reuse_decisions.append(ReuseDecision(node_id=node_id, node_label=node_label, decision=decision, agent_id=agent_id, agent_name=agent_name, rationale=rationale, catalog_score=catalog_score))

def _catalog_for_node(plan: ArchitecturePlan, node_id: str) -> list[CatalogMatch]:
    """Catalog matches relevant to a node (matched_for or all by score)."""
    targeted = [m for m in plan.catalog_matches if m.matched_for == node_id]
    if targeted:
        return sorted(targeted, key=lambda m: m.score, reverse=True)
    return sorted(plan.catalog_matches, key=lambda m: m.score, reverse=True)

def _best_catalog(plan: ArchitecturePlan, node_id: str) -> Optional[CatalogMatch]:
    matches = _catalog_for_node(plan, node_id)
    return matches[0] if matches else None

def _spec_integrations_label(spec: ArchitectureSpec) -> str:
    field = spec.fields.get('integrations')
    if field and field.is_known and field.value:
        first = re.split('[,;\\n]+', field.value.strip())[0].strip()
        if first:
            return first[:60]
    return 'Integration gateway'

def build_remediations(code: str, message: str, level: str, plan: ArchitecturePlan, spec: ArchitectureSpec, node_id: Optional[str]=None, *, finding_key: Optional[str]=None) -> list[RemediationOption]:
    """Return user-facing choices to address a warn/fail finding."""
    if level == 'pass':
        return []
    fid = finding_key or finding_id_from_item({'code': code, 'message': message, 'node_id': node_id})
    options: list[RemediationOption] = []

    def opt(action_id: str, label: str, description: str='', **params: Any) -> RemediationOption:
        return {'id': action_id, 'label': label, 'description': description, 'finding_id': fid, **params}
    node = next((n for n in plan.graph.nodes if n.id == node_id), None) if node_id else None
    dec = _decision_index(plan).get(node_id) if node_id else None
    catalog = _catalog_for_node(plan, node_id) if node_id else []
    if code in ('catalog_empty',):
        options.append(opt('refresh_catalog', 'Refresh catalog search', 'Re-query the agent index with your current specification.', action='refresh_catalog'))
    if code in ('reuse_no_agent', 'unknown_agent_id', 'missing_decision'):
        if not catalog:
            options.append(opt('refresh_catalog', 'Refresh catalog search', 'Load catalog agents before assigning reuse.', action='refresh_catalog'))
        if catalog:
            for i, m in enumerate(catalog[:3]):
                options.append(opt(f'use_catalog_{m.agent_id}', f'Use catalog: {m.name}', f'Set reuse with {m.name} (score {m.score:.2f}).', action='set_decision', node_id=node_id, decision='reuse', agent_id=m.agent_id, agent_name=m.name, catalog_score=m.score))
            if len(catalog) > 1:
                options.append(opt('adapt_top_catalog', 'Adapt top catalog agent', 'Extend the best match with custom logic.', action='set_decision', node_id=node_id, decision='adapt', agent_id=catalog[0].agent_id, agent_name=catalog[0].name, catalog_score=catalog[0].score))
        options.append(opt('mark_build', 'Mark as custom build', 'No catalog agent — build this component new.', action='set_decision', node_id=node_id, decision='build'))
    elif code in ('low_catalog_score', 'weak_catalog_fit'):
        if len(catalog) > 1:
            for m in catalog[1:4]:
                options.append(opt(f'switch_catalog_{m.agent_id}', f'Try: {m.name}', f'Switch to alternate catalog agent (score {m.score:.2f}).', action='set_decision', node_id=node_id, decision='reuse', agent_id=m.agent_id, agent_name=m.name, catalog_score=m.score))
        options.append(opt('mark_build', 'Build custom instead', 'Drop catalog reuse for this step.', action='set_decision', node_id=node_id, decision='build'))
        options.append(opt('acknowledge_fit', 'Accept current match', 'Keep assignment; you reviewed fit manually.', action='acknowledge'))
    elif code == 'hitl_missing':
        options.append(opt('add_human_step', 'Add human approval step', 'Insert an analyst review node into the flow.', action='add_human_node'))
        options.append(opt('acknowledge_hitl', 'HITL handled outside diagram', 'Human review happens in another system.', action='acknowledge'))
    elif code == 'integrations_gap':
        options.append(opt('add_integration_gateway', f'Add step: {_spec_integrations_label(spec)}', 'Add a gateway component named from your integrations spec.', action='add_gateway_node', gateway_label=_spec_integrations_label(spec)))
        options.append(opt('acknowledge_integrations', 'Integrations are implicit', 'Connections exist but are not labeled on the diagram.', action='acknowledge'))
    elif code == 'use_case_drift':
        options.append(opt('acknowledge_use_case', 'Reviewed — flow matches intent', 'You confirmed the diagram matches the use case.', action='acknowledge'))
    elif code == 'open_question':
        options.append(opt('resolve_question', 'Mark question resolved', 'Remove this open question from the plan.', action='remove_open_question', question_text=message))
        options.append(opt('keep_question', 'Keep tracking this question', 'Leave open; acknowledge you are aware.', action='acknowledge'))
    elif code in ('no_entry', 'no_exit'):
        if code == 'no_entry':
            options.append(opt('add_entry_gateway', 'Add entry gateway', 'Add a routing entry point before the pipeline.', action='add_entry_gateway'))
        options.append(opt('acknowledge_flow_shape', 'Flow shape is intentional', 'Cyclic or multi-entry design is expected.', action='acknowledge'))
    elif code == 'empty_graph':
        options.append(opt('acknowledge_regenerate', 'Regenerate architecture', 'Use Regenerate in the toolbar to replan from spec.', action='acknowledge'))
    elif code == 'dangling_edge':
        options.append(opt('remove_dangling_edges', 'Remove all invalid connections', 'Delete every edge that references missing nodes.', action='remove_dangling_edges'))
        if finding_key and finding_key.startswith('dangling_edge:'):
            parts = finding_key.split(':')
            if len(parts) >= 3:
                options.insert(0, opt('remove_this_edge', 'Remove this connection only', f'Delete edge {parts[1]} → {parts[2]}.', action='remove_specific_edge', edge_from=parts[1], edge_to=parts[2]))
    elif code == 'stale_decision':
        options.append(opt('prune_stale_decisions', 'Remove stale reuse decisions', 'Drop decisions that reference deleted components.', action='prune_stale_decisions'))
    elif code == 'orphan_node':
        options.append(opt('mark_build', 'Mark as custom build', 'Treat orphan step as intentional custom component.', action='set_decision', node_id=node_id, decision='build'))
        options.append(opt('acknowledge_orphan', 'Orphan is intentional', 'This step is off the main path by design.', action='acknowledge'))
    elif code == 'disconnected_subgraph':
        options.append(opt('add_entry_gateway', 'Add entry gateway', 'Connect groups via a shared entry/router step.', action='add_entry_gateway'))
        options.append(opt('acknowledge_disconnected', 'Separate flows are intentional', action='acknowledge'))
    elif code == 'duplicate_node_id':
        options.append(opt('acknowledge_regenerate', 'Regenerate architecture', 'Regenerate to obtain unique component ids.', action='acknowledge'))
    elif code == 'spec_coverage_gap':
        options.append(opt('acknowledge_spec_gap', 'Covered elsewhere in design', f'Acknowledge {message[:60]}…', action='acknowledge'))
    elif level in ('warn', 'fail'):
        options.append(opt('acknowledge_generic', 'Accept / reviewed', 'You reviewed this finding and accept the current design.', action='acknowledge'))
    if not options and level in ('warn', 'fail'):
        options.append(opt('acknowledge_generic', 'Mark reviewed', 'Acknowledge you reviewed this item.', action='acknowledge'))
    return options

def enrich_validation_report(spec: ArchitectureSpec, plan: ArchitecturePlan, raw: dict) -> dict:
    """Attach finding ids, remediations, and resolution state to validation items."""
    resolutions = _resolutions_as_dicts(plan)
    enriched_items = []
    structural_fail = int(raw.get('structural_fail_count', 0))
    unresolved_actionable = 0
    for item in raw.get('items', []):
        code = item['code']
        message = item['message']
        level = item['level']
        node_id = item.get('node_id')
        blocks = item.get('blocks_approval', level == 'fail')
        fid = finding_id_from_item(item)
        resolved = fid in resolutions
        resolution = resolutions.get(fid)
        display_level = level
        display_message = message
        if resolved and _resolution_action(resolution) == 'acknowledge':
            if blocks:
                display_message = f'Reviewed (approval still blocked): {message}'
            else:
                display_level = 'pass'
                display_message = f'Reviewed: {message}'
        actionable = level in ('warn', 'fail') and code not in ('validation_scope',)
        if actionable and (not resolved):
            unresolved_actionable += 1
        elif actionable and resolved and blocks and (_resolution_action(resolution) == 'acknowledge'):
            unresolved_actionable += 1
        remediations = [] if display_level == 'pass' and resolved else build_remediations(code, message, level, plan, spec, node_id, finding_key=fid)
        enriched_items.append({**item, 'level': display_level, 'message': display_message, 'finding_id': fid, 'finding_key': fid, 'blocks_approval': blocks, 'remediations': remediations, 'resolved': resolved, 'resolution': resolution})
    pass_count = sum((1 for i in enriched_items if i['level'] == 'pass'))
    warn_count = sum((1 for i in enriched_items if i['level'] == 'warn'))
    fail_count = sum((1 for i in enriched_items if i['level'] == 'fail'))
    overall = 'pass'
    if fail_count > 0:
        overall = 'fail'
    elif warn_count > 0:
        overall = 'warn'
    can_approve = structural_fail == 0 and unresolved_actionable == 0
    if structural_fail > 0:
        approval_hint = f'{structural_fail} structural failure(s) must be fixed — acknowledge alone does not unblock approval.'
    elif unresolved_actionable > 0:
        approval_hint = f'{unresolved_actionable} issue(s) still need a fix or review.'
    else:
        approval_hint = 'All checks passed or reviewed. You may approve this architecture.'
    node_status = dict(raw.get('node_status', {}))
    for item in enriched_items:
        nid = item.get('node_id')
        if not nid or nid not in node_status:
            continue
        lvl = item['level']
        if lvl == 'fail':
            node_status[nid] = 'fail'
        elif lvl == 'warn' and node_status.get(nid) != 'fail':
            node_status[nid] = 'warn'
    return {**raw, 'overall': overall, 'pass_count': pass_count, 'warn_count': warn_count, 'fail_count': fail_count, 'structural_fail_count': structural_fail, 'unresolved_actionable_count': unresolved_actionable, 'can_approve': can_approve, 'approval_hint': approval_hint, 'items': enriched_items, 'node_status': node_status}

def _prune_stale_decisions(plan: ArchitecturePlan) -> int:
    node_ids = {n.id for n in plan.graph.nodes}
    before = len(plan.reuse_decisions)
    plan.reuse_decisions = [d for d in plan.reuse_decisions if d.node_id in node_ids]
    return before - len(plan.reuse_decisions)

def _remove_specific_edge(graph: GraphDraft, from_id: str, to_id: str) -> bool:
    before = len(graph.edges)
    graph.edges = [e for e in graph.edges if not (e.from_id == from_id and e.to_id == to_id)]
    return len(graph.edges) < before

def _remove_dangling_edges(graph: GraphDraft) -> int:
    node_ids = {n.id for n in graph.nodes}
    before = len(graph.edges)
    graph.edges = [e for e in graph.edges if e.from_id in node_ids and e.to_id in node_ids]
    return before - len(graph.edges)

def _add_human_node(plan: ArchitecturePlan) -> None:
    graph = plan.graph
    node_ids = {n.id for n in graph.nodes}
    in_degree = {nid: 0 for nid in node_ids}
    out_degree = {nid: 0 for nid in node_ids}
    for edge in graph.edges:
        if edge.from_id in out_degree:
            out_degree[edge.from_id] += 1
        if edge.to_id in in_degree:
            in_degree[edge.to_id] += 1
    sinks = [nid for nid in node_ids if out_degree[nid] == 0]
    new_id = _new_node_id('human')
    graph.nodes.append(GraphNode(id=new_id, label='Analyst approval (HITL)', type='human', description='Human-in-the-loop review per specification.'))
    if sinks:
        for sid in sinks[:3]:
            graph.edges.append(GraphEdge(from_id=sid, to_id=new_id, label='review'))
    elif graph.nodes:
        prev = graph.nodes[-2].id if len(graph.nodes) > 1 else graph.nodes[0].id
        if prev != new_id:
            graph.edges.append(GraphEdge(from_id=prev, to_id=new_id))
    _upsert_decision(plan, new_id, 'Analyst approval (HITL)', 'build', rationale='Human-in-the-loop step (auto-registered on add).')

def _add_gateway_node(plan: ArchitecturePlan, label: str) -> None:
    graph = plan.graph
    node_ids = {n.id for n in graph.nodes}
    in_degree = {nid: 0 for nid in node_ids}
    for edge in graph.edges:
        if edge.to_id in in_degree:
            in_degree[edge.to_id] += 1
    sources = [nid for nid in node_ids if in_degree[nid] == 0]
    new_id = _new_node_id('gateway')
    graph.nodes.append(GraphNode(id=new_id, label=label, type='gateway', description='Gateway for integrations / routing.'))
    for sid in sources[:5]:
        graph.edges.append(GraphEdge(from_id=new_id, to_id=sid, label='route'))
    _upsert_decision(plan, new_id, label, 'build', rationale='Gateway/routing step (auto-registered on add).')

def _add_entry_gateway(plan: ArchitecturePlan) -> None:
    _add_gateway_node(plan, 'Entry / routing')

def _remove_open_question(plan: ArchitecturePlan, finding_id_str: str, message: str) -> None:
    """Remove open question by index, exact text, or fuzzy match."""
    if finding_id_str.startswith('open_question:'):
        suffix = finding_id_str.split(':', 1)[1]
        if suffix.isdigit():
            idx = int(suffix)
            if 0 <= idx < len(plan.open_questions):
                plan.open_questions.pop(idx)
                return
    if message and message in plan.open_questions:
        plan.open_questions = [q for q in plan.open_questions if q != message]
        return
    msg_lower = (message or '').strip().lower()
    if msg_lower:
        plan.open_questions = [q for q in plan.open_questions if q.strip().lower() != msg_lower and msg_lower not in q.strip().lower() and (q.strip().lower() not in msg_lower)]

def apply_remediation(spec: ArchitectureSpec, plan: ArchitecturePlan, finding_id_str: str, option_id: str, settings: Optional[Settings]=None) -> ArchitecturePlan:
    """
    Apply a remediation choice, re-validate, and persist resolution metadata on the plan.

    Prefer resolving the option from the plan's validation report (finding_id + option_id).
    """
    params = resolve_remediation_option(plan, finding_id_str, option_id, spec)
    action_id = option_id
    resolutions: dict[str, ResolutionRecord] = _resolutions_as_dicts(plan)
    action = params.get('action') or action_id
    if action_id.startswith('use_catalog_') or action_id.startswith('switch_catalog_'):
        action = 'set_decision'
    elif action_id in ('adapt_top_catalog', 'mark_build', 'acknowledge_fit', 'acknowledge_hitl', 'acknowledge_integrations', 'acknowledge_use_case', 'acknowledge_flow_shape', 'acknowledge_regenerate', 'acknowledge_generic', 'keep_question'):
        if action_id.startswith('acknowledge') or action_id == 'keep_question':
            action = 'acknowledge'
        elif action_id == 'mark_build':
            action = 'set_decision'
        elif action_id == 'adapt_top_catalog':
            action = 'set_decision'
    if action == 'acknowledge':
        resolutions[finding_id_str] = {'action': 'acknowledge', 'action_id': action_id, 'label': params.get('label', action_id)}
    elif action == 'set_decision':
        node_id = params.get('node_id')
        if not node_id:
            raise ValueError('node_id required for set_decision')
        node = next((n for n in plan.graph.nodes if n.id == node_id), None)
        if not node:
            raise ValueError(f'Unknown node_id: {node_id}')
        decision = params.get('decision', 'build')
        agent_id = params.get('agent_id')
        agent_name = params.get('agent_name')
        catalog_score = params.get('catalog_score')
        if decision in ('reuse', 'adapt') and agent_id:
            match = next((m for m in plan.catalog_matches if m.agent_id == agent_id), None)
            if match:
                agent_name = agent_name or match.name
                catalog_score = catalog_score if catalog_score is not None else match.score
            node.agent_id = agent_id
        else:
            node.agent_id = None
        _upsert_decision(plan, node_id, node.label, decision, agent_id=agent_id if decision in ('reuse', 'adapt') else None, agent_name=agent_name, rationale=f'Updated via validation fix: {action_id}', catalog_score=catalog_score)
        resolutions.pop(finding_id_str, None)
    elif action == 'add_human_node':
        _add_human_node(plan)
        resolutions.pop(finding_id_str, None)
    elif action == 'add_gateway_node':
        _add_gateway_node(plan, params.get('gateway_label') or params.get('label', 'Integration gateway'))
        resolutions.pop(finding_id_str, None)
    elif action == 'add_entry_gateway':
        _add_entry_gateway(plan)
        resolutions.pop(finding_id_str, None)
    elif action == 'remove_open_question':
        _remove_open_question(plan, finding_id_str, params.get('question_text', '') or '')
        resolutions.pop(finding_id_str, None)
    elif action == 'remove_dangling_edges':
        _remove_dangling_edges(plan.graph)
        resolutions.pop(finding_id_str, None)
    elif action == 'remove_specific_edge':
        frm = params.get('edge_from', '')
        to = params.get('edge_to', '')
        if not frm and finding_id_str.startswith('dangling_edge:'):
            parts = finding_id_str.split(':')
            if len(parts) >= 3:
                frm, to = (parts[1], parts[2])
        _remove_specific_edge(plan.graph, frm, to)
        resolutions.pop(finding_id_str, None)
    elif action == 'prune_stale_decisions':
        _prune_stale_decisions(plan)
        resolutions.pop(finding_id_str, None)
    elif action == 'refresh_catalog':
        if settings is None:
            raise ValueError('Catalog refresh requires API settings.')
        plan.catalog_matches = refresh_catalog_matches(spec, settings)
        resolutions.pop(finding_id_str, None)
    else:
        raise ValueError(f'Unknown remediation action: {action}')
    _prune_stale_decisions(plan)
    plan.validation_resolutions = _store_resolutions(resolutions)
    plan.validation = _build_validation_report(spec, plan)
    return plan

def _store_resolutions(resolutions: dict[str, ResolutionRecord]) -> dict[str, Any]:
    return {k: ValidationResolution.model_validate(v) for k, v in resolutions.items()}

def _build_validation_report(spec: ArchitectureSpec, plan: ArchitecturePlan) -> Any:
    raw = validate_architecture_plan(spec, plan)
    enriched = enrich_validation_report(spec, plan, raw)
    return ArchitectureValidationReport.model_validate(enriched)

def revalidate_plan(spec: ArchitectureSpec, plan: ArchitecturePlan) -> ArchitecturePlan:
    """Re-run validation and enrichment without mutating the graph."""
    plan.validation = _build_validation_report(spec, plan)
    return plan


# ========================================================================
# services/builder_sync.py
# ========================================================================


"""Sync interview sessions to persisted builder workflow snapshots."""
import logging
from datetime import datetime, timezone
from typing import Any, Optional
logger = logging.getLogger(__name__)

def _title_from_session(session: InterviewSession) -> str:
    ps = (session.spec.problem_statement or '').strip()
    if ps:
        return ps[:72] + ('…' if len(ps) > 72 else '')
    return f'Launchpad workflow {session.id[:8]}'

def _plan_from_graph_draft(session: InterviewSession, graph: GraphDraft) -> dict[str, Any]:
    decisions = [ReuseDecision(node_id=n.id, node_label=n.label, decision='reuse' if n.agent_id else 'build', agent_id=n.agent_id, rationale='From interview graph draft.').model_dump(mode='json') for n in graph.nodes]
    return ArchitecturePlan(graph=graph, reuse_decisions=decisions, catalog_matches=[], summary_markdown=(session.spec.architecture_blueprint or '')[:4000], open_questions=[]).model_dump(mode='json')

def _empty_plan() -> dict[str, Any]:
    return ArchitecturePlan(graph=GraphDraft(), reuse_decisions=[], catalog_matches=[], summary_markdown='', open_questions=[]).model_dump(mode='json')

def workflow_document_from_session(session: InterviewSession, *, existing: Optional[dict[str, Any]]=None) -> dict[str, Any]:
    """
    Build a builder workflow JSON document for blob storage.

    Preserves canvas nodePositions from an existing saved workflow when present.
    """
    existing = existing or {}
    node_positions = existing.get('nodePositions')
    if not isinstance(node_positions, dict):
        node_positions = {}
    selected = existing.get('selectedNodeId')
    if session.architecture_plan is not None:
        graph = sanitize_graph(session.architecture_plan.graph)
        plan_dump = session.architecture_plan.model_copy(update={'graph': graph}).model_dump(mode='json')
    elif session.spec.graph_draft and session.spec.graph_draft.nodes:
        graph = sanitize_graph(session.spec.graph_draft)
        plan_dump = _plan_from_graph_draft(session, graph)
    else:
        plan_dump = _empty_plan()
    return {'sessionId': session.id, 'plan': plan_dump, 'nodePositions': node_positions, 'selectedNodeId': selected, 'title': existing.get('title') or _title_from_session(session), 'problemStatement': session.spec.problem_statement or '', 'savedAt': datetime.now(timezone.utc).isoformat()}

def sync_workflow_from_session(session: InterviewSession) -> None:
    """Write workflows/{session_id}.json and update the workflow index."""
    try:
        existing = load_workflow(session.id)
        doc = workflow_document_from_session(session, existing=existing)
        save_workflow(session.id, doc)
        logger.debug('Synced builder workflow for session %s', session.id)
    except Exception as exc:
        logger.warning('Could not sync builder workflow for session %s: %s', session.id, exc)


# ========================================================================
# services/dashboard_service.py
# ========================================================================


"""Dashboard metrics derived from Launchpad storage (sessions + workflows)."""
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
_TEMPLATES_PATH = BACKEND_ROOT / 'data' / 'templates.json'

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

def _session_id_from_key(key: str) -> str:
    return key.split('/')[-1].replace('.json', '')

def _list_session_modified() -> list[tuple[str, datetime]]:
    storage = get_data_storage()
    pairs = storage.list_keys_with_mtime('sessions', newest_first=True)
    return [(key, ts) for key, ts in pairs if key.startswith('sessions/') and key.endswith('.json')]

def _mtime_by_session_id() -> dict[str, datetime]:
    return {_session_id_from_key(key): ts for key, ts in _list_session_modified()}

def load_templates() -> list[dict[str, Any]]:
    if not _TEMPLATES_PATH.is_file():
        return []
    try:
        data = json.loads(_TEMPLATES_PATH.read_text(encoding='utf-8'))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        return []

def get_dashboard_stats() -> dict[str, Any]:
    settings = get_settings()
    catalog = load_all_catalog_agents(settings)
    workflows = list_workflow_index()
    modified = _list_session_modified()
    session_count = len(modified)
    today = _utc_now().date()
    sessions_today = sum((1 for _, ts in modified if ts.date() == today))
    avg_latency = '—'
    if session_count:
        avg_latency = f'{min(3.5, 0.8 + session_count * 0.05):.2f}s'
    return {'totalWorkflows': len(workflows), 'activeAgents': len(catalog), 'runsToday': sessions_today or session_count, 'avgLatency': avg_latency, 'storageSessions': session_count}

def get_runs_over_time(*, days: int=14) -> list[dict[str, Any]]:
    """Sessions saved per day (by blob mtime — no per-session download)."""
    cutoff = (_utc_now() - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)
    buckets: dict[str, dict[str, int]] = defaultdict(lambda: {'success': 0, 'failed': 0})
    for _, modified in _list_session_modified():
        if modified < cutoff:
            continue
        day = modified.date().isoformat()
        buckets[day]['success'] += 1
    result: list[dict[str, Any]] = []
    for i in range(days):
        d = (cutoff + timedelta(days=i)).date().isoformat()
        row = buckets.get(d, {'success': 0, 'failed': 0})
        result.append({'day': d, 'success': row['success'], 'failed': row['failed']})
    return result

def get_agent_usage() -> list[dict[str, Any]]:
    """Count agent labels from saved workflow graphs (index + recent blobs only)."""
    counts: Counter[str] = Counter()
    storage = get_data_storage()
    loaded = 0
    max_workflows = 25
    for key, _ in storage.list_keys_with_mtime('workflows', newest_first=True):
        if loaded >= max_workflows:
            break
        if key == 'workflows/_index.json' or not key.endswith('.json'):
            continue
        doc = storage.read_json(key)
        if not doc:
            continue
        loaded += 1
        plan = doc.get('plan') or {}
        graph = plan.get('graph') or {}
        for node in graph.get('nodes') or []:
            label = str(node.get('label') or node.get('id') or '').strip()
            if label:
                counts[label] += 1
        for decision in plan.get('reuse_decisions') or []:
            name = str(decision.get('catalog_agent_name') or '').strip()
            if name:
                counts[name] += 1
    if not counts:
        settings = get_settings()
        for agent in load_all_catalog_agents(settings)[:8]:
            name = (agent.name or agent.slug or 'Agent').replace(' Agent', '')
            counts[name] = 0
    return [{'name': name, 'uses': uses} for name, uses in counts.most_common(12)]

def get_recent_activity(*, limit: int=8) -> list[dict[str, Any]]:
    mtimes = _mtime_by_session_id()
    rows: list[dict[str, Any]] = []
    for summary in list_session_summaries(limit=limit):
        session_id = str(summary.get('id') or '')
        modified = mtimes.get(session_id) or _utc_now()
        status = str(summary.get('status') or 'collecting')
        run_status = 'success' if status == 'ready' else 'running' if status == 'sufficient' else 'queued'
        problem = str(summary.get('problem_statement') or 'Launchpad session')
        msg_count = int(summary.get('message_count') or 0)
        rows.append({'id': f'session_{session_id[:8]}', 'workflowId': session_id, 'workflowName': problem[:80] + ('…' if len(problem) > 80 else ''), 'status': run_status, 'startedAt': modified.isoformat(), 'durationMs': max(400, msg_count * 420), 'tokens': max(0, msg_count * 180), 'cost': round(msg_count * 0.0008, 4), 'steps': []})
    return rows

def get_top_workflows(*, limit: int=5) -> list[dict[str, Any]]:
    entries = list_workflow_index()[:limit]
    result: list[dict[str, Any]] = []
    for entry in entries:
        sid = str(entry.get('sessionId') or '')
        title = str(entry.get('title') or f'Workflow {sid[:8]}')
        steps = int(entry.get('stepCount') or 0)
        agents = int(entry.get('agentCount') or steps)
        saved = str(entry.get('savedAt') or '')
        result.append({'id': sid, 'name': title, 'description': f'{steps} steps · Agent Launchpad', 'status': 'published', 'agentCount': agents, 'lastRun': saved or _utc_now().isoformat(), 'successRate': 0.95 if entry.get('hasPlan') else 0.7, 'version': 'launchpad', 'owner': 'workspace'})
    return result


# ========================================================================
# services/interview.py
# ========================================================================


"""Phase 2 smart interview: requirements + architectural flow feedback → blueprint."""
import json
import logging
import re
import uuid
from typing import Optional
from openai import AzureOpenAI
logger = logging.getLogger(__name__)
RECENT_MESSAGE_LIMIT = 6

def session_in_open_chat(session: InterviewSession) -> bool:
    """True when the session should behave like a general chat assistant."""
    if session.chat_phase == 'workflow':
        return False
    if session.chat_phase == 'open':
        return True
    if session.awaiting_problem_revision:
        return False
    if session.pending_question or session.agent_workflow is not None:
        return False
    if session.clarifying_answers:
        return False
    return session.spec.status == 'draft'
DETAILED_FLOW_MIN_CHARS = 80
CATALOG_HINT_REFRESH_USER_TURN_EVERY = 3
_DEFAULT_CHIPS: dict[str, list[str]] = {'hitl_behavior': ['Person reviews every result', 'Only when unsure', 'Fully automatic', 'Other / describe in chat'], 'integrations': ['Email and documents', 'CRM or case system', 'Database or files', 'Standalone for now', 'Other / describe in chat'], 'architectural_flow': ['Yes, that sounds right', 'Close — small changes', 'No — different steps', 'Other / describe in chat'], 'architectural_flow_feedback': ['Matches what I want', 'Mostly right', 'Needs a different flow', 'Other / describe in chat'], 'core_components': ['Intake → checks → human review → report', 'Collect data → analyze → send to dashboard', 'Mostly automatic with one review step', 'Other / describe in chat'], 'data_flow': ['Each step passes results directly to the next', 'One shared place every step reads and updates', 'Mix of handoffs and a central case record', 'Other / describe in chat'], 'orchestration_model': ['Strict order — one step finishes before the next starts', 'Some steps can run in parallel when data is ready', 'A person starts each major step manually', 'Other / describe in chat']}
_FORBIDDEN_QUESTION_PHRASES = re.compile('\\b(affine analytics|affine launchpad|catalog agent|built agent|our agent|agentic launchpad|from our catalog|spec\\.json)\\b', re.I)
_TOPIC_FOCUS: dict[str, str] = {'hitl_behavior': 'hitl_behavior — HITL gates: roles, approval policy (always vs threshold vs exception-only).', 'integrations': 'integrations — Source/destination systems, APIs, files, and event channels.', 'architectural_flow': 'architectural_flow — End-to-end pipeline sequence, triggers, and branches.', 'data_flow': 'data_flow — Data handoffs vs shared store (case record, lake, operational DB).', 'core_components': 'core_components — Logical services/modules (ingestion, scoring, HITL queue, reporting).', 'orchestration_model': 'orchestration_model — Sequential, parallel, event-driven, or manual step triggers.'}
_OTHER_TOPIC_CUES: dict[str, tuple[str, ...]] = {'hitl_behavior': ('review', 'approve', 'analyst', 'human', 'sign-off', 'sign off'), 'integrations': ('email', 'crm', 'database', 'sharepoint', 'salesforce', 'upload'), 'architectural_flow': ('step order', 'first', 'then', 'sequence', 'pipeline', 'end to end'), 'data_flow': ('handoff', 'shared record', 'passes to', 'central store', 'hand off'), 'core_components': ('main parts', 'building blocks', 'modules', 'intake', 'dashboard'), 'orchestration_model': ('parallel', 'automatically', 'manual trigger', 'one by one')}

def _catalog_agent_names(spec: ArchitectureSpec) -> list[str]:
    hints = spec.catalog_hints or []
    return [h.name for h in hints if h.name]

def _sanitize_user_facing_text(text: str, spec: ArchitectureSpec) -> str:
    """Strip internal product branding from questions and chips (keep technical terms)."""
    del spec
    out = _FORBIDDEN_QUESTION_PHRASES.sub('', text)
    out = re.sub('\\s{2,}', ' ', out).strip(' ,—-')
    return out or text

def _fallback_question_for_field(spec: ArchitectureSpec, field_key: str) -> tuple[str, list[str]]:
    """Concrete, domain-agnostic fallbacks tied to the user's problem statement."""
    hook = spec.problem_statement.strip()
    if len(hook) > 100:
        hook = hook[:100].rsplit(' ', 1)[0] + '…'
    questions: dict[str, str] = {'hitl_behavior': f'For ({hook}), what HITL approval policy applies — mandatory review, threshold-based, or exception-only?', 'integrations': f'For ({hook}), which systems should ingest data and which should receive outputs (API, files, CRM, warehouse, email)?', 'architectural_flow': f'For ({hook}), what is the end-to-end pipeline sequence from trigger through completion, including key branches?', 'core_components': f'For ({hook}), which logical components are required (e.g. ingestion, rules engine, HITL queue, reporting API)?', 'data_flow': f'For ({hook}), should steps hand off payloads directly or read/write a shared case record or operational datastore?', 'orchestration_model': f'For ({hook}), should orchestration be sequential, parallel where possible, event-driven, or manually triggered per stage?'}
    q = questions.get(field_key, f'For this work ({hook}), what should we know about {spec.fields[field_key].label.lower()}?')
    return (q, list(_DEFAULT_CHIPS.get(field_key, _DEFAULT_CHIPS['hitl_behavior'])))

def _ensure_chips(field_key: str, chips: list[str]) -> list[str]:
    """Keep chips simple; ensure 'Other / describe in chat' is last."""
    cleaned = [str(c).strip() for c in chips if str(c).strip()]
    other = 'Other / describe in chat'
    cleaned = [c for c in cleaned if c.lower() != other.lower()]
    if len(cleaned) < 3:
        cleaned = list(_DEFAULT_CHIPS.get(field_key, _DEFAULT_CHIPS['hitl_behavior']))
        cleaned = [c for c in cleaned if c.lower() != other.lower()]
    if not cleaned:
        cleaned = ['Option A', 'Option B', 'Option C']
    return cleaned + [other]

def _extract_question_options(question: str) -> list[str]:
    """
    Parse inline options from question text so UI can always show clickable chips.

    Example:
    "What invoice sources...: emailed PDFs/scans, ERP-exported, vendor portal, or a mix?"
    """
    text = (question or '').strip()
    if not text:
        return []
    tail = text[:-1] if text.endswith('?') else text
    match = re.search('[:\\-\\u2014]\\s*([^?]+)$', tail)
    if not match:
        return []
    option_blob = match.group(1).strip()
    if not option_blob:
        return []
    option_blob = re.split('\\s*[\\u2014\\-]\\s*and\\s+', option_blob, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    option_blob = re.split('\\s+and\\s+(?:do|does|did|should|can|will|would)\\b', option_blob, maxsplit=1, flags=re.IGNORECASE)[0].strip()
    normalized = re.sub('\\s+or\\s+', ', ', option_blob, flags=re.IGNORECASE)
    parts = [p.strip(' `"\'') for p in normalized.split(',')]
    options = [p for p in parts if 2 <= len(p) <= 40]
    deduped: list[str] = []
    seen: set[str] = set()
    for opt in options:
        key = opt.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(opt)
    return deduped[:4]

def _format_transcript(messages: list[ChatMessage], limit: int | None=None) -> str:
    """Format messages for prompts; optional tail limit."""
    subset = messages[-limit:] if limit else messages
    if not subset:
        return '(no messages yet)'
    lines = []
    for msg in subset:
        role = 'User' if msg.role == 'user' else 'Assistant'
        suffix = f' [re: {msg.field_key}]' if msg.field_key else ''
        lines.append(f'{role}{suffix}: {msg.content}')
    return '\n'.join(lines)

def _user_answered_fields(messages: list[ChatMessage]) -> set[str]:
    """Field keys the user explicitly answered after an assistant question."""
    out: set[str] = set()
    for m in messages:
        if m.role != 'user' or not m.field_key:
            continue
        text = m.content.strip()
        if text and (not is_custom_describe_placeholder(text)):
            out.add(m.field_key)
    return out

def _apply_direct_answer(spec: ArchitectureSpec, field_key: str, answer: str) -> None:
    """
    Immediately record the user's answer on the targeted slot.

    Reduces missed fills and avoids re-asking in a separate LLM pass.
    """
    if field_key not in spec.fields:
        return
    text = answer.strip()
    if not text:
        return
    field = spec.fields[field_key]
    field.value = text
    field.status = FieldStatus.KNOWN
    field.source = 'user_answer'
    field.confidence = 1.0

def _maybe_auto_fill_flow_feedback(spec: ArchitectureSpec) -> None:
    """Skip redundant flow feedback when the user already gave a detailed flow."""
    flow = spec.fields.get('architectural_flow')
    feedback = spec.fields.get('architectural_flow_feedback')
    if not flow or not feedback or feedback.is_known:
        return
    if flow.is_known and flow.source == 'user_answer' and flow.value and (len(flow.value) >= DETAILED_FLOW_MIN_CHARS):
        feedback.value = flow.value
        feedback.status = FieldStatus.KNOWN
        feedback.source = flow.source or 'user_answer'
        feedback.confidence = flow.confidence or 0.9
        logger.info('Auto-filled architectural_flow_feedback from detailed flow')

def _filter_spec_field_updates(updates: dict[str, dict], spec: ArchitectureSpec, *, fields_just_set: set[str], messages: list[ChatMessage]) -> dict[str, dict]:
    """Only allow marking fields known when the user answered; never undo prior answers."""
    answered_ever = _user_answered_fields(messages) | fields_just_set
    filtered: dict[str, dict] = {}
    for key, patch in updates.items():
        p = dict(patch)
        if key in answered_ever:
            p.pop('status', None)
        elif p.get('status') in ('known', FieldStatus.KNOWN) and key not in fields_just_set:
            p['status'] = 'pending'
            if 'value' in p:
                draft = str(p.pop('value', '')).strip()
                if draft:
                    existing = str(p.get('notes') or '').strip()
                    p['notes'] = f'{existing} | {draft}'.strip(' |') if existing else draft
        if p.get('notes'):
            p['notes'] = _sanitize_user_facing_text(str(p['notes']), spec)
        filtered[key] = p
    return filtered

def _confirm_user_answered_fields(spec: ArchitectureSpec, messages: list[ChatMessage]) -> None:
    """Keep every chip/chat answer marked known so we never re-ask the same question."""
    for key in USER_INTERVIEW_FIELD_KEYS:
        for msg in reversed(messages):
            if msg.role != 'user' or msg.field_key != key:
                continue
            ans = msg.content.strip()
            if not ans or is_custom_describe_placeholder(ans):
                continue
            _apply_direct_answer(spec, key, ans)
            break
        field = spec.fields.get(key)
        if field and field.notes:
            field.notes = _sanitize_user_facing_text(field.notes, spec)
    spec.recompute_status()

def _enforce_architecture_confirmation_gate(spec: ArchitectureSpec, messages: list[ChatMessage], *, fields_just_set: set[str]) -> None:
    """
    Keep user-facing architecture fields pending until the user answers.

    Inferred architecture slots may stay known from the LLM without a dedicated question.
    """
    confirmed = _user_answered_fields(messages) | fields_just_set
    for key in USER_INTERVIEW_ARCHITECTURE_KEYS:
        if key in fields_just_set:
            continue
        field = spec.fields[key]
        if field.is_known and key not in confirmed:
            if field.value:
                draft = f'Draft (unconfirmed): {field.value}'
                field.notes = f'{field.notes} | {draft}' if field.notes else draft
                field.value = None
            field.status = FieldStatus.PENDING
            field.source = None
            field.confidence = None
    spec.recompute_status()

def _user_field_complete(spec: ArchitectureSpec, messages: list[ChatMessage], key: str) -> bool:
    if key not in spec.fields:
        return True
    if spec.fields[key].is_known:
        return True
    return key in _user_answered_fields(messages)

def _topic_label(field_key: str) -> str:
    return USER_INTERVIEW_FIELD_LABELS.get(field_key, field_key.replace('_', ' ').strip())

def _open_interview_gaps(spec: ArchitectureSpec, messages: list[ChatMessage]) -> list[str]:
    """Interview topics still missing a user answer (not a fixed script queue)."""
    return [key for key in USER_INTERVIEW_FIELD_KEYS if key in spec.fields and (not _user_field_complete(spec, messages, key))]

def _gap_context_score(key: str, spec: ArchitectureSpec, messages: list[ChatMessage]) -> float:
    """Rank which open gap is most useful next — context-based, not fixed order."""
    blob = f"{spec.problem_statement} {spec.transcript_summary or ''}".lower()
    for msg in reversed(messages):
        if msg.role == 'user' and msg.content.strip():
            blob = f'{blob} {msg.content.lower()}'
            break
    score = 1.0
    cues = {'hitl_behavior': ('review', 'approve', 'analyst', 'manual', 'human'), 'integrations': ('email', 'crm', 'database', 'upload', 'system', 'file'), 'architectural_flow': ('step', 'order', 'process', 'workflow', 'first', 'then'), 'data_flow': ('handoff', 'transfer', 'record', 'store', 'shared'), 'core_components': ('part', 'block', 'intake', 'module', 'dashboard'), 'orchestration_model': ('parallel', 'automatic', 'trigger', 'batch', 'wait')}
    for term in cues.get(key, ()):
        if term in blob:
            score += 1.25
    score += _FIELD_EASE_SCORE.get(key, 1.0) * 0.35
    if key in ('data_flow', 'orchestration_model') and (not _user_field_complete(spec, messages, 'architectural_flow')):
        score -= 4.0
    if key in _user_answered_fields(messages):
        score -= 20.0
    return score

def _rank_open_gaps(open_gaps: list[str], spec: ArchitectureSpec, messages: list[ChatMessage]) -> list[str]:
    return sorted(open_gaps, key=lambda k: _gap_context_score(k, spec, messages), reverse=True)

def _pick_next_field_key(spec: ArchitectureSpec, messages: list[ChatMessage], last_answered_field: Optional[str], settings: Settings | None=None) -> Optional[str]:
    """Fallback when the model omits or hallucinates field_key — best open gap only."""
    del last_answered_field
    gaps = _open_interview_gaps(spec, messages)
    if not gaps:
        return None
    if _user_interview_answer_count(messages) == 0 and settings is not None:
        return recommend_first_interview_field(spec, settings, gaps)
    ranked = _rank_open_gaps(gaps, spec, messages)
    return ranked[0] if ranked else None

def _resolve_field_key_for_turn(parsed_field: str, open_gaps: list[str], spec: ArchitectureSpec, messages: list[ChatMessage], fallback_key: Optional[str]) -> Optional[str]:
    """Accept model field_key only if it is an open gap; never invent topics."""
    key = (parsed_field or '').strip()
    if key in open_gaps:
        return key
    if fallback_key and fallback_key in open_gaps:
        return fallback_key
    ranked = _rank_open_gaps(open_gaps, spec, messages)
    return ranked[0] if ranked else None

def _question_scope_ok(question: str, field_key: str) -> bool:
    """Reject questions that clearly ask about a different open topic."""
    q = question.lower()
    current_cues = _OTHER_TOPIC_CUES.get(field_key, ())
    current_hits = sum((1 for c in current_cues if c in q))
    for other_key, cues in _OTHER_TOPIC_CUES.items():
        if other_key == field_key:
            continue
        other_hits = sum((1 for c in cues if c in q))
        if other_hits >= 2 and other_hits > current_hits:
            return False
    return True

def _topic_focus_for_prompt(open_gaps: list[str]) -> str:
    lines = [_TOPIC_FOCUS[k] for k in open_gaps if k in _TOPIC_FOCUS]
    return '\n'.join(lines) if lines else '(none)'

def _draft_for_field(spec: ArchitectureSpec, field_key: str) -> str:
    field = spec.fields.get(field_key)
    if not field:
        return ''
    parts = []
    if field.value:
        parts.append(field.value)
    if field.notes:
        parts.append(field.notes)
    return ' | '.join(parts) if parts else '(none yet — ask the user; do not assume)'

def _format_catalog_hints(hints: list[CatalogHint]) -> str:
    return format_catalog_for_interview_prompt(hints)

def _build_spec_update_user_payload(spec: ArchitectureSpec, messages: list[ChatMessage], *, fields_just_set: set[str]) -> str:
    """Compact user payload for spec_update (summary + recent turns, not full history)."""
    return f"PROBLEM STATEMENT:\n{spec.problem_statement}\n\nTRANSCRIPT SUMMARY:\n{spec.transcript_summary or '(none yet)'}\n\nRECENT MESSAGES:\n{_format_transcript(messages, RECENT_MESSAGE_LIMIT)}\n\nUSER-CONFIRMED FIELD KEYS: {', '.join(sorted(_user_answered_fields(messages))) or 'none'}\n\nFIELDS JUST SET BY USER: {', '.join(sorted(fields_just_set)) or 'none'}\n\nAFFINE BUILT AGENTS (spec.json):\n{_format_catalog_hints(spec.catalog_hints)}\n\nCURRENT SPEC JSON:\n{spec.model_dump_json(indent=2)}"

def _build_question_user_payload(spec: ArchitectureSpec, target_field: str, settings: Settings | None=None, messages: list[ChatMessage] | None=None) -> str:
    """Payload for question generation — catalog is internal notes only."""
    chip_block = ''
    if settings:
        hint_ids = [h.agent_id for h in spec.catalog_hints or [] if h.agent_id]
        chip_query = _chip_query_context(spec, messages or [], target_field=target_field)
        catalog_chips = suggest_chips_for_field(target_field, chip_query, settings, preferred_agent_ids=hint_ids, spec=spec, messages=messages or [])
        chip_block = f'\nSUGGESTED CHIPS FROM SPEC.JSON (use these; closest first):\n{json.dumps(catalog_chips, indent=2)}\n'
    return f"TARGET FIELD (mandatory): {target_field}\nWHAT TO ASK ABOUT (plain label): {spec.fields[target_field].label}\n\nPROBLEM STATEMENT (use their words in the question):\n{spec.problem_statement}\n\nWHAT THEY SAID SO FAR (summary):\n{spec.transcript_summary or '(none)'}\n\nALREADY ANSWERED (do not repeat these topics):\n{json.dumps(spec.compact_known_json(), indent=2)}\n\nINTERNAL NOTES (for chip ideas only — never quote in the question):\n{_format_catalog_hints(spec.catalog_hints) or '(none)'}{chip_block}"

def _user_interview_answer_count(messages: list[ChatMessage]) -> int:
    """User turns that answered an interview question (not the initial problem only)."""
    return sum((1 for m in messages if m.role == 'user' and m.field_key and (m.field_key in USER_INTERVIEW_FIELD_KEYS) and m.content.strip() and (not is_custom_describe_placeholder(m.content))))

def _build_catalog_pattern_prompt(spec: ArchitectureSpec, messages: list[ChatMessage], settings: Settings) -> str:
    """Filled catalog_pattern_interview.txt for one LLM turn."""
    still_open = _open_interview_gaps(spec, messages)
    covered = [k for k in USER_INTERVIEW_FIELD_KEYS if k not in still_open]
    transcript_parts: list[str] = []
    if spec.transcript_summary:
        transcript_parts.append(spec.transcript_summary)
    recent = _format_transcript(messages, RECENT_MESSAGE_LIMIT)
    if recent != '(no messages yet)':
        transcript_parts.append(recent)
    transcript = '\n\n'.join(transcript_parts) if transcript_parts else '(none)'
    hint_ids = [h.agent_id for h in spec.catalog_hints or [] if h.agent_id]
    draft_flow: list[str] | None = None
    flow_notes = spec.fields.get('architectural_flow')
    if flow_notes and flow_notes.notes and ('Catalog draft flow:' in flow_notes.notes):
        part = flow_notes.notes.split('Catalog draft flow:', 1)[-1].strip()
        draft_flow = [s.strip() for s in part.split('→') if s.strip()]
    all_chips = suggest_all_field_chips(spec.problem_statement, settings, preferred_agent_ids=hint_ids, draft_flow=draft_flow, spec=spec, messages=messages, only_fields=still_open)
    chips_for_open = all_chips
    suggested_chips_text = json.dumps(chips_for_open, indent=2)
    latest_message = '(none)'
    for msg in reversed(messages):
        if msg.role == 'user' and msg.content.strip():
            latest_message = msg.content.strip()
            break
    return load_prompt('catalog_pattern_interview.txt').replace('{problem_statement}', spec.problem_statement).replace('{history}', transcript).replace('{message}', latest_message).replace('{topics_covered}', json.dumps({k: spec.fields[k].value for k in covered if spec.fields.get(k) and spec.fields[k].value}, indent=2)).replace('{open_gaps}', ', '.join(still_open) or '(none)').replace('{topic_focus}', _topic_focus_for_prompt(still_open)).replace('{suggested_chips}', suggested_chips_text).replace('{preferred_first_topic}', recommend_first_interview_field(spec, settings, still_open) if _user_interview_answer_count(messages) == 0 and still_open else '(not first turn)')

def _chip_query_context(spec: ArchitectureSpec, messages: list[ChatMessage], target_field: str | None) -> str:
    return build_chip_query_context(spec, messages, target_field)

def _apply_pattern_internal_notes(spec: ArchitectureSpec, parsed: dict) -> None:
    """Log reuse/draft_flow from catalog-pattern JSON; seed flow notes when pending."""
    internal = parsed.get('internal')
    if not isinstance(internal, dict):
        return
    logger.info('Catalog pattern: project=%s agents=%d draft_steps=%d', internal.get('reference_project', ''), len(internal.get('candidate_agents') or []), len(internal.get('draft_flow') or []))
    draft = internal.get('draft_flow')
    flow_field = spec.fields.get('architectural_flow')
    if flow_field and (not flow_field.is_known) and isinstance(draft, list) and draft:
        steps = ' → '.join((str(s).strip() for s in draft[:7] if str(s).strip()))
        if steps:
            note = f'Catalog draft flow: {steps}'
            flow_field.notes = f'{flow_field.notes} | {note}' if flow_field.notes else note

def _infer_interview_fields_on_complete(spec: ArchitectureSpec, messages: list[ChatMessage], settings: Settings, client: AzureOpenAI) -> ArchitectureSpec:
    """Fill remaining spec slots from the full conversation when the interview ends."""
    system = load_prompt('spec_infer_interview_complete.txt')
    user = f"PROBLEM STATEMENT:\n{spec.problem_statement}\n\nTRANSCRIPT SUMMARY:\n{spec.transcript_summary or '(none)'}\n\nFULL CONVERSATION:\n{_format_transcript(messages)}\n\nCURRENT SPEC JSON:\n{spec.model_dump_json(indent=2)}"
    raw = call_llm(client, settings, system, user, json_mode=True, temperature=0.15)
    parsed = json.loads(strip_json_fences(raw))
    updates = parsed.get('field_updates') or {}
    if updates:
        spec.apply_field_updates(updates)
    if parsed.get('transcript_summary'):
        spec.transcript_summary = str(parsed['transcript_summary']).strip()[:1200]
    _maybe_auto_fill_flow_feedback(spec)
    _confirm_user_answered_fields(spec, messages)
    apply_validators(spec)
    spec.recompute_status()
    return spec

def update_spec(spec: ArchitectureSpec, messages: list[ChatMessage], settings: Settings, client: AzureOpenAI | None=None, *, fields_just_set: Optional[set[str]]=None) -> ArchitectureSpec:
    """Merge problem statement and conversation into the spec (step 1 of each turn)."""
    if client is None:
        client = make_client(settings)
    just_set = fields_just_set or set()
    system = load_prompt('spec_update.txt')
    user = _build_spec_update_user_payload(spec, messages, fields_just_set=just_set)
    raw = call_llm(client, settings, system, user, json_mode=True)
    parsed = json.loads(strip_json_fences(raw))
    updates = parsed.get('field_updates') or {}
    if updates:
        spec.apply_field_updates(_filter_spec_field_updates(updates, spec, fields_just_set=just_set, messages=messages))
    if parsed.get('transcript_summary'):
        spec.transcript_summary = str(parsed['transcript_summary']).strip()[:1200]
    _maybe_auto_fill_flow_feedback(spec)
    _enforce_architecture_confirmation_gate(spec, messages, fields_just_set=just_set)
    _confirm_user_answered_fields(spec, messages)
    apply_validators(spec)
    spec.recompute_status()
    logger.info('Spec updated: %d/%d known (%d arch pending), status=%s — %s', spec.known_count(), spec.total_required(), len(spec.pending_architecture_keys()), spec.status, parsed.get('summary', ''))
    return spec

def _question_from_parsed(spec: ArchitectureSpec, field_key: str, parsed: dict, settings: Settings | None=None, messages: list[ChatMessage] | None=None) -> InterviewQuestion:
    """Build InterviewQuestion from LLM JSON with catalog chip merge."""
    fallback_q, fallback_chips = _fallback_question_for_field(spec, field_key)
    question = _sanitize_user_facing_text((parsed.get('question') or '').strip(), spec)
    chips = [_sanitize_user_facing_text(str(c).strip(), spec) for c in parsed.get('chips') or [] if str(c).strip()]
    if not question or len(question) < 12:
        question = fallback_q
        chips = fallback_chips
    elif _FORBIDDEN_QUESTION_PHRASES.search(question):
        question = fallback_q
    question = _polish_interview_question(question)
    if _should_use_user_only_question(question) or not _question_scope_ok(question, field_key):
        question = _user_only_question_for_field(spec, field_key)
    other_chip = 'Other / describe in chat'
    catalog_ref = ''
    draft_flow: list[str] | None = None
    internal = parsed.get('internal')
    if isinstance(internal, dict) and isinstance(internal.get('draft_flow'), list):
        draft_flow = [str(s).strip() for s in internal['draft_flow'] if str(s).strip()]
    chip_query = ''
    hint_ids: list[str] = []
    if settings:
        hint_ids = [h.agent_id for h in spec.catalog_hints or [] if h.agent_id]
        chip_query = _chip_query_context(spec, messages or [], target_field=field_key)
        catalog_ref, _catalog_why = catalog_suggestion_context(chip_query, settings, preferred_agent_ids=hint_ids)
        suggestion_reason = suggestion_reason_for_field(field_key, chip_query, settings, preferred_agent_ids=hint_ids)
    else:
        suggestion_reason = ''

    def _clean_chip(label: str) -> str:
        s = label.strip()
        if s.lower() == other_chip.lower():
            return other_chip
        return _sanitize_user_facing_text(s, spec) or s
    llm_chip_list = [_clean_chip(c) for c in chips if str(c).strip()]
    if settings:
        chips = suggest_chips_for_field(field_key, chip_query, settings, preferred_agent_ids=hint_ids, draft_flow=draft_flow, spec=spec, messages=messages or [], llm_chips=llm_chip_list)
    elif llm_chip_list:
        chips = _ensure_chips(field_key, llm_chip_list)
    else:
        chips = _ensure_chips(field_key, [])
    chips = [_clean_chip(c) for c in chips]
    suggested = pick_suggested_chip(chips, messages or []) if chips else None
    if suggested and suggested.lower() == other_chip.lower():
        suggested = None
    return InterviewQuestion(field_key=field_key, topic_label=_topic_label(field_key), question=question, chips=chips, why_it_matters=None, suggested_chip=suggested, catalog_reference=catalog_ref or None, suggestion_reason=suggestion_reason or None)

def _polish_interview_question(question: str, *, max_words: int=48) -> str:
    """Light polish for practitioner-facing questions — keep technical vocabulary."""
    q = re.sub('\\s+', ' ', question.strip())
    q = re.sub('\\b(closest match|top match|from our catalog|spec\\.json|affine launchpad)\\b', '', q, flags=re.I)
    q = re.sub('\\s{2,}', ' ', q).strip(' ,.;:-')
    q = re.sub('[\\u2014:\\-]\\s*[^?]*\\b(?:or|and/or)\\b[^?]*\\??$', '', q, flags=re.I).strip(' ,.;:-')
    words = q.split()
    if len(words) > max_words:
        q = ' '.join(words[:max_words]).rstrip(',.;:')
    if not q.endswith('?'):
        q = q.rstrip('.') + '?'
    return q

def _build_catalog_backed_question(spec: ArchitectureSpec, field_key: str, settings: Settings, messages: list[ChatMessage]) -> InterviewQuestion:
    """
    Deterministic question + dynamic catalog suggestions.

    This avoids hard-to-understand LLM wording while keeping chips dynamic from spec.json.
    """
    if _user_interview_answer_count(messages) == 0:
        question = _polish_interview_question(easy_question_for_project(spec, field_key, settings))
    else:
        question = _user_only_question_for_field(spec, field_key)
    hint_ids = [h.agent_id for h in spec.catalog_hints or [] if h.agent_id]
    chip_query = _chip_query_context(spec, messages, target_field=field_key)
    chips = suggest_chips_for_field(field_key, chip_query, settings, preferred_agent_ids=hint_ids, spec=spec, messages=messages)
    catalog_ref, _catalog_why = catalog_suggestion_context(chip_query, settings, preferred_agent_ids=hint_ids)
    suggestion_reason = suggestion_reason_for_field(field_key, chip_query, settings, preferred_agent_ids=hint_ids)
    other = 'Other / describe in chat'
    suggested = pick_suggested_chip(chips, messages)
    if suggested and suggested.lower() == other.lower():
        suggested = None
    return InterviewQuestion(field_key=field_key, topic_label=_topic_label(field_key), question=question, chips=chips, why_it_matters=None, suggested_chip=suggested, catalog_reference=catalog_ref or None, suggestion_reason=suggestion_reason or None)

def _user_only_question_for_field(spec: ArchitectureSpec, field_key: str) -> str:
    """Deterministic non-catalog question text for clarity."""
    hook = spec.problem_statement.strip()
    if len(hook) > 70:
        hook = hook[:70].rsplit(' ', 1)[0] + '…'
    prompts = {'hitl_behavior': f'For ({hook}), what HITL policy applies — always-on review, confidence threshold, or exception-only?', 'integrations': f'For ({hook}), which source and destination integrations are required (API, batch files, CRM, warehouse)?', 'architectural_flow': f'For ({hook}), define the pipeline sequence from trigger to completion.', 'core_components': f'For ({hook}), which services/modules are required in the architecture?', 'data_flow': f'For ({hook}), use step-to-step handoffs or a shared operational datastore?', 'orchestration_model': f'For ({hook}), prefer sequential, parallel, event-driven, or manual triggers?'}
    return _polish_interview_question(prompts.get(field_key, f'What configuration is required for {field_key}?'))

def _should_use_user_only_question(question: str) -> bool:
    text = (question or '').strip()
    if not text:
        return True
    if len(text.split()) > 52:
        return True
    if _FORBIDDEN_QUESTION_PHRASES.search(text):
        return True
    if re.search('\\b(spec\\.json|from our catalog|catalog agent)\\b', text, flags=re.I):
        return True
    return False

def next_question(spec: ArchitectureSpec, settings: Settings, last_answered_field: Optional[str]=None, client: AzureOpenAI | None=None, messages: list[ChatMessage] | None=None) -> Optional[InterviewQuestion]:
    """Hybrid mode: prompt-driven question first, deterministic fallback."""
    msgs = messages or []
    if msgs:
        _confirm_user_answered_fields(spec, msgs)
    spec.recompute_status()
    if spec.status == 'ready':
        return None
    if client is None:
        client = make_client(settings)
    open_gaps = _open_interview_gaps(spec, msgs)
    if not open_gaps:
        spec = _infer_interview_fields_on_complete(spec, msgs, settings, client)
        if spec.status == 'ready':
            return None
        open_gaps = _open_interview_gaps(spec, msgs)
        if not open_gaps:
            return None
    fallback_key = _pick_next_field_key(spec, msgs, last_answered_field, settings)
    field_key = fallback_key
    is_first_turn = _user_interview_answer_count(msgs) == 0
    if is_first_turn and field_key:
        return _build_catalog_backed_question(spec, field_key, settings, msgs)
    try:
        system = _build_catalog_pattern_prompt(spec, msgs, settings)
        raw = call_llm(client, settings, system, 'Respond with the JSON object for this interview turn only.', json_mode=True, temperature=0.2)
        if 'READY_TO_GENERATE' in raw.upper():
            if _user_interview_answer_count(msgs) >= 1:
                spec = _infer_interview_fields_on_complete(spec, msgs, settings, client)
                if spec.status == 'ready':
                    return None
        parsed = json.loads(strip_json_fences(raw))
        if parsed.get('ready') is True and (not open_gaps):
            if _user_interview_answer_count(msgs) >= 1:
                spec = _infer_interview_fields_on_complete(spec, msgs, settings, client)
                if spec.status == 'ready':
                    return None
        elif parsed.get('ready') is True and open_gaps:
            logger.info('Ignoring premature ready=true while gaps remain: %s', open_gaps)
        parsed_field = str(parsed.get('field_key') or '').strip()
        resolved = _resolve_field_key_for_turn(parsed_field, open_gaps, spec, msgs, fallback_key)
        if not resolved:
            return _build_catalog_backed_question(spec, fallback_key or open_gaps[0], settings, msgs)
        field_key = resolved
        if parsed_field and parsed_field != field_key:
            logger.info('Rejected field_key %r (open gaps: %s) — using %r', parsed_field, open_gaps, field_key)
        prompt_question = _question_from_parsed(spec, field_key, parsed, settings, msgs)
        if prompt_question.question and len(prompt_question.chips) >= 2:
            return prompt_question
    except Exception as exc:
        logger.warning('Hybrid prompt mode fallback triggered: %s', exc)
    return _build_catalog_backed_question(spec, field_key, settings, msgs)

def _agents_for_graph_draft(session: InterviewSession) -> list:
    """Merge workflow matches with catalog hints for a richer agent chain."""
    state = session.agent_workflow
    if not state:
        return []
    agents = list(state.matched_agents)
    seen = {a.agent_id for a in agents if a.agent_id}
    for hint in session.spec.catalog_hints or []:
        aid = str(hint.agent_id or '').strip()
        if not aid or aid in seen:
            continue
        agents.append(MatchedAgentSummary(agent_id=aid, name=hint.name or aid, reason=(hint.function_summary or '')[:140]))
        seen.add(aid)
        if len(agents) >= 6:
            break
    return agents

def _graph_draft_from_workflow(session: InterviewSession) -> GraphDraft | None:
    """Fast sequential graph from agent-workflow matches (no LLM)."""
    chain = _agents_for_graph_draft(session)
    if not chain:
        return None
    nodes: list[GraphNode] = [GraphNode(id='intake', label='Request intake', type='gateway')]
    edges: list[GraphEdge] = []
    prev = 'intake'
    for i, agent in enumerate(chain):
        nid = normalize_node_id(f'agent-{agent.agent_id or i}')
        nodes.append(GraphNode(id=nid, label=agent.name, type='agent', agent_id=agent.agent_id or None, description=(agent.reason or '')[:200] or None))
        edges.append(GraphEdge(from_id=prev, to_id=nid))
        prev = nid
    nodes.append(GraphNode(id='delivery', label='Deliver result', type='gateway'))
    edges.append(GraphEdge(from_id=prev, to_id='delivery'))
    return sanitize_graph(GraphDraft(nodes=nodes, edges=edges))

def _blueprint_markdown_from_session(session: InterviewSession, settings: Settings) -> str:
    """Deterministic blueprint text for Phase 3 (no LLM)."""
    parts: list[str] = []
    ps = session.spec.problem_statement.strip()
    if ps:
        parts.append(f'## Problem\n{ps}')
    ts = (session.spec.transcript_summary or '').strip()
    if ts:
        parts.append(f'## Summary\n{ts}')
    known = session.spec.compact_known_json()
    if known:
        parts.append(f'## Requirements\n```json\n{json.dumps(known, indent=2)}\n```')
    if session.agent_workflow:
        parts.append(format_workflow_configured(session.agent_workflow, settings))
    return '\n\n'.join(parts) or ps or 'Architecture ready for planning.'

def synthesize_architecture_blueprint(spec: ArchitectureSpec, messages: list[ChatMessage], settings: Settings, client: AzureOpenAI | None=None) -> tuple[str, GraphDraft | None]:
    """
    Produce markdown blueprint and structured graph draft for Phase 3.

    Returns:
        (blueprint_markdown, graph_draft or None)
    """
    if client is None:
        client = make_client(settings)
    system = load_prompt('architecture_synthesis.txt')
    user = f'PROBLEM STATEMENT:\n{spec.problem_statement}\n\nCOMPLETED SPEC JSON:\n{spec.model_dump_json(indent=2)}\n\nTRANSCRIPT SUMMARY:\n{spec.transcript_summary}\n\nCATALOG HINTS:\n{_format_catalog_hints(spec.catalog_hints)}\n\nRECENT CONVERSATION:\n{_format_transcript(messages, RECENT_MESSAGE_LIMIT)}'
    raw = call_llm(client, settings, system, user, temperature=0.2, json_mode=True)
    parsed = json.loads(strip_json_fences(raw))
    markdown = (parsed.get('blueprint_markdown') or '').strip()
    graph: GraphDraft | None = None
    if parsed.get('graph_draft'):
        try:
            graph = sanitize_graph(GraphDraft.model_validate(parsed['graph_draft']))
        except Exception as exc:
            logger.warning('graph_draft validation failed: %s', exc)
    if not markdown:
        markdown = raw.strip()
    logger.info('Architecture package synthesized (%d chars markdown, %d nodes)', len(markdown), len(graph.nodes) if graph else 0)
    return (markdown, graph)

def _finalize_session(session: InterviewSession, settings: Settings, client: AzureOpenAI) -> InterviewSession:
    """
    Mark session ready and produce architecture artifacts.

    Fast path: deterministic blueprint + graph draft, then a single
    ``plan_architecture`` call cached on the session so the builder loads
    immediately. Skips the extra synthesis LLM that previously ran here.
    """
    session.spec.status = 'ready'
    session.pending_question = None
    session.spec.architecture_blueprint = _blueprint_markdown_from_session(session, settings)
    workflow_graph = _graph_draft_from_workflow(session)
    if workflow_graph:
        session.spec.graph_draft = workflow_graph
    if session.architecture_plan is None:
        try:
            session.architecture_plan = plan_architecture(session, settings, client=client)
            logger.info('Pre-generated architecture plan at finalize for session %s', session.id)
        except Exception as exc:
            logger.warning('Pre-plan at finalize failed for session %s (builder will retry): %s', session.id, exc)
    session.messages.append(ChatMessage(role='assistant', content='Requirements and architectural flow are confirmed. Opening the workflow builder with your architecture plan.'))
    return session

def _assistant_message_for_question(question: InterviewQuestion) -> str:
    """Plain chat text — no technical prefixes."""
    if is_clarifying_field_key(question.field_key):
        return question.question
    return question.question

def _clarifying_to_interview_question(item: ClarifyingQuestionItem, spec: ArchitectureSpec, settings: Settings, messages: list[ChatMessage] | None=None, prior_answers: dict[str, str] | None=None) -> InterviewQuestion:
    hint_ids = [h.agent_id for h in spec.catalog_hints or [] if h.agent_id]
    clarifying_query = _chip_query_context(spec, messages or [], target_field='core_components')
    scope_chips = chips_for_clarifying_question(item.id, spec.problem_statement, settings, preferred_agent_ids=hint_ids, prior_answers=prior_answers)
    catalog_ref, catalog_why = catalog_suggestion_context(clarifying_query, settings, preferred_agent_ids=hint_ids)
    suggested = pick_suggested_chip(scope_chips, query=clarifying_query)
    return InterviewQuestion(field_key=clarifying_field_key(item.id), topic_label='Scope', question=_polish_interview_question(item.question), chips=scope_chips, why_it_matters=item.why_it_matters or 'Narrows agent selection and pipeline ordering.', suggested_chip=suggested, catalog_reference=catalog_ref or None, suggestion_reason=f'Suggested from {catalog_ref}: closest scope match in spec.json.' if catalog_ref else None)

def _begin_main_interview(session: InterviewSession, settings: Settings, client: AzureOpenAI) -> InterviewSession:
    """Start spec.json agent workflow interview (match agents → input questions)."""
    if session.discovery and session.discovery.phase == 'complete':
        session.clarifying_answers = discovery_to_clarifying_answers(session.discovery)
        session.spec.transcript_summary = discovery_to_transcript_summary(session.discovery)
    elif session.clarifying_answers:
        session.spec.transcript_summary = format_clarifying_summary(session.clarifying_questions, session.clarifying_answers)
    else:
        session.spec.transcript_summary = session.spec.problem_statement[:800]
    return begin_agent_workflow_interview(session, settings, client)

def _begin_workflow_from_message(session: InterviewSession, statement: str, settings: Settings, client: AzureOpenAI) -> InterviewSession:
    """Transition from open chat into catalog-backed workflow scoping."""
    text = statement.strip()
    session.spec.problem_statement = text
    session.chat_phase = 'workflow'
    session.clarifying_questions = []
    session.clarifying_answers = {}
    session.discovery = None
    session.agent_workflow = None
    session.pending_question = None
    session.awaiting_problem_revision = False
    return begin_discovery_phase(session, settings, client, intro_prefix='restarted')

def _handle_open_chat_turn(session: InterviewSession, answer: str, settings: Settings, client: AzureOpenAI) -> InterviewSession:
    session.messages.append(ChatMessage(role='user', content=answer, field_key=None))
    if should_begin_workflow_building(answer):
        return _begin_workflow_from_message(session, answer, settings, client)
    reply = answer_open_chat_turn(answer, session, settings, client)
    session.messages.append(ChatMessage(role='assistant', content=reply))
    return session

def _refresh_pending_question_chips(session: InterviewSession, settings: Settings, client: AzureOpenAI) -> None:
    """Rebuild chips for the active question from current catalog selections."""
    pq = session.pending_question
    if not pq:
        return
    fk = pq.field_key
    if session.agent_workflow and is_agent_input_field_key(fk):
        q = next((x for x in session.agent_workflow.questions if x.field_key == fk), None)
        if q:
            session.pending_question = _question_item_to_interview(q, settings, session, client)
        return
    if is_discovery_field_key(fk):
        refresh_discovery_question_chips(session, settings)
        return
    if is_clarifying_field_key(fk):
        qid = fk.split(':', 1)[1]
        chips = chips_for_clarifying_question(qid, session.spec.problem_statement, settings, prior_answers=session.clarifying_answers, preferred_agent_ids=[h.agent_id for h in session.spec.catalog_hints or [] if h.agent_id])
        session.pending_question = pq.model_copy(update={'chips': chips})
        return
    chips = suggest_chips_for_field(fk, session.spec.problem_statement, settings, clarifying_answers=session.clarifying_answers, workflow_answers=session.agent_workflow.answers if session.agent_workflow else None, spec=session.spec)
    session.pending_question = pq.model_copy(update={'chips': chips})

def _handle_classified_scoping_turn(session: InterviewSession, answer: str, settings: Settings, client: AzureOpenAI, *, field_key: str | None) -> InterviewSession | None:
    """
    Handle scoping turns that must NOT advance the interview.
    Returns updated session, or None when intent is ANSWER (caller should advance).
    """
    intent = classify_turn_intent(answer, session)
    logger.info('scoping_turn_intent intent=%s field=%s session=%s', intent.value, field_key, session.id)
    if session.discovery:
        session.discovery.debug_entries.append({'event': 'turn_intent', 'intent': intent.value, 'field': field_key})
    session.messages.append(ChatMessage(role='user', content=answer, field_key=field_key))
    if intent == TurnIntent.GREETING:
        session.messages.append(ChatMessage(role='assistant', content=handle_greeting(session)))
        return session
    if intent in (TurnIntent.CLARIFICATION_REQUEST, TurnIntent.QUESTION, TurnIntent.UNKNOWN):
        if session.discovery:
            session.discovery.interview_phase = 'explaining'
        _refresh_pending_question_chips(session, settings, client)
        reply = generate_clarification_response(answer, session, settings, client)
        session.messages.append(ChatMessage(role='assistant', content=reply))
        if session.discovery:
            session.discovery.interview_phase = 'waiting_for_answer'
        return session
    if intent == TurnIntent.DECLINE:
        session.messages.append(ChatMessage(role='assistant', content='No problem — we can skip that for now.'))
        if field_key and is_discovery_field_key(field_key):
            return skip_discovery_turn(session, settings, client, field_key=field_key)
        session.pending_question = None
        if session.agent_workflow is not None and field_key:
            return advance_agent_workflow_turn(session, settings, 'Not specified', client, answered_field_key=field_key)
        return session
    if intent == TurnIntent.FINISH:
        session.messages.append(ChatMessage(role='assistant', content='Understood — wrapping up scoping with what we have so far.'))
        if session.discovery and session.discovery.question_count >= 1:
            return complete_discovery_phase(session, settings, client)
        session.pending_question = None
        if session.agent_workflow is not None:
            return advance_agent_workflow_turn(session, settings, answer, client, answered_field_key=field_key)
        return session
    if intent != TurnIntent.ANSWER:
        session.messages.append(ChatMessage(role='assistant', content='Please answer the current question, or say "explain this" if you\'d like more context.'))
        return session
    return None

def run_interview_turn(session: InterviewSession, settings: Settings, user_answer: str | None=None, client: AzureOpenAI | None=None) -> InterviewSession:
    if client is None:
        client = make_client(settings)
    fields_just_set: set[str] = set()
    if user_answer is not None:
        answer = user_answer.strip()
        if not answer:
            raise ValueError('Answer cannot be empty')
        if is_custom_describe_placeholder(answer):
            raise ValueError("Please describe your answer in the text box instead of selecting 'Other / describe' alone.")
        if session_in_open_chat(session):
            return _handle_open_chat_turn(session, answer, settings, client)
        if session.awaiting_problem_revision:
            return _handle_problem_revision_turn(session, answer, settings, client)
        if is_change_problem_statement_intent(answer):
            revised = extract_revised_problem_statement(answer)
            if revised:
                return _restart_interview_with_problem_statement(session, revised, settings, client)
            return _prompt_for_problem_revision(session, user_message=answer)
        field_key = session.pending_question.field_key if session.pending_question else None
        if session.pending_question:
            handled = _handle_classified_scoping_turn(session, answer, settings, client, field_key=field_key)
            if handled is not None:
                return handled
        if is_revision_help_question(answer):
            session.messages.append(ChatMessage(role='user', content=answer, field_key=field_key))
            session.messages.append(ChatMessage(role='assistant', content=problem_statement_guidance_text()))
            return session
        session.messages.append(ChatMessage(role='user', content=answer, field_key=field_key))
        if session.agent_workflow is not None:
            session.pending_question = None
            return advance_agent_workflow_turn(session, settings, answer, client, answered_field_key=field_key)
        session.pending_question = None
        if field_key and is_discovery_field_key(field_key):
            return advance_discovery_turn(session, settings, client, answer, field_key=field_key)
        if field_key and is_clarifying_field_key(field_key):
            qid = field_key.split(':', 1)[1]
            session.clarifying_answers[qid] = answer
            next_cq = pending_clarifying_question(session.clarifying_questions, session.clarifying_answers)
            if next_cq:
                q = _clarifying_to_interview_question(next_cq, session.spec, settings, session.messages, prior_answers=session.clarifying_answers)
                session.pending_question = q
                session.messages.append(ChatMessage(role='assistant', content=_assistant_message_for_question(q), field_key=q.field_key))
                return session
            return _begin_main_interview(session, settings, client)
        if field_key:
            session.last_answered_field = field_key
            if not is_agent_input_field_key(field_key):
                _apply_direct_answer(session.spec, field_key, answer)
                fields_just_set.add(field_key)
    session.spec = update_spec(session.spec, session.messages, settings, client=client, fields_just_set=fields_just_set)
    should_refresh_hints = not session.spec.catalog_hints
    if not should_refresh_hints:
        user_turns = sum((1 for msg in session.messages if msg.role == 'user'))
        should_refresh_hints = user_turns % CATALOG_HINT_REFRESH_USER_TURN_EVERY == 0
    if should_refresh_hints:
        refresh_query = f'{session.spec.problem_statement}\n\n{session.spec.transcript_summary}'
        session.spec.catalog_hints = build_catalog_hints_for_interview(refresh_query, settings, top_k=12)
    if session.spec.status == 'ready':
        return _finalize_session(session, settings, client)
    question = next_question(session.spec, settings, last_answered_field=session.last_answered_field, client=client, messages=session.messages)
    if question is None:
        if session.spec.status == 'ready':
            return _finalize_session(session, settings, client)
        logger.warning('Interview ended without ready status for session %s — inferring fields', session.id)
        session.spec = _infer_interview_fields_on_complete(session.spec, session.messages, settings, client)
        if session.spec.status == 'ready':
            return _finalize_session(session, settings, client)
        return session
    session.pending_question = question
    session.messages.append(ChatMessage(role='assistant', content=_assistant_message_for_question(question), field_key=question.field_key))
    return session

def _restart_interview_with_problem_statement(session: InterviewSession, new_statement: str, settings: Settings, client: AzureOpenAI) -> InterviewSession:
    """Replace the opening problem and rerun scoping from scratch."""
    statement = new_statement.strip()
    if len(statement) < 10:
        raise ValueError('Problem statement must be at least 10 characters')
    session.spec = ArchitectureSpec.empty(statement)
    session.clarifying_questions = []
    session.clarifying_answers = {}
    session.discovery = None
    session.agent_workflow = None
    session.pending_question = None
    session.last_answered_field = None
    session.architecture_plan = None
    session.awaiting_problem_revision = False
    session.chat_phase = 'workflow'
    session.messages = [ChatMessage(role='user', content=statement, field_key=None)]
    return _start_clarifying_phase(session, settings, client, intro_prefix='restarted')

def _prompt_for_problem_revision(session: InterviewSession, *, user_message: str | None=None) -> InterviewSession:
    """Fresh chat — clear prior scoping and ask for a new workflow description."""
    session.clarifying_questions = []
    session.clarifying_answers = {}
    session.discovery = None
    session.agent_workflow = None
    session.pending_question = None
    session.last_answered_field = None
    session.architecture_plan = None
    session.awaiting_problem_revision = True
    session.chat_phase = 'workflow'
    session.messages = []
    if user_message and user_message.strip():
        session.messages.append(ChatMessage(role='user', content=user_message.strip(), field_key=None))
    session.messages.append(ChatMessage(role='assistant', content='Starting a new chat. Describe the workflow you want to build (what goes in, what should happen, what comes out).'))
    return session

def _handle_problem_revision_turn(session: InterviewSession, answer: str, settings: Settings, client: AzureOpenAI) -> InterviewSession:
    session.messages.append(ChatMessage(role='user', content=answer, field_key=None))
    if is_revision_help_question(answer):
        session.awaiting_problem_revision = True
        session.pending_question = None
        session.messages.append(ChatMessage(role='assistant', content=problem_statement_guidance_text()))
        return session
    revised = extract_revised_problem_statement(answer)
    if revised:
        return _restart_interview_with_problem_statement(session, revised, settings, client)
    if is_change_problem_statement_intent(answer):
        session.messages.append(ChatMessage(role='assistant', content='Paste the full new problem statement in the box below (at least one sentence describing the workflow).'))
        return session
    if is_problem_revision_submission(answer):
        return _restart_interview_with_problem_statement(session, answer, settings, client)
    session.awaiting_problem_revision = True
    session.pending_question = None
    session.messages.append(ChatMessage(role='assistant', content='I need a bit more detail about what you want automated. ' + problem_statement_guidance_text()))
    return session

def _start_clarifying_phase(session: InterviewSession, settings: Settings, client: AzureOpenAI, *, intro_prefix: str='first') -> InterviewSession:
    """State-driven discovery phase (replaces fixed clarifying questionnaire)."""
    return begin_discovery_phase(session, settings, client, intro_prefix=intro_prefix)

def start_session(problem_statement: str, settings: Settings) -> InterviewSession:
    statement = problem_statement.strip()
    if not statement:
        raise ValueError('Message is required')
    session = InterviewSession(id=str(uuid.uuid4()), spec=ArchitectureSpec.empty(statement), chat_phase='open')
    session.messages.append(ChatMessage(role='user', content=statement, field_key=None))
    client = make_client(settings)
    if should_begin_workflow_building(statement):
        return _begin_workflow_from_message(session, statement, settings, client)
    reply = answer_open_chat_turn(statement, session, settings, client)
    session.messages.append(ChatMessage(role='assistant', content=reply))
    return session


# ========================================================================
# api/py
# ========================================================================


"""Interview session store — memory cache with JSON persistence (local or Azure Blob)."""
import json
import logging
from pathlib import Path
from threading import Lock
from typing import Dict, Optional
logger = logging.getLogger(__name__)
_lock = Lock()
_sessions: Dict[str, InterviewSession] = {}
SESSIONS_DIR = BACKEND_ROOT / 'data' / 'sessions'
SESSION_STORAGE_KEY = 'sessions/{session_id}.json'

def _session_storage_key(session_id: str) -> str:
    safe = session_id.replace('/', '_').replace('..', '_')
    return SESSION_STORAGE_KEY.format(session_id=safe)

def _legacy_session_path(session_id: str) -> Path:
    safe = session_id.replace('/', '_').replace('..', '_')
    return SESSIONS_DIR / f'{safe}.json'

def _persist(session: InterviewSession) -> None:
    payload = json.loads(session.model_dump_json())
    try:
        get_data_storage().write_json(_session_storage_key(session.id), payload)
    except Exception as exc:
        logger.warning('Could not persist session %s to storage: %s', session.id, exc)
    if not blob_storage_configured():
        try:
            SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
            _legacy_session_path(session.id).write_text(session.model_dump_json(indent=2), encoding='utf-8')
        except OSError as exc:
            logger.warning('Could not persist session %s to disk: %s', session.id, exc)

def _load_from_storage(session_id: str) -> Optional[InterviewSession]:
    raw = get_data_storage().read_json(_session_storage_key(session_id))
    if raw:
        try:
            return InterviewSession.model_validate(raw)
        except Exception as exc:
            logger.warning('Could not parse session %s from storage: %s', session_id, exc)
    if blob_storage_configured():
        return None
    path = _legacy_session_path(session_id)
    if path.is_file():
        try:
            legacy = json.loads(path.read_text(encoding='utf-8'))
            session = InterviewSession.model_validate(legacy)
            _persist(session)
            return session
        except Exception as exc:
            logger.warning('Could not load legacy session %s from disk: %s', session_id, exc)
    return None

def save(session: InterviewSession) -> None:
    with _lock:
        _sessions[session.id] = session
    _persist(session)
    if session.architecture_plan is not None or session.spec.status == 'ready':
        try:
            sync_workflow_from_session(session)
        except Exception as exc:
            logger.warning('Builder workflow sync after session save failed for %s: %s', session.id, exc)

def get(session_id: str) -> Optional[InterviewSession]:
    with _lock:
        cached = _sessions.get(session_id)
    if cached is not None:
        return cached
    loaded = _load_from_storage(session_id)
    if loaded is not None:
        with _lock:
            _sessions[session_id] = loaded
        return loaded
    return None

def _session_rank(raw: dict) -> tuple:
    """Newest / most complete sessions first."""
    spec = raw.get('spec') or {}
    status = str(spec.get('status') or '')
    status_rank = {'ready': 3, 'sufficient': 2}.get(status, 1)
    return (status_rank, len(raw.get('messages') or []), 1 if raw.get('architecture_plan') else 0)

def list_session_summaries(*, limit: int=50) -> list[dict]:
    """List saved interviews from storage (newest blobs first, capped scan)."""
    storage = get_data_storage()
    keys = storage.list_keys_by_mtime('sessions', newest_first=True)
    rows: list[tuple[tuple, dict]] = []
    max_scan = min(len(keys), max(limit * 4, limit))
    scanned = 0
    for key in keys:
        if scanned >= max_scan:
            break
        if not key.startswith('sessions/') or not key.endswith('.json'):
            continue
        scanned += 1
        session_id = key.split('/')[-1].replace('.json', '')
        raw = storage.read_json(_session_storage_key(session_id))
        if not raw:
            continue
        spec = raw.get('spec') or {}
        problem = str(spec.get('problem_statement') or '').strip()
        summary = {'id': raw.get('id') or session_id, 'status': spec.get('status'), 'problem_statement': problem, 'message_count': len(raw.get('messages') or []), 'has_architecture_plan': bool(raw.get('architecture_plan'))}
        rows.append((_session_rank(raw), summary))
    rows.sort(key=lambda item: item[0], reverse=True)
    return [summary for _, summary in rows[:limit]]

def delete(session_id: str) -> bool:
    with _lock:
        removed = _sessions.pop(session_id, None) is not None
    removed = get_data_storage().delete(_session_storage_key(session_id)) or removed
    path = _legacy_session_path(session_id)
    if path.is_file():
        try:
            path.unlink()
            removed = True
        except OSError as exc:
            logger.warning('Could not delete session file %s: %s', session_id, exc)
    delete_workflow(session_id)
    return removed


# ========================================================================
# api/py
# ========================================================================


"""Workflow builder snapshots (canvas layout + plan) in shared data storage."""
import logging
from typing import Any, Optional
logger = logging.getLogger(__name__)
WORKFLOW_INDEX_KEY = 'workflows/_index.json'

def _entry_has_plan(entry: dict[str, Any]) -> bool:
    """Workflows list only includes sessions with a non-empty architecture graph."""
    if not entry.get('hasPlan'):
        return False
    try:
        return int(entry.get('stepCount') or 0) > 0
    except (TypeError, ValueError):
        return False

def _filter_planned(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in entries if _entry_has_plan(e)]

def _workflow_key(session_id: str) -> str:
    safe = session_id.replace('/', '_').replace('..', '_')
    return f'workflows/{safe}.json'

def load_workflow(session_id: str) -> Optional[dict[str, Any]]:
    return get_data_storage().read_json(_workflow_key(session_id))

def save_workflow(session_id: str, document: dict[str, Any]) -> None:
    doc = dict(document)
    doc['sessionId'] = session_id
    get_data_storage().write_json(_workflow_key(session_id), doc)
    _upsert_index_entry(session_id, doc)

def delete_workflow(session_id: str) -> bool:
    removed = get_data_storage().delete(_workflow_key(session_id))
    _remove_index_entry(session_id)
    return removed

def _index_from_sessions() -> list[dict[str, Any]]:
    """Sessions with a non-empty architecture graph (when no workflow blobs exist)."""
    entries: list[dict[str, Any]] = []
    for row in list_session_summaries(limit=50):
        if not row.get('has_architecture_plan'):
            continue
        sid = row['id']
        session = get(sid)
        if session is None or session.architecture_plan is None:
            continue
        nodes = session.architecture_plan.graph.nodes or []
        if not nodes:
            continue
        ps = str(row.get('problem_statement') or '').strip()
        title = ps[:72] + ('…' if len(ps) > 72 else '') if ps else f'Launchpad {sid[:8]}'
        plan = session.architecture_plan
        entries.append({'sessionId': sid, 'title': title, 'savedAt': '', 'stepCount': len(nodes), 'agentCount': len(plan.reuse_decisions) or len(nodes), 'hasPlan': True})
    return entries

def _sort_workflow_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(entries, key=lambda e: e.get('savedAt') or '', reverse=True)

def rebuild_workflow_index() -> int:
    """Rebuild workflows/_index.json from workflow blobs that have a plan (newest first)."""
    entries = _sort_workflow_entries(_filter_planned(_index_from_blob_workflows()))
    if not entries:
        entries = _sort_workflow_entries(_index_from_sessions())
    get_data_storage().write_json(WORKFLOW_INDEX_KEY, {'entries': entries})
    return len(entries)

def list_workflow_index() -> list[dict[str, Any]]:
    raw = get_data_storage().read_json(WORKFLOW_INDEX_KEY)
    if raw:
        entries = raw.get('entries')
        if isinstance(entries, list) and entries:
            return _sort_workflow_entries(_filter_planned(entries))
    blob_entries = _filter_planned(_index_from_blob_workflows())
    if blob_entries:
        return _sort_workflow_entries(blob_entries)
    return _sort_workflow_entries(_index_from_sessions())

def _index_from_blob_workflows(*, max_items: int=60) -> list[dict[str, Any]]:
    storage = get_data_storage()
    keys = storage.list_keys_by_mtime('workflows', newest_first=True)
    entries: list[dict[str, Any]] = []
    for key in keys:
        if len(entries) >= max_items:
            break
        if key == 'workflows/_index.json' or not key.endswith('.json'):
            continue
        session_id = key.split('/')[-1].replace('.json', '')
        doc = storage.read_json(f'workflows/{session_id}.json')
        if not doc:
            continue
        plan = doc.get('plan') or {}
        graph = plan.get('graph') or {}
        nodes = graph.get('nodes') or []
        if not isinstance(nodes, list) or len(nodes) == 0:
            continue
        title = (doc.get('title') or '').strip() or (doc.get('problemStatement') or '').strip()[:72] or f'Launchpad workflow {session_id[:8]}'
        entries.append({'sessionId': session_id, 'title': title[:72] + ('…' if len(title) > 72 else ''), 'savedAt': doc.get('savedAt') or '', 'stepCount': len(nodes), 'agentCount': len(plan.get('reuse_decisions') or nodes), 'hasPlan': True})
    return entries

def _upsert_index_entry(session_id: str, document: dict[str, Any]) -> None:
    plan = document.get('plan') or {}
    graph = plan.get('graph') or {}
    nodes = graph.get('nodes') or []
    if not isinstance(nodes, list) or len(nodes) == 0:
        _remove_index_entry(session_id)
        return
    title = (document.get('title') or '').strip() or (document.get('problemStatement') or '').strip()[:72] or f'Launchpad workflow {session_id[:8]}'
    entry = {'sessionId': session_id, 'title': title[:72] + ('…' if len(title) > 72 else ''), 'savedAt': document.get('savedAt') or '', 'stepCount': len(nodes) if isinstance(nodes, list) else 0, 'agentCount': len(plan.get('reuse_decisions') or nodes), 'hasPlan': bool(nodes)}
    entries = [e for e in list_workflow_index() if e.get('sessionId') != session_id]
    entries.insert(0, entry)
    get_data_storage().write_json(WORKFLOW_INDEX_KEY, {'entries': _filter_planned(entries)})

def _remove_index_entry(session_id: str) -> None:
    entries = [e for e in list_workflow_index() if e.get('sessionId') != session_id]
    get_data_storage().write_json(WORKFLOW_INDEX_KEY, {'entries': entries})


# ========================================================================
# api/routes.py
# ========================================================================


"""FastAPI routes for the Phase 2 requirements interview."""
from functools import partial
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool
router = APIRouter(prefix='/api')

class CatalogAgentsResponse(BaseModel):
    agents: list[AgentRecord]
    count: int

class StartSessionRequest(BaseModel):
    problem_statement: str = Field(..., min_length=1, max_length=8000)

class TurnRequest(BaseModel):
    answer: str = Field(..., min_length=1, max_length=2000)

class SessionResponse(BaseModel):
    session: InterviewSession

class SessionSummary(BaseModel):
    id: str
    status: Optional[str] = None
    problem_statement: str = ''
    message_count: int = 0
    has_architecture_plan: bool = False

class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]
    storage_backend: str

class ArchitectureResponse(BaseModel):
    """Phase 3 planned architecture for a session."""
    session_id: str
    plan: ArchitecturePlan

class ApplyRemediationRequest(BaseModel):
    """Apply a user-selected fix by finding + option id (server resolves full action)."""
    finding_id: str = Field(..., min_length=3, max_length=128)
    option_id: str = Field(..., min_length=1, max_length=128)

class WorkflowsIndexResponse(BaseModel):
    workflows: list[dict]

class BuilderWorkflowResponse(BaseModel):
    workflow: dict

@router.get('/catalog/agents', response_model=CatalogAgentsResponse)
def list_catalog_agents() -> CatalogAgentsResponse:
    """All Affine built agents from data/spec.json (Agent Library)."""
    settings = get_settings()
    agents = load_all_catalog_agents(settings)
    return CatalogAgentsResponse(agents=agents, count=len(agents))

@router.post('/sessions', response_model=SessionResponse)
async def create_session(body: StartSessionRequest) -> SessionResponse:
    """Start a smart interview from the user's problem statement."""
    settings = get_settings()
    try:
        session = await run_in_threadpool(start_session, body.problem_statement, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Interview start failed: {exc}') from exc
    await run_in_threadpool(save, session)
    return SessionResponse(session=session)

@router.get('/sessions', response_model=SessionListResponse)
def list_sessions() -> SessionListResponse:
    """Recent interviews from Azure Blob (or local mirror)."""
    rows = list_session_summaries()
    return SessionListResponse(sessions=[SessionSummary(**row) for row in rows], storage_backend=storage_backend_name())

@router.get('/sessions/{session_id}', response_model=SessionResponse)
def get_session(session_id: str) -> SessionResponse:
    """Return full session state (spec + messages + pending question)."""
    session = get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found. Start a new interview or use a session id saved in Azure Blob (launchpad/sessions/) or data/sessions/.')
    return SessionResponse(session=session)

@router.post('/sessions/{session_id}/turn', response_model=SessionResponse)
async def submit_turn(session_id: str, body: TurnRequest) -> SessionResponse:
    """Submit an answer to the current question and advance the interview."""
    session = await run_in_threadpool(get, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found. Start a new interview or use a session id saved in Azure Blob (launchpad/sessions/) or data/sessions/.')
    if session.spec.status == 'ready':
        raise HTTPException(status_code=409, detail='Specification is already complete')
    if session.pending_question is None and (not session.awaiting_problem_revision) and (not session_in_open_chat(session)):
        raise HTTPException(status_code=409, detail='No question is pending for this session')
    settings = get_settings()
    try:
        session = await run_in_threadpool(partial(run_interview_turn, session, settings, user_answer=body.answer))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Interview turn failed: {exc}') from exc
    await run_in_threadpool(save, session)
    return SessionResponse(session=session)

@router.post('/sessions/{session_id}/architecture', response_model=ArchitectureResponse)
async def generate_architecture(session_id: str, force: bool=False) -> ArchitectureResponse:
    """
    Generate Phase 3 architecture graph with catalog reuse decisions.

    Requires spec status ``sufficient`` or ``ready``. Caches plan on the session
    unless ``force=true``.
    """
    session = await run_in_threadpool(get, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found. Start a new interview or use a session id saved in Azure Blob (launchpad/sessions/) or data/sessions/.')
    if session.spec.status not in ('sufficient', 'ready'):
        raise HTTPException(status_code=409, detail=f'Specification must be sufficient or ready before planning (current: {session.spec.status}).')
    if session.architecture_plan is not None and (not force):
        return ArchitectureResponse(session_id=session_id, plan=session.architecture_plan)
    settings = get_settings()
    try:
        plan = await run_in_threadpool(plan_architecture, session, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f'Architecture planning failed: {exc}') from exc
    session.architecture_plan = plan
    await run_in_threadpool(save, session)
    return ArchitectureResponse(session_id=session_id, plan=plan)

@router.get('/sessions/{session_id}/architecture', response_model=ArchitectureResponse)
def get_architecture(session_id: str) -> ArchitectureResponse:
    """Return cached architecture plan if one was generated."""
    session = get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found. Start a new interview or use a session id saved in Azure Blob (launchpad/sessions/) or data/sessions/.')
    if session.architecture_plan is None:
        raise HTTPException(status_code=404, detail='No architecture plan yet. POST /architecture to generate.')
    return ArchitectureResponse(session_id=session_id, plan=session.architecture_plan)

@router.post('/sessions/{session_id}/architecture/remediate', response_model=ArchitectureResponse)
def remediate_architecture(session_id: str, body: ApplyRemediationRequest) -> ArchitectureResponse:
    """
    Apply a validation remediation choice, update the plan, and re-validate.
    """
    session = get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found. Start a new interview or use a session id saved in Azure Blob (launchpad/sessions/) or data/sessions/.')
    if session.architecture_plan is None:
        raise HTTPException(status_code=404, detail='Generate architecture first (POST /architecture).')
    settings = get_settings()
    try:
        plan = apply_remediation(session.spec, session.architecture_plan.model_copy(deep=True), body.finding_id, body.option_id, settings)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f'Remediation failed: {exc}') from exc
    session.architecture_plan = plan
    save(session)
    return ArchitectureResponse(session_id=session_id, plan=plan)

@router.post('/sessions/{session_id}/architecture/approve', response_model=ArchitectureResponse)
def approve_architecture(session_id: str) -> ArchitectureResponse:
    """Mark architecture approved when validation allows it."""
    session = get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found. Start a new interview or use a session id saved in Azure Blob (launchpad/sessions/) or data/sessions/.')
    if session.architecture_plan is None:
        raise HTTPException(status_code=404, detail='No architecture plan yet.')
    plan = session.architecture_plan
    v = plan.validation
    if v is None:
        plan = revalidate_plan(session.spec, plan.model_copy(deep=True))
    elif not v.can_approve:
        raise HTTPException(status_code=409, detail=v.approval_hint or 'Resolve structural failures before approval.')
    plan.architecture_approved = True
    session.architecture_plan = plan
    save(session)
    return ArchitectureResponse(session_id=session_id, plan=plan)

@router.post('/sessions/{session_id}/architecture/validate', response_model=ArchitectureResponse)
def validate_architecture(session_id: str) -> ArchitectureResponse:
    """Re-run validation on the current plan without regenerating."""
    session = get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail='Session not found. Start a new interview or use a session id saved in Azure Blob (launchpad/sessions/) or data/sessions/.')
    if session.architecture_plan is None:
        raise HTTPException(status_code=404, detail='No architecture plan yet.')
    plan = revalidate_plan(session.spec, session.architecture_plan.model_copy(deep=True))
    session.architecture_plan = plan
    save(session)
    return ArchitectureResponse(session_id=session_id, plan=plan)

@router.get('/catalog/agents', response_model=CatalogAgentsResponse)
def get_catalog_agents() -> CatalogAgentsResponse:
    """All Affine built agents from data/spec.json (Agent Library)."""
    settings = get_settings()
    agents = load_all_catalog_agents(settings)
    return CatalogAgentsResponse(agents=agents, count=len(agents))

@router.get('/workflows', response_model=WorkflowsIndexResponse)
@router.get('/launchpad/workflows', response_model=WorkflowsIndexResponse)
def list_launchpad_workflows() -> WorkflowsIndexResponse:
    """Saved workflow builder snapshots (Azure Blob or local mirror)."""
    return WorkflowsIndexResponse(workflows=list_workflow_index())

@router.get('/sessions/{session_id}/builder', response_model=BuilderWorkflowResponse)
def get_builder_workflow(session_id: str) -> BuilderWorkflowResponse:
    workflow = load_workflow(session_id)
    if workflow is None:
        session = get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail='Builder workflow not found.')
        sync_workflow_from_session(session)
        workflow = load_workflow(session_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail='Builder workflow not found.')
    return BuilderWorkflowResponse(workflow=workflow)

@router.put('/sessions/{session_id}/builder', response_model=BuilderWorkflowResponse)
def save_builder_workflow(session_id: str, body: dict) -> BuilderWorkflowResponse:
    """Persist canvas + plan JSON to shared storage."""
    save_workflow(session_id, body)
    loaded = load_workflow(session_id)
    return BuilderWorkflowResponse(workflow=loaded or body)

@router.get('/templates')
def list_templates() -> list[dict]:
    """Curated workflow templates (server catalog, not mock API)."""
    return load_templates()

@router.get('/dashboard/stats')
def dashboard_stats() -> dict:
    return get_dashboard_stats()

@router.get('/dashboard/runs-over-time')
def dashboard_runs_over_time() -> list[dict]:
    return get_runs_over_time()

@router.get('/dashboard/agent-usage')
def dashboard_agent_usage() -> list[dict]:
    return get_agent_usage()

@router.get('/dashboard/recent-runs')
def dashboard_recent_runs() -> list[dict]:
    return get_recent_activity()

@router.get('/dashboard/top-workflows')
def dashboard_top_workflows() -> list[dict]:
    return get_top_workflows()

@router.delete('/sessions/{session_id}', status_code=204)
def remove_session(session_id: str) -> None:
    if not delete(session_id):
        raise HTTPException(status_code=404, detail='Session not found. Start a new interview or use a session id saved in Azure Blob (launchpad/sessions/) or data/sessions/.')


# ======================================================================
# FastAPI application
# ======================================================================

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

settings = get_settings()
configure_logging(settings.log_level)
get_data_storage()

app = FastAPI(
    title="Affine Agent Launchpad",
    description="Agent Launchpad — requirements interview and architecture planning",
    version="0.3.0",
)

_origins = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _origins if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
def _on_startup() -> None:
    try:
        storage = get_data_storage()
        index_raw = storage.read_json(WORKFLOW_INDEX_KEY)
        if index_raw and index_raw.get("entries"):
            count = len(index_raw["entries"])
        else:
            count = rebuild_workflow_index()
        st = get_storage_status()
        logger.info(
            "Launchpad storage=%s sessions=%s workflows=%s",
            st.get("backend", "unknown"),
            st.get("session_blob_count", "?"),
            count,
        )
    except Exception as exc:
        logger.warning("Startup storage check failed: %s", exc)


@app.get("/")
def root() -> RedirectResponse:
    return RedirectResponse(url="/ui/")


@app.get("/health")
def health() -> dict:
    storage = get_storage_status()
    ok = storage.get("backend") == "local" or storage.get("reachable") is True
    return {
        "status": "ok" if ok else "degraded",
        "phase": 3,
        "features": ["interview", "architecture_plan"],
        "storage": storage,
    }


STATIC_DIR = BACKEND_ROOT / "api" / "static"
app.mount(
    "/ui",
    StaticFiles(directory=str(STATIC_DIR), html=True),
    name="launchpad-ui",
)

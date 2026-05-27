"""Schema for pre-structured project/agent spec JSON imports."""

from pydantic import BaseModel, Field


class SpecProject(BaseModel):
    name: str
    client: str = ""
    vertical: str = ""
    business_problem: str = ""
    solution_summary: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    outcomes: str = ""


class SpecAgent(BaseModel):
    name: str
    version: str = ""
    category: str = ""
    function_summary: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    model_used: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    origin_project: str = ""
    origin_client: str = ""
    vertical: str = ""
    status: str = ""
    typical_accuracy: float | None = None
    notes: str = ""


class ProjectSpecDocument(BaseModel):
    """Canonical import format — matches data/specs/spec.json."""

    project: SpecProject
    agents: list[SpecAgent] = Field(default_factory=list)

"""Schemas for Affine solution catalog PDF structure (solution_agents.pdf)."""

from pydantic import BaseModel, Field


class ParsedSolutionAgent(BaseModel):
    agent_name: str
    function_summary: str = ""
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    model_used: str = ""
    workflow_position: str = ""
    raw_content: str = ""


class ParsedSolution(BaseModel):
    """One solution entry from the catalog PDF."""

    project_name: str
    client: str = ""
    vertical: str = ""
    business_problem: str = ""
    solution_summary: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    outcomes: str = ""
    agents: list[ParsedSolutionAgent] = Field(default_factory=list)
    workflow_steps: list[str] = Field(default_factory=list)
    integrations: list[str] = Field(default_factory=list)
    segment_start_page: int = 1
    segment_text: str = ""


class SolutionCatalogDocument(BaseModel):
    filename: str
    page_count: int
    content_hash: str
    solutions: list[ParsedSolution] = Field(default_factory=list)

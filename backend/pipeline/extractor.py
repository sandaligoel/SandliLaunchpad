"""LLM-based extraction of project and agent records from text chunks."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

from openai import APIError, APITimeoutError, AzureOpenAI, RateLimitError
from pydantic import ValidationError

from config import Settings
from pipeline.chunker import ProjectChunk
from schemas.agent_record import AgentRecord, ProjectRecord, normalize_vertical, slugify
from schemas.extraction_output import ExtractionOutput

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
MAX_RETRIES = 3
BACKOFF_SECONDS = (2, 4, 8)


def _load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8")


def _strip_json_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped JSON in them."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def _call_llm(
    client: AzureOpenAI,
    settings: Settings,
    system_prompt: str,
    user_message: str,
) -> str:
    """
    Call Azure OpenAI chat completion with retry and exponential backoff.

    Raises the last exception after MAX_RETRIES failures.
    """
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            response = client.chat.completions.create(
                model=settings.azure_openai_chat_deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.1,
            )
            content = response.choices[0].message.content
            if not content:
                raise ValueError("Empty response from chat completion")
            return content
        except (RateLimitError, APITimeoutError, APIError) as exc:
            last_error = exc
            wait = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
            logger.warning(
                "API error (attempt %d/%d): %s — retrying in %ds",
                attempt + 1,
                MAX_RETRIES,
                exc,
                wait,
            )
            time.sleep(wait)
    raise last_error or RuntimeError("LLM call failed after retries")


def _parse_project(
    raw: dict,
    source_page: int,
) -> ProjectRecord:
    """Parse and validate a project dict into a ProjectRecord."""
    raw["source_page"] = raw.get("source_page", source_page)
    name = raw.get("name") or "unknown-project"
    record = ProjectRecord(
        id=slugify(name),
        name=name,
        client=raw.get("client") or "",
        vertical=normalize_vertical(raw.get("vertical")),
        business_problem=raw.get("business_problem") or "",
        solution_summary=raw.get("solution_summary") or "",
        agents_used=raw.get("agents_used") or [],
        tech_stack=raw.get("tech_stack") or [],
        outcomes=raw.get("outcomes"),
        source_page=int(raw["source_page"]),
    )
    return record


def _parse_agents(
    raw_list: list,
    source_page: int,
    origin_project: str,
    origin_client: str,
) -> list[AgentRecord]:
    """Parse and validate a list of agent dicts into AgentRecords."""
    agents: list[AgentRecord] = []
    for item in raw_list:
        if not isinstance(item, dict):
            continue
        item["source_page"] = item.get("source_page", source_page)
        item.setdefault("origin_project", origin_project)
        item.setdefault("origin_client", origin_client)
        name = item.get("name") or "unknown-agent"
        version = item.get("version") or "1.0"
        agent_id = slugify(name)
        if version and version != "1.0":
            agent_id = f"{agent_id}-v{version.replace('.', '-')}"

        record = AgentRecord(
            id=agent_id,
            name=name,
            version=version,
            category=item["category"],
            function_summary=item.get("function_summary") or "",
            inputs=item.get("inputs") or [],
            outputs=item.get("outputs") or [],
            model_used=item.get("model_used") or "Unknown",
            tech_stack=item.get("tech_stack") or [],
            integrations=item.get("integrations") or [],
            origin_project=item.get("origin_project") or origin_project,
            origin_client=item.get("origin_client") or origin_client,
            vertical=normalize_vertical(item.get("vertical")),
            status=item.get("status") or "available",
            typical_accuracy=item.get("typical_accuracy"),
            notes=item.get("notes"),
            source_page=int(item["source_page"]),
        )
        agents.append(record)
    return agents


def extract_project_and_agents(
    chunk: ProjectChunk,
    settings: Settings,
    client: AzureOpenAI | None = None,
) -> ExtractionOutput:
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
        client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )

    errors: list[str] = []
    chunk_id = f"pages-{chunk.estimated_start_page}-{chunk.estimated_end_page}"
    project_prompt = _load_prompt("project_extraction.txt")
    agent_prompt = _load_prompt("agent_extraction.txt")

    project: ProjectRecord | None = None
    agents: list[AgentRecord] = []

    user_project = (
        f"Extract the ProjectRecord from this text. "
        f"Source page: {chunk.estimated_start_page}\n\n"
        f"TEXT:\n{chunk.raw_text}"
    )

    raw_project_response = ""
    try:
        raw_project_response = _call_llm(client, settings, project_prompt, user_project)
        parsed = json.loads(_strip_json_fences(raw_project_response))
        project = _parse_project(parsed, chunk.estimated_start_page)
    except json.JSONDecodeError as exc:
        msg = f"[{chunk_id}] Project JSON parse error: {exc}"
        logger.error("%s — raw response logged at DEBUG", msg)
        logger.debug("Raw project response: %s", raw_project_response)
        errors.append(msg)
    except ValidationError as exc:
        msg = f"[{chunk_id}] Project validation error: {exc}"
        logger.error(msg)
        errors.append(msg)
    except Exception as exc:
        msg = f"[{chunk_id}] Project extraction failed: {exc}"
        logger.error(msg)
        errors.append(msg)

    project_name = project.name if project else chunk.title or "Unknown Project"
    project_client = project.client if project else ""

    user_agents = (
        f"Project name: {project_name}\n"
        f"Client: {project_client}\n\n"
        f"Extract all AgentRecords from this text. "
        f"Source page: {chunk.estimated_start_page}\n\n"
        f"TEXT:\n{chunk.raw_text}"
    )

    try:
        raw_agents = _call_llm(client, settings, agent_prompt, user_agents)
        parsed_agents = json.loads(_strip_json_fences(raw_agents))
        if not isinstance(parsed_agents, list):
            raise ValueError("Agent extraction must return a JSON array")
        agents = _parse_agents(
            parsed_agents,
            chunk.estimated_start_page,
            project_name,
            project_client,
        )
    except json.JSONDecodeError as exc:
        msg = f"[{chunk_id}] Agent JSON parse error: {exc}"
        logger.error(msg)
        errors.append(msg)
    except ValidationError as exc:
        msg = f"[{chunk_id}] Agent validation error: {exc}"
        logger.error(msg)
        errors.append(msg)
    except Exception as exc:
        msg = f"[{chunk_id}] Agent extraction failed: {exc}"
        logger.error(msg)
        errors.append(msg)

    return ExtractionOutput(project=project, agents=agents, errors=errors)

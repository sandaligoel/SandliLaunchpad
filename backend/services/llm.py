"""Shared Azure OpenAI chat helpers for pipeline and interview services."""

from __future__ import annotations

import logging
import time
from pathlib import Path

from openai import APIError, APITimeoutError, AzureOpenAI, RateLimitError

from config import Settings

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
MAX_RETRIES = 3
BACKOFF_SECONDS = (2, 4, 8)


def load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts directory."""
    text = (PROMPTS_DIR / filename).read_text(encoding="utf-8")
    return _expand_prompt_includes(text)


def _expand_prompt_includes(text: str, *, _depth: int = 0) -> str:
    """Inline {{partial.txt}} includes (one level, no recursion into partials)."""
    if _depth > 2:
        return text
    import re

    pattern = re.compile(r"\{\{([a-zA-Z0-9_.-]+\.txt)\}\}")

    def _replace(match: re.Match[str]) -> str:
        include_name = match.group(1)
        include_path = PROMPTS_DIR / include_name
        if not include_path.is_file():
            logger.warning("Prompt include not found: %s", include_name)
            return match.group(0)
        return include_path.read_text(encoding="utf-8").strip()

    expanded = pattern.sub(_replace, text)
    if pattern.search(expanded):
        return _expand_prompt_includes(expanded, _depth=_depth + 1)
    return expanded


def strip_json_fences(text: str) -> str:
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


def call_llm(
    client: AzureOpenAI,
    settings: Settings,
    system_prompt: str,
    user_message: str,
    *,
    temperature: float = 0.1,
    json_mode: bool = False,
) -> str:
    """
    Call Azure OpenAI chat completion with retry and exponential backoff.

    Raises the last exception after MAX_RETRIES failures.
    """
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            kwargs: dict = {
                "model": settings.azure_openai_chat_deployment,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                "temperature": temperature,
            }
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
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


def make_client(settings: Settings) -> AzureOpenAI:
    """Build an Azure OpenAI client from settings."""
    return AzureOpenAI(
        azure_endpoint=settings.azure_openai_endpoint,
        api_key=settings.azure_openai_api_key,
        api_version=settings.azure_openai_api_version,
    )

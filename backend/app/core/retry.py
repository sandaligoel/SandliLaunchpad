"""Shared retry policies for external service calls."""

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from backend.app.core.config import get_settings


def llm_retry():
    settings = get_settings()
    return retry(
        stop=stop_after_attempt(settings.extraction_max_retries),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        retry=retry_if_exception_type((Exception,)),
        reraise=True,
    )


def embedding_retry():
    settings = get_settings()
    return retry(
        stop=stop_after_attempt(settings.extraction_max_retries),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )


def search_retry():
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=15),
        reraise=True,
    )

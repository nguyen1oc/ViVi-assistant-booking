"""Runtime configuration for third-party AI observability."""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

from langsmith import traceable

from src.agents.trace import redact
from src.config import Settings


def configure_langsmith(settings: Settings) -> bool:
    """Expose validated settings as LangSmith's canonical environment variables.

    LangChain/LangGraph discover LangSmith through environment variables. Pydantic
    reads ``.env`` without exporting it to ``os.environ``, so this bridge is
    required for local runs; Docker already receives the same values via env_file.
    """
    logger = logging.getLogger("observability.langsmith")
    if not settings.langsmith_tracing:
        os.environ["LANGSMITH_TRACING"] = "false"
        logger.info("LangSmith tracing is disabled")
        return False
    if not settings.langsmith_api_key:
        logger.warning("LangSmith tracing requested but LANGSMITH_API_KEY is not configured")
        return False

    values = {
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_API_KEY": settings.langsmith_api_key,
        "LANGSMITH_PROJECT": settings.langsmith_project,
        "LANGSMITH_EVENT_LOGS": "true" if settings.langsmith_event_logs else "false",
    }
    if settings.langsmith_endpoint:
        values["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    if settings.langsmith_workspace_id:
        values["LANGSMITH_WORKSPACE_ID"] = settings.langsmith_workspace_id
    os.environ.update(values)
    logger.info(
        "LangSmith tracing enabled project=%s endpoint=%s",
        settings.langsmith_project,
        settings.langsmith_endpoint or "https://api.smith.langchain.com",
    )
    return True


def trace_backend_operation(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Create a redacted child span for a service call made by an AI tool."""
    return traceable(
        name=name,
        run_type="chain",
        process_inputs=redact,
        process_outputs=redact,
    )

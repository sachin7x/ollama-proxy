"""Retry + fallback orchestration for provider calls.

Triggers fallback on:
- HTTP 429, 500-599 from upstream
- Connection / timeout errors
- Any exception flagged as transient (configurable list)

Per-provider config in PROVIDER_SETTINGS:
  retries: int     — number of retry attempts before falling back (default 0)
  fallback: str    — model string to use as fallback (e.g. "openai/gpt-4o-mini")
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable

logger = logging.getLogger("ollama-proxy.retry")

# Status codes considered retryable / fallback-triggering
TRANSIENT_STATUS = {429, 500, 502, 503, 504}


def _is_transient(exc: BaseException) -> bool:
    """Best-effort check whether an exception should trigger retry/fallback."""
    # OpenAI SDK status-bearing errors
    status = getattr(exc, "status_code", None)
    if isinstance(status, int) and status in TRANSIENT_STATUS:
        return True
    # boto3 / botocore error metadata
    resp = getattr(exc, "response", None)
    if isinstance(resp, dict):
        meta_status = resp.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if isinstance(meta_status, int) and meta_status in TRANSIENT_STATUS:
            return True
    # Common transient error class names
    name = type(exc).__name__
    if name in {
        "APIConnectionError", "APITimeoutError", "RateLimitError",
        "InternalServerError", "ServiceUnavailableError",
        "ConnectError", "ConnectTimeout", "ReadTimeout",
        "ThrottlingException", "ServiceUnavailableException",
    }:
        return True
    return False


async def with_retry_and_fallback(
    primary_model: str,
    primary_call: Callable[[], Awaitable[Any]],
    *,
    settings: dict[str, dict[str, Any]],
    fallback_call_factory: Callable[[str], Callable[[], Awaitable[Any]]] | None = None,
) -> Any:
    """Run `primary_call`. On transient failure, retry per provider config and
    optionally fall back to a different model (constructed via factory).

    `fallback_call_factory(model_str)` returns a no-arg coroutine factory for
    the fallback model. If None, no fallback is attempted.
    """
    prefix = primary_model.split("/", 1)[0].lower() if "/" in primary_model else ""
    cfg = settings.get(prefix, {})
    retries = int(cfg.get("retries", 0))
    fallback_model: str | None = cfg.get("fallback") or None

    last_exc: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            return await primary_call()
        except Exception as e:
            last_exc = e
            if not _is_transient(e):
                raise
            if attempt < retries:
                delay = min(2 ** attempt, 10)  # exponential backoff, capped at 10s
                logger.warning(
                    f"transient error from {prefix} (attempt {attempt + 1}/{retries + 1}): "
                    f"{type(e).__name__}: {e}. retrying in {delay}s"
                )
                await asyncio.sleep(delay)
            else:
                logger.warning(
                    f"transient error from {prefix} after {retries + 1} attempts: "
                    f"{type(e).__name__}: {e}"
                )

    # All retries exhausted — try fallback
    if fallback_model and fallback_call_factory:
        logger.warning(f"falling back from {primary_model} to {fallback_model}")
        try:
            return await fallback_call_factory(fallback_model)()
        except Exception as fb_exc:
            logger.error(f"fallback {fallback_model} also failed: {fb_exc}")
            raise

    assert last_exc is not None
    raise last_exc

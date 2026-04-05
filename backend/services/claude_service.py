"""
Auditex -- Claude service.
Thin wrapper around the Anthropic SDK.

Responsibilities:
  - Reads API key and model from settings
  - Handles rate-limit retry (429) with exponential backoff
  - Enforces a 30-second request timeout
  - Logs token usage per call
  - Returns the raw Anthropic Message object to callers

This service has NO knowledge of task types or prompt construction.
That belongs in claude_executor.py.
"""
from __future__ import annotations

import asyncio
import logging
import time

import anthropic

from app.config import settings

logger = logging.getLogger(__name__)

# Maximum number of retry attempts on rate-limit (429) or transient server errors
_MAX_RETRIES = 3
# Base backoff in seconds -- doubles each attempt: 1s, 2s, 4s
_BACKOFF_BASE = 1.0
# Hard timeout per API call in seconds
_TIMEOUT_SECONDS = 30.0


class ClaudeServiceError(Exception):
    """Raised when the Claude API call fails after all retries."""


async def call_claude(
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 1024,
) -> anthropic.types.Message:
    """
    Call the Claude API with retry on 429 and timeout enforcement.

    Args:
        system_prompt: The system prompt defining Claude's role and output schema.
        user_message:  The user-turn message containing the task payload.
        max_tokens:    Maximum tokens in the response (default 1024).

    Returns:
        anthropic.types.Message -- the raw API response object.

    Raises:
        ClaudeServiceError -- if the call fails after _MAX_RETRIES attempts.
    """
    client = anthropic.AsyncAnthropic(
        api_key=settings.ANTHROPIC_API_KEY,
        timeout=_TIMEOUT_SECONDS,
    )

    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            t_start = time.monotonic()
            message = await client.messages.create(
                model=settings.CLAUDE_MODEL,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
            elapsed = time.monotonic() - t_start

            # Log token usage for cost tracking
            logger.info(
                "Claude call succeeded | attempt=%d elapsed=%.2fs "
                "input_tokens=%d output_tokens=%d model=%s",
                attempt,
                elapsed,
                message.usage.input_tokens,
                message.usage.output_tokens,
                message.model,
            )
            return message

        except anthropic.RateLimitError as exc:
            last_error = exc
            backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning(
                "Claude rate limit (429) | attempt=%d/%d backoff=%.1fs",
                attempt,
                _MAX_RETRIES,
                backoff,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(backoff)

        except anthropic.APITimeoutError as exc:
            last_error = exc
            backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning(
                "Claude timeout | attempt=%d/%d backoff=%.1fs",
                attempt,
                _MAX_RETRIES,
                backoff,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(backoff)

        except anthropic.APIStatusError as exc:
            # 5xx server errors -- retry
            if exc.status_code >= 500:
                last_error = exc
                backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    "Claude server error %d | attempt=%d/%d backoff=%.1fs",
                    exc.status_code,
                    attempt,
                    _MAX_RETRIES,
                    backoff,
                )
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(backoff)
            else:
                # 4xx client errors (except 429) -- do not retry
                logger.error(
                    "Claude client error %d: %s", exc.status_code, str(exc)
                )
                raise ClaudeServiceError(
                    f"Claude API client error {exc.status_code}: {exc}"
                ) from exc

        except Exception as exc:
            logger.error("Claude unexpected error: %s", str(exc))
            raise ClaudeServiceError(f"Claude unexpected error: {exc}") from exc

    raise ClaudeServiceError(
        f"Claude API failed after {_MAX_RETRIES} attempts. Last error: {last_error}"
    )

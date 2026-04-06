"""
Auditex -- OpenAI service.
Thin wrapper around the OpenAI SDK.

Fix (Phase 7): Added asyncio.wait_for() hard wall-clock timeout around the
entire API call. The openai SDK timeout= parameter only covers connection
establishment, not response streaming. Without wait_for(), a slow GPT-4o
response hangs the Celery worker indefinitely (confirmed: task stuck 39 min).
"""
from __future__ import annotations

import asyncio
import logging
import time

import openai

from app.config import settings

logger = logging.getLogger(__name__)

_MAX_RETRIES    = 3
_BACKOFF_BASE   = 1.0
_TIMEOUT_SECONDS = 45.0   # hard wall-clock limit per attempt (asyncio.wait_for)


class OpenAIServiceError(Exception):
    """Raised when the OpenAI API call fails after all retries."""


async def _call_once(client: openai.AsyncOpenAI, system_prompt: str, user_message: str, max_tokens: int) -> openai.types.chat.ChatCompletion:
    """Single attempt — wrapped by wait_for in the caller."""
    return await client.chat.completions.create(
        model=settings.GPT4O_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        response_format={"type": "json_object"},
    )


async def call_openai(
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 512,
) -> openai.types.chat.ChatCompletion:
    """
    Call OpenAI Chat Completions with hard asyncio timeout + retry on 429/5xx.

    The asyncio.wait_for() enforces a true wall-clock timeout that catches
    slow responses the SDK timeout= parameter misses.
    """
    client = openai.AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=_TIMEOUT_SECONDS,
    )

    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            t_start = time.monotonic()

            # Hard wall-clock timeout — catches slow responses the SDK misses
            completion = await asyncio.wait_for(
                _call_once(client, system_prompt, user_message, max_tokens),
                timeout=_TIMEOUT_SECONDS,
            )

            elapsed = time.monotonic() - t_start
            usage = completion.usage
            logger.info(
                "OpenAI call succeeded | attempt=%d elapsed=%.2fs "
                "input=%d output=%d model=%s",
                attempt, elapsed,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
                completion.model,
            )
            return completion

        except asyncio.TimeoutError as exc:
            last_error = exc
            logger.warning(
                "OpenAI hard timeout (%ss) | attempt=%d/%d",
                _TIMEOUT_SECONDS, attempt, _MAX_RETRIES,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))

        except openai.RateLimitError as exc:
            last_error = exc
            backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning("OpenAI rate limit (429) | attempt=%d/%d backoff=%.1fs", attempt, _MAX_RETRIES, backoff)
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(backoff)

        except openai.APITimeoutError as exc:
            last_error = exc
            backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning("OpenAI SDK timeout | attempt=%d/%d backoff=%.1fs", attempt, _MAX_RETRIES, backoff)
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(backoff)

        except openai.APIStatusError as exc:
            if exc.status_code >= 500:
                last_error = exc
                backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning("OpenAI server error %d | attempt=%d/%d", exc.status_code, attempt, _MAX_RETRIES)
                if attempt < _MAX_RETRIES:
                    await asyncio.sleep(backoff)
            else:
                logger.error("OpenAI client error %d: %s", exc.status_code, str(exc))
                raise OpenAIServiceError(f"OpenAI client error {exc.status_code}: {exc}") from exc

        except Exception as exc:
            logger.error("OpenAI unexpected error: %s", str(exc))
            raise OpenAIServiceError(f"OpenAI unexpected error: {exc}") from exc

    raise OpenAIServiceError(
        f"OpenAI failed after {_MAX_RETRIES} attempts. Last: {last_error}"
    )

"""
Auditex -- OpenAI service.
Thin wrapper around the OpenAI SDK.  Mirrors the pattern of claude_service.py.

Responsibilities:
  - Reads API key and model from settings
  - Handles rate-limit retry (429) with exponential backoff (1s / 2s / 4s)
  - Enforces a 30-second request timeout
  - Logs token usage per call
  - Returns the raw OpenAI ChatCompletion object to callers

This service has NO knowledge of task types, prompt construction, or review logic.
That belongs in gpt4o_reviewer.py.
"""
from __future__ import annotations

import asyncio
import logging
import time

import openai

from app.config import settings

logger = logging.getLogger(__name__)

# Maximum number of retry attempts on rate-limit (429) or transient server errors
_MAX_RETRIES = 3
# Base backoff in seconds -- doubles each attempt: 1s, 2s, 4s
_BACKOFF_BASE = 1.0
# Hard timeout per API call in seconds
_TIMEOUT_SECONDS = 30.0


class OpenAIServiceError(Exception):
    """Raised when the OpenAI API call fails after all retries."""


async def call_openai(
    *,
    system_prompt: str,
    user_message: str,
    max_tokens: int = 512,
) -> openai.types.chat.ChatCompletion:
    """
    Call the OpenAI Chat Completions API with retry on 429 / 5xx and timeout.

    Args:
        system_prompt: The system prompt defining the reviewer's role.
        user_message:  The user-turn message containing the content to review.
        max_tokens:    Maximum tokens in the response (default 512 -- reviews are short).

    Returns:
        openai.types.chat.ChatCompletion -- the raw API response object.

    Raises:
        OpenAIServiceError -- if the call fails after _MAX_RETRIES attempts.
    """
    client = openai.AsyncOpenAI(
        api_key=settings.OPENAI_API_KEY,
        timeout=_TIMEOUT_SECONDS,
    )

    last_error: Exception | None = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            t_start = time.monotonic()
            completion = await client.chat.completions.create(
                model=settings.GPT4O_MODEL,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},  # enforce JSON output
            )
            elapsed = time.monotonic() - t_start

            # Log token usage for cost tracking
            usage = completion.usage
            logger.info(
                "OpenAI call succeeded | attempt=%d elapsed=%.2fs "
                "input_tokens=%d output_tokens=%d model=%s",
                attempt,
                elapsed,
                usage.prompt_tokens if usage else 0,
                usage.completion_tokens if usage else 0,
                completion.model,
            )
            return completion

        except openai.RateLimitError as exc:
            last_error = exc
            backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning(
                "OpenAI rate limit (429) | attempt=%d/%d backoff=%.1fs",
                attempt,
                _MAX_RETRIES,
                backoff,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(backoff)

        except openai.APITimeoutError as exc:
            last_error = exc
            backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
            logger.warning(
                "OpenAI timeout | attempt=%d/%d backoff=%.1fs",
                attempt,
                _MAX_RETRIES,
                backoff,
            )
            if attempt < _MAX_RETRIES:
                await asyncio.sleep(backoff)

        except openai.APIStatusError as exc:
            # 5xx server errors -- retry
            if exc.status_code >= 500:
                last_error = exc
                backoff = _BACKOFF_BASE * (2 ** (attempt - 1))
                logger.warning(
                    "OpenAI server error %d | attempt=%d/%d backoff=%.1fs",
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
                    "OpenAI client error %d: %s", exc.status_code, str(exc)
                )
                raise OpenAIServiceError(
                    f"OpenAI API client error {exc.status_code}: {exc}"
                ) from exc

        except Exception as exc:
            logger.error("OpenAI unexpected error: %s", str(exc))
            raise OpenAIServiceError(f"OpenAI unexpected error: {exc}") from exc

    raise OpenAIServiceError(
        f"OpenAI API failed after {_MAX_RETRIES} attempts. Last error: {last_error}"
    )

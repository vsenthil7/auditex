"""Tests for services.openai_service: retry + timeout + error branches."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.openai_service import OpenAIServiceError, call_openai


def _make_completion():
    c = MagicMock()
    c.choices = [MagicMock(message=MagicMock(content='{"verdict": "APPROVE"}'))]
    c.model = "gpt-4o"
    c.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
    return c


@pytest.mark.asyncio
async def test_call_openai_success():
    comp = _make_completion()
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(return_value=comp)
    with patch("openai.AsyncOpenAI", return_value=fake_client):
        out = await call_openai(system_prompt="s", user_message="u")
    assert out is comp


@pytest.mark.asyncio
async def test_call_openai_timeout_then_success():
    comp = _make_completion()
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(
        side_effect=[asyncio.TimeoutError(), comp]
    )
    with patch("openai.AsyncOpenAI", return_value=fake_client), \
         patch("asyncio.sleep", AsyncMock()):
        out = await call_openai(system_prompt="s", user_message="u")
    assert out is comp


@pytest.mark.asyncio
async def test_call_openai_rate_limit_then_success():
    import openai as real_openai
    comp = _make_completion()
    fake_client = MagicMock()
    fake_err = real_openai.RateLimitError(
        message="429", response=MagicMock(status_code=429, request=MagicMock()),
        body=None,
    )
    fake_client.chat.completions.create = AsyncMock(side_effect=[fake_err, comp])
    with patch("openai.AsyncOpenAI", return_value=fake_client), \
         patch("asyncio.sleep", AsyncMock()):
        out = await call_openai(system_prompt="s", user_message="u")
    assert out is comp


@pytest.mark.asyncio
async def test_call_openai_sdk_timeout_then_success():
    import openai as real_openai
    comp = _make_completion()
    fake_client = MagicMock()
    fake_err = real_openai.APITimeoutError(request=MagicMock())
    fake_client.chat.completions.create = AsyncMock(side_effect=[fake_err, comp])
    with patch("openai.AsyncOpenAI", return_value=fake_client), \
         patch("asyncio.sleep", AsyncMock()):
        out = await call_openai(system_prompt="s", user_message="u")
    assert out is comp


@pytest.mark.asyncio
async def test_call_openai_server_error_then_success():
    import openai as real_openai
    comp = _make_completion()
    fake_client = MagicMock()
    fake_err = real_openai.APIStatusError(
        message="srv", response=MagicMock(status_code=500, request=MagicMock()),
        body={},
    )
    fake_client.chat.completions.create = AsyncMock(side_effect=[fake_err, comp])
    with patch("openai.AsyncOpenAI", return_value=fake_client), \
         patch("asyncio.sleep", AsyncMock()):
        out = await call_openai(system_prompt="s", user_message="u")
    assert out is comp


@pytest.mark.asyncio
async def test_call_openai_4xx_client_error_raises():
    import openai as real_openai
    fake_client = MagicMock()
    fake_err = real_openai.APIStatusError(
        message="bad", response=MagicMock(status_code=400, request=MagicMock()),
        body={},
    )
    fake_client.chat.completions.create = AsyncMock(side_effect=fake_err)
    with patch("openai.AsyncOpenAI", return_value=fake_client):
        with pytest.raises(OpenAIServiceError):
            await call_openai(system_prompt="s", user_message="u")


@pytest.mark.asyncio
async def test_call_openai_unexpected_error_raises():
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("openai.AsyncOpenAI", return_value=fake_client):
        with pytest.raises(OpenAIServiceError):
            await call_openai(system_prompt="s", user_message="u")


@pytest.mark.asyncio
async def test_call_openai_all_retries_exhausted():
    fake_client = MagicMock()
    fake_client.chat.completions.create = AsyncMock(side_effect=asyncio.TimeoutError())
    with patch("openai.AsyncOpenAI", return_value=fake_client), \
         patch("asyncio.sleep", AsyncMock()):
        with pytest.raises(OpenAIServiceError):
            await call_openai(system_prompt="s", user_message="u")


def test_openai_service_error_is_exception():
    assert issubclass(OpenAIServiceError, Exception)

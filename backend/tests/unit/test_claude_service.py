"""Tests for services.claude_service: retry + error branches."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services import claude_service
from services.claude_service import ClaudeServiceError, call_claude


def _make_message():
    m = MagicMock()
    m.content = [MagicMock(text="ok")]
    m.model = "claude-sonnet-4-6"
    m.usage.input_tokens = 10
    m.usage.output_tokens = 5
    return m


@pytest.mark.asyncio
async def test_call_claude_success_first_attempt():
    msg = _make_message()
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(return_value=msg)
    with patch("anthropic.AsyncAnthropic", return_value=fake_client):
        out = await call_claude(system_prompt="s", user_message="u")
    assert out is msg


@pytest.mark.asyncio
async def test_call_claude_rate_limit_then_success():
    import anthropic as real_anthropic
    msg = _make_message()
    fake_client = MagicMock()
    fake_err = real_anthropic.RateLimitError(
        message="429", response=MagicMock(status_code=429), body=None,
    )
    fake_client.messages.create = AsyncMock(side_effect=[fake_err, msg])
    with patch("anthropic.AsyncAnthropic", return_value=fake_client), \
         patch("asyncio.sleep", AsyncMock()):
        out = await call_claude(system_prompt="s", user_message="u")
    assert out is msg


@pytest.mark.asyncio
async def test_call_claude_timeout_then_success():
    import anthropic as real_anthropic
    msg = _make_message()
    fake_client = MagicMock()
    fake_err = real_anthropic.APITimeoutError(request=MagicMock())
    fake_client.messages.create = AsyncMock(side_effect=[fake_err, msg])
    with patch("anthropic.AsyncAnthropic", return_value=fake_client), \
         patch("asyncio.sleep", AsyncMock()):
        out = await call_claude(system_prompt="s", user_message="u")
    assert out is msg


@pytest.mark.asyncio
async def test_call_claude_server_error_then_success():
    import anthropic as real_anthropic
    msg = _make_message()
    fake_client = MagicMock()
    resp = MagicMock(status_code=503)
    fake_err = real_anthropic.APIStatusError(
        message="srv", response=resp, body={},
    )
    fake_client.messages.create = AsyncMock(side_effect=[fake_err, msg])
    with patch("anthropic.AsyncAnthropic", return_value=fake_client), \
         patch("asyncio.sleep", AsyncMock()):
        out = await call_claude(system_prompt="s", user_message="u")
    assert out is msg


@pytest.mark.asyncio
async def test_call_claude_4xx_client_error_raises_immediately():
    import anthropic as real_anthropic
    fake_client = MagicMock()
    resp = MagicMock(status_code=400)
    fake_err = real_anthropic.APIStatusError(
        message="bad", response=resp, body={},
    )
    fake_client.messages.create = AsyncMock(side_effect=fake_err)
    with patch("anthropic.AsyncAnthropic", return_value=fake_client):
        with pytest.raises(ClaudeServiceError):
            await call_claude(system_prompt="s", user_message="u")


@pytest.mark.asyncio
async def test_call_claude_unexpected_exception_raises():
    fake_client = MagicMock()
    fake_client.messages.create = AsyncMock(side_effect=RuntimeError("boom"))
    with patch("anthropic.AsyncAnthropic", return_value=fake_client):
        with pytest.raises(ClaudeServiceError):
            await call_claude(system_prompt="s", user_message="u")


@pytest.mark.asyncio
async def test_call_claude_all_retries_exhausted():
    import anthropic as real_anthropic
    fake_client = MagicMock()
    fake_err = real_anthropic.RateLimitError(
        message="429", response=MagicMock(status_code=429), body=None,
    )
    fake_client.messages.create = AsyncMock(side_effect=fake_err)
    with patch("anthropic.AsyncAnthropic", return_value=fake_client), \
         patch("asyncio.sleep", AsyncMock()):
        with pytest.raises(ClaudeServiceError):
            await call_claude(system_prompt="s", user_message="u")


def test_claude_service_error_is_exception():
    assert issubclass(ClaudeServiceError, Exception)

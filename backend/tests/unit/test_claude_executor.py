"""Tests for core.execution.claude_executor."""
from __future__ import annotations

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.execution import claude_executor
from core.execution.claude_executor import (
    ExecutorResult,
    _build_user_message,
    _extract_json,
    _get_system_prompt,
    execute_task,
)


def test_get_system_prompt_known_types():
    assert "financial compliance" in _get_system_prompt("document_review")
    assert "risk analyst" in _get_system_prompt("risk_analysis")
    assert "contract compliance" in _get_system_prompt("contract_check")


def test_get_system_prompt_unknown_defaults_to_document_review():
    assert _get_system_prompt("unknown_type") == _get_system_prompt("document_review")


def test_build_user_message():
    msg = _build_user_message("document_review", {"foo": "bar"})
    assert "document_review" in msg
    assert "foo" in msg
    assert "bar" in msg


def test_extract_json_plain():
    assert _extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_fences():
    raw = "```json\n{\"a\": 1}\n```"
    assert _extract_json(raw) == {"a": 1}


def test_extract_json_with_only_opening_fence():
    raw = "```\n{\"a\": 2}"
    assert _extract_json(raw) == {"a": 2}


def test_extract_json_invalid_raises():
    with pytest.raises(ValueError):
        _extract_json("not a json")


@pytest.mark.asyncio
async def test_execute_task_success():
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text=json.dumps({
        "completeness": 0.9,
        "missing_fields": [],
        "recommendation": "APPROVE",
        "reasoning": "ok",
        "confidence": 0.85,
    }))]
    fake_msg.model = "claude-sonnet-4-6"
    fake_msg.usage.input_tokens = 100
    fake_msg.usage.output_tokens = 50

    with patch("core.execution.claude_executor.call_claude", AsyncMock(return_value=fake_msg)):
        result = await execute_task(
            task_id=uuid.uuid4(),
            task_type="document_review",
            payload={"a": 1},
        )
    assert isinstance(result, ExecutorResult)
    assert result.confidence == 0.85
    assert result.tokens_used == 150
    assert result.output["recommendation"] == "APPROVE"


@pytest.mark.asyncio
async def test_execute_task_bad_json_raises():
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text="not json at all")]
    fake_msg.model = "claude"
    fake_msg.usage.input_tokens = 1
    fake_msg.usage.output_tokens = 1

    with patch("core.execution.claude_executor.call_claude", AsyncMock(return_value=fake_msg)):
        with pytest.raises(ValueError):
            await execute_task(uuid.uuid4(), "document_review", {})


@pytest.mark.asyncio
async def test_execute_task_schema_validation_fails():
    fake_msg = MagicMock()
    fake_msg.content = [MagicMock(text=json.dumps({
        "completeness": 0.9,
        "missing_fields": [],
        "recommendation": "NOT_A_REAL_REC",
        "reasoning": "ok",
        "confidence": 0.85,
    }))]
    fake_msg.model = "claude"
    fake_msg.usage.input_tokens = 1
    fake_msg.usage.output_tokens = 1

    with patch("core.execution.claude_executor.call_claude", AsyncMock(return_value=fake_msg)):
        with pytest.raises(ValueError):
            await execute_task(uuid.uuid4(), "document_review", {})


@pytest.mark.asyncio
async def test_execute_task_empty_content():
    fake_msg = MagicMock()
    fake_msg.content = []
    fake_msg.model = "claude"
    fake_msg.usage.input_tokens = 1
    fake_msg.usage.output_tokens = 1

    with patch("core.execution.claude_executor.call_claude", AsyncMock(return_value=fake_msg)):
        with pytest.raises(ValueError):
            await execute_task(uuid.uuid4(), "document_review", {})

"""
Auditex -- pytest shared fixtures and configuration.

All fixtures are designed for unit tests that never touch the real database.
Sessions are AsyncMock objects; external service calls (Anthropic, OpenAI,
Redis, paho-mqtt) are patched at the call site.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Ensure backend root is on sys.path so imports like "app.config" resolve
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(_BACKEND_ROOT) not in sys.path:  # pragma: no cover -- exercised indirectly
    sys.path.insert(0, str(_BACKEND_ROOT))

# --- Env setup: force stub mode so no real network calls happen -------------
os.environ.setdefault("USE_REAL_VERTEX", "false")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-anthropic")
os.environ.setdefault("OPENAI_API_KEY", "test-key-openai")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://t:t@localhost:5432/t")
os.environ.setdefault("FOXMQ_BROKER_URL", "mqtt://localhost:1883")


# ---------------------------------------------------------------------------
# Session fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def mock_async_session():
    """
    AsyncMock-backed AsyncSession that records add/flush/refresh/commit/rollback/close.
    .execute() returns a result with scalar_one_or_none() / scalars().all() / scalar_one()
    preconfigured to return None by default. Tests override per-call.
    """
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()

    result_mock = MagicMock()
    result_mock.scalar_one_or_none = MagicMock(return_value=None)
    result_mock.scalar_one = MagicMock(return_value=0)
    scalars_mock = MagicMock()
    scalars_mock.all = MagicMock(return_value=[])
    result_mock.scalars = MagicMock(return_value=scalars_mock)
    result_mock.fetchall = MagicMock(return_value=[])

    session.execute = AsyncMock(return_value=result_mock)
    session._result = result_mock  # tests can tweak returns on this
    session._scalars = scalars_mock
    return session


# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_task_id():
    return uuid.uuid4()


@pytest.fixture
def sample_agent_id():
    return uuid.uuid4()


@pytest.fixture
def sample_executor_output():
    return {
        "completeness": 0.9,
        "missing_fields": [],
        "recommendation": "APPROVE",
        "reasoning": "All fields present and values within policy bounds.",
        "confidence": 0.85,
    }


@pytest.fixture
def sample_risk_output():
    return {
        "risk_level": "LOW",
        "risk_factors": ["stable income"],
        "recommendation": "APPROVE",
        "reasoning": "Healthy DSCR and strong balance sheet.",
        "confidence": 0.88,
    }


@pytest.fixture
def sample_contract_output():
    return {
        "compliance_status": "COMPLIANT",
        "issues": [],
        "recommendation": "APPROVE",
        "reasoning": "All Article 28 clauses satisfied.",
        "confidence": 0.9,
    }


@pytest.fixture
def sample_task(sample_task_id):
    """A Task-ORM-like MagicMock suitable for most code paths."""
    task = MagicMock()
    task.id = sample_task_id
    task.task_type = "document_review"
    task.status = "COMPLETED"
    task.workflow_id = None
    task.submitted_by = None
    task.api_key_id = None
    task.payload_json = json.dumps({"payload": {"foo": "bar"}})
    task.executor_output_json = json.dumps({
        "model": "claude-sonnet-4-6",
        "output": {
            "recommendation": "APPROVE",
            "reasoning": "Looks good.",
            "confidence": 0.9,
        },
        "confidence": 0.9,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    task.review_result_json = json.dumps({
        "consensus": "3_OF_3_APPROVE",
        "reviewers": [
            {"model": "gpt-4o", "verdict": "APPROVE", "confidence": 0.9, "commitment_verified": True},
            {"model": "gpt-4o", "verdict": "APPROVE", "confidence": 0.88, "commitment_verified": True},
            {"model": "claude-sonnet-4-6", "verdict": "APPROVE", "confidence": 0.85, "commitment_verified": True},
        ],
        "completed_at": datetime.now(timezone.utc).isoformat(),
    })
    task.consensus_result = "3_OF_3_APPROVE"
    task.vertex_event_hash = "a" * 64
    task.vertex_round = 1
    # Use MagicMock for datetime fields so tests can override .isoformat() freely
    task.vertex_finalised_at = MagicMock()
    task.vertex_finalised_at.isoformat = MagicMock(return_value="2026-04-21T01:00:00+00:00")
    task.created_at = MagicMock()
    task.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00+00:00")
    task.executor_confidence = 0.9
    task.retry_count = 0
    task.report_available = True
    return task


@pytest.fixture
def sample_report():
    report = MagicMock()
    report.id = uuid.uuid4()
    report.task_id = uuid.uuid4()
    report.narrative = "Sample narrative."
    report.eu_ai_act_json = json.dumps({
        "article_9_risk_management": {"risk_assessment": "LOW"},
        "article_13_transparency": {"decision_made": "APPROVE"},
        "article_17_quality_management": {"all_commitments_verified": True},
    })
    report.schema_version = "poc_report_v1"
    report.vertex_event_hash = "b" * 64
    report.generated_at = MagicMock()
    report.generated_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00+00:00")
    report.generator_model = "claude-sonnet-4-6"
    return report


@pytest.fixture
def sample_agent(sample_agent_id):
    agent = MagicMock()
    agent.id = sample_agent_id
    agent.name = "Test Agent"
    agent.agent_type = "claude"
    agent.model_version = "claude-sonnet-4-6"
    agent.public_key = None
    agent.is_active = True
    agent.capabilities = json.dumps(["document_review"])
    agent.created_at = MagicMock()
    agent.created_at.isoformat = MagicMock(return_value="2026-04-21T00:00:00+00:00")
    return agent

"""Tests for db.models ORM classes (import + repr)."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from db.models import Agent, AuditEvent, Base, Report, Task
from db.models.base import TimestampMixin, UUIDPrimaryKeyMixin, utcnow


def test_utcnow_returns_utc_aware_datetime():
    dt = utcnow()
    assert isinstance(dt, datetime)
    assert dt.tzinfo is not None


def test_base_is_declarative():
    # Base is a DeclarativeBase so it has __mapper__ after models import
    assert hasattr(Base, "metadata")


def test_timestamp_mixin_defined():
    assert hasattr(TimestampMixin, "created_at")


def test_uuid_primary_key_mixin_defined():
    assert hasattr(UUIDPrimaryKeyMixin, "id")


def test_task_repr():
    t = Task(task_type="document_review", status="QUEUED", payload_json="{}")
    t.id = uuid.uuid4()
    r = repr(t)
    assert "Task" in r
    assert "document_review" in r
    assert "QUEUED" in r


def test_agent_repr():
    a = Agent(name="x", agent_type="claude")
    a.id = uuid.uuid4()
    r = repr(a)
    assert "Agent" in r
    assert "claude" in r


def test_audit_event_repr():
    e = AuditEvent(event_type="task_submitted", payload_json="{}")
    e.id = uuid.uuid4()
    r = repr(e)
    assert "AuditEvent" in r
    assert "task_submitted" in r


def test_report_repr_unsigned():
    rep = Report(task_id=uuid.uuid4())
    rep.id = uuid.uuid4()
    rep.signed_at = None
    r = repr(rep)
    assert "Report" in r
    assert "signed=False" in r


def test_report_repr_signed():
    rep = Report(task_id=uuid.uuid4())
    rep.id = uuid.uuid4()
    rep.signed_at = datetime.now(timezone.utc)
    r = repr(rep)
    assert "signed=True" in r

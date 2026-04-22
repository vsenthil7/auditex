"""Tests for db.models.dlq_entry.DLQEntry."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from db.models.dlq_entry import DLQEntry


def test_dlq_entry_construction_with_all_fields():
    eid = uuid.uuid4()
    tid = uuid.uuid4()
    now = datetime.now(timezone.utc)
    e = DLQEntry(
        id=eid,
        created_at=now,
        task_id=tid,
        source_queue="execution_queue",
        error_class="ValueError",
        error_message="bad input",
        payload={"a": 1},
        attempt_count=4,
        status="PENDING",
        resolved_at=None,
        resolution_note=None,
    )
    assert e.id == eid
    assert e.task_id == tid
    assert e.source_queue == "execution_queue"
    assert e.attempt_count == 4


def test_dlq_entry_repr_shows_id_source_status():
    e = DLQEntry(
        id=uuid.uuid4(),
        created_at=datetime.now(timezone.utc),
        task_id=None,
        source_queue="q1",
        error_class="E",
        error_message="m",
        payload={},
        attempt_count=0,
        status="PENDING",
    )
    r = repr(e)
    assert "DLQEntry" in r
    assert "q1" in r
    assert "PENDING" in r


def test_dlq_entry_tablename_is_correct():
    assert DLQEntry.__tablename__ == "dlq_entries"

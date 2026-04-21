"""Tests for workers.celery_app."""
from __future__ import annotations

from workers import celery_app


def test_celery_app_importable():
    assert celery_app.celery_app is not None


def test_celery_app_name():
    assert celery_app.celery_app.main == "auditex"


def test_celery_app_queues_present():
    q_names = {q.name for q in celery_app.celery_app.conf.task_queues}
    assert "execution_queue" in q_names
    assert "review_queue" in q_names
    assert "reporting_queue" in q_names
    assert "dlq" in q_names


def test_celery_app_defaults():
    assert celery_app.celery_app.conf.task_default_queue == "execution_queue"
    assert celery_app.celery_app.conf.task_serializer == "json"
    assert celery_app.celery_app.conf.task_acks_late is True
    assert celery_app.celery_app.conf.worker_prefetch_multiplier == 1
    assert celery_app.celery_app.conf.timezone == "UTC"
    assert celery_app.celery_app.conf.enable_utc is True

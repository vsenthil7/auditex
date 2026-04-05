"""
Auditex -- Celery application factory.
Defines the Celery app, queue topology, and serialisation settings.

Queues:
  execution_queue  -- Claude task execution
  review_queue     -- GPT-4o / multi-model review (Phase 4)
  reporting_queue  -- PoC report generation (Phase 6)
  dlq              -- Dead letter queue for permanently failed tasks

Usage:
  celery -A workers.celery_app worker --loglevel=info -Q execution_queue,review_queue,reporting_queue,dlq
"""
from __future__ import annotations

import os

from celery import Celery
from kombu import Exchange, Queue

# ---------------------------------------------------------------------------
# Redis broker URL
# ---------------------------------------------------------------------------
# Read from environment so Docker Compose can inject the correct service URL.
REDIS_URL: str = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Celery app
# ---------------------------------------------------------------------------
celery_app = Celery(
    "auditex",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "workers.execution_worker",
        "workers.reporting_worker",
    ],
)

# ---------------------------------------------------------------------------
# Queue definitions
# ---------------------------------------------------------------------------
default_exchange = Exchange("auditex", type="direct")

celery_app.conf.task_queues = (
    Queue("execution_queue", default_exchange, routing_key="execution"),
    Queue("review_queue", default_exchange, routing_key="review"),
    Queue("reporting_queue", default_exchange, routing_key="reporting"),
    Queue("dlq", default_exchange, routing_key="dlq"),
)
celery_app.conf.task_default_queue = "execution_queue"
celery_app.conf.task_default_exchange = "auditex"
celery_app.conf.task_default_routing_key = "execution"

# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------
celery_app.conf.task_serializer = "json"
celery_app.conf.result_serializer = "json"
celery_app.conf.accept_content = ["json"]

# ---------------------------------------------------------------------------
# Reliability settings
# ---------------------------------------------------------------------------
celery_app.conf.task_acks_late = True           # Ack only after task completes
celery_app.conf.task_reject_on_worker_lost = True  # Requeue if worker dies mid-task
celery_app.conf.worker_prefetch_multiplier = 1  # One task at a time per worker process

# ---------------------------------------------------------------------------
# Result expiry
# ---------------------------------------------------------------------------
celery_app.conf.result_expires = 3600  # 1 hour -- results stored in Redis backend

# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------
celery_app.conf.timezone = "UTC"
celery_app.conf.enable_utc = True

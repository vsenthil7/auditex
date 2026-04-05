"""
Auditex -- Pydantic schemas for Task API.
These are the request/response models for the HTTP layer.
NOT the ORM models (those live in db/models/task.py).

Phase 2: TaskCreate, TaskResponse, TaskStatus for MT-002 and MT-003.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """
    Task lifecycle states -- matches the ORM model exactly.
    String enum so FastAPI serialises as plain string in JSON.
    """
    QUEUED = "QUEUED"
    EXECUTING = "EXECUTING"
    REVIEWING = "REVIEWING"
    FINALISING = "FINALISING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ESCALATED = "ESCALATED"


class TaskCreate(BaseModel):
    """
    Request body for POST /api/v1/tasks.
    Validated by Pydantic before it touches the database.
    """
    task_type: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Type of task: document_review | risk_analysis | contract_check",
        examples=["document_review"],
    )
    payload: dict[str, Any] = Field(
        ...,
        description="Task-specific payload. Contents depend on task_type.",
    )
    metadata: dict[str, Any] | None = Field(
        default=None,
        description="Optional client metadata: submitted_by, workflow_id, etc.",
    )


class TaskResponse(BaseModel):
    """
    Response body for POST /api/v1/tasks (submit) and GET /api/v1/tasks/{id} (poll).
    Minimal at QUEUED status. Enriched as the task progresses.
    """
    task_id: uuid.UUID = Field(..., description="Unique task identifier.")
    status: TaskStatus = Field(..., description="Current lifecycle status.")
    task_type: str = Field(..., description="Task type as submitted.")
    workflow_id: str | None = Field(
        default=None, description="Workflow ID from metadata, if provided."
    )
    created_at: datetime = Field(..., description="UTC timestamp of task creation.")

    # Populated after execution
    executor: dict[str, Any] | None = Field(
        default=None,
        description="Executor details: model, output_hash, confidence. Null until EXECUTING.",
    )

    # Populated after review
    review: dict[str, Any] | None = Field(
        default=None,
        description="Review result: consensus, reviewer verdicts. Null until REVIEWING.",
    )

    # Populated after Vertex finalisation
    vertex: dict[str, Any] | None = Field(
        default=None,
        description="Vertex proof: event_hash, round. Null until FINALISING.",
    )

    # Populated after report generation
    report_available: bool = Field(
        default=False,
        description="True once PoC report has been generated and is available for download.",
    )

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""
    tasks: list[TaskResponse]
    total: int
    page: int
    page_size: int

"""
Auditex -- Task routes.
POST /api/v1/tasks        -- submit task (MT-002)
GET  /api/v1/tasks/{id}   -- poll status (MT-003)
GET  /api/v1/tasks        -- list tasks paginated
All routes require X-API-Key authentication.
"""
from __future__ import annotations

import json
import uuid
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.middleware.auth import require_api_key
from app.models.task import TaskCreate, TaskListResponse, TaskResponse, TaskStatus
from db.connection import get_db_session
from db.repositories import task_repo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["tasks"])


def _orm_to_response(task) -> TaskResponse:
    """
    Convert a Task ORM object to a TaskResponse Pydantic model.
    Handles JSON field deserialisation and nullable fields safely.
    """
    # Parse executor details if present
    executor = None
    if task.executor_output_json:
        try:
            executor = {
                "model": task.executor_agent_id and str(task.executor_agent_id),
                "output": json.loads(task.executor_output_json),
                "confidence": float(task.executor_confidence) if task.executor_confidence else None,
                "completed_at": task.execution_completed_at.isoformat() if task.execution_completed_at else None,
            }
        except Exception:
            executor = {"raw": task.executor_output_json}

    # Parse review result if present
    review = None
    if task.review_result_json:
        try:
            review = json.loads(task.review_result_json)
        except Exception:
            review = {"raw": task.review_result_json}
    if task.consensus_result and review is None:
        review = {"consensus": task.consensus_result}
    elif task.consensus_result and review is not None:
        review["consensus"] = task.consensus_result

    # Vertex proof if present
    vertex = None
    if task.vertex_event_hash:
        vertex = {
            "event_hash": task.vertex_event_hash,
            "round": task.vertex_round,
            "finalised_at": task.vertex_finalised_at.isoformat() if task.vertex_finalised_at else None,
        }

    # Extract workflow_id from metadata if not stored directly
    workflow_id = task.workflow_id

    return TaskResponse(
        task_id=task.id,
        status=TaskStatus(task.status),
        task_type=task.task_type,
        workflow_id=workflow_id,
        created_at=task.created_at,
        executor=executor,
        review=review,
        vertex=vertex,
        report_available=task.report is not None if hasattr(task, "report") else False,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=dict,
    summary="Submit a task for AI execution and compliance recording",
)
async def submit_task(
    body: TaskCreate,
    key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """
    MT-002: Submit a task.
    Expected response: {"task_id": "<uuid>", "status": "QUEUED", "created_at": "<timestamp>"}
    """
    # Extract optional fields from metadata
    submitted_by = None
    workflow_id = None
    if body.metadata:
        submitted_by = body.metadata.get("submitted_by")
        workflow_id = body.metadata.get("workflow_id")

    # Merge payload with metadata for storage
    full_payload = {"payload": body.payload}
    if body.metadata:
        full_payload["metadata"] = body.metadata

    task = await task_repo.create_task(
        session,
        task_type=body.task_type,
        payload=full_payload,
        submitted_by=submitted_by,
        workflow_id=workflow_id,
        api_key_id=key_meta.get("key_id"),
    )

    logger.info("Task created: %s type=%s by=%s", task.id, task.task_type, submitted_by)

    return {
        "task_id": str(task.id),
        "status": task.status,
        "created_at": task.created_at.isoformat(),
        "message": "Task queued for processing",
    }


@router.get(
    "/{task_id}",
    response_model=dict,
    summary="Poll task status",
)
async def get_task(
    task_id: uuid.UUID,
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """
    MT-003: Poll task status by UUID.
    Returns full task detail including executor, review, vertex, and report_available.
    """
    task = await task_repo.get_task(session, task_id)
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found.",
        )

    # Build MT-003 expected response shape
    executor_out = None
    if task.executor_output_json:
        try:
            executor_out = json.loads(task.executor_output_json)
        except Exception:
            executor_out = None

    review_out = None
    if task.review_result_json:
        try:
            review_out = json.loads(task.review_result_json)
        except Exception:
            review_out = None

    vertex_out = None
    if task.vertex_event_hash:
        vertex_out = {
            "event_hash": task.vertex_event_hash,
            "round": task.vertex_round,
        }

    return {
        "task_id": str(task.id),
        "status": task.status,
        "task_type": task.task_type,
        "workflow_id": task.workflow_id,
        "created_at": task.created_at.isoformat(),
        "executor": executor_out,
        "review": review_out,
        "vertex": vertex_out,
        "report_available": False,  # Phase 5
    }


@router.get(
    "",
    response_model=dict,
    summary="List tasks (paginated)",
)
async def list_tasks(
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Results per page"),
    status_filter: str | None = Query(default=None, description="Filter by status"),
    _key_meta: dict = Depends(require_api_key),
    session=Depends(get_db_session),
):
    """Paginated list of all tasks, newest first."""
    tasks, total = await task_repo.list_tasks(
        session,
        page=page,
        page_size=page_size,
        status_filter=status_filter,
    )

    return {
        "tasks": [
            {
                "task_id": str(t.id),
                "status": t.status,
                "task_type": t.task_type,
                "workflow_id": t.workflow_id,
                "created_at": t.created_at.isoformat(),
            }
            for t in tasks
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

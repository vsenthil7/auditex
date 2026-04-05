"""
Auditex -- Task repository.
All database access for the tasks table goes through here.
No SQL outside of repository files.

Methods:
  create_task()         -- INSERT new task record
  get_task()            -- SELECT single task by UUID
  list_tasks()          -- SELECT paginated task list
  update_task_status()  -- UPDATE status + optional fields (the one permitted mutation)
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models.task import Task


async def create_task(
    session: AsyncSession,
    *,
    task_type: str,
    payload: dict,
    submitted_by: str | None = None,
    workflow_id: str | None = None,
    api_key_id: str | None = None,
) -> Task:
    """
    Insert a new Task record at QUEUED status.
    Returns the persisted Task ORM object.
    """
    task = Task(
        task_type=task_type,
        status="QUEUED",
        payload_json=json.dumps(payload),
        submitted_by=submitted_by,
        workflow_id=workflow_id,
        api_key_id=api_key_id,
    )
    session.add(task)
    await session.flush()  # flush to get generated id without committing
    await session.refresh(task)
    return task


async def get_task(
    session: AsyncSession,
    task_id: uuid.UUID,
) -> Task | None:
    """
    Fetch a single Task by UUID. Returns None if not found.
    """
    result = await session.execute(select(Task).where(Task.id == task_id))
    return result.scalar_one_or_none()


async def list_tasks(
    session: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 20,
    status_filter: str | None = None,
) -> tuple[list[Task], int]:
    """
    Paginated task list. Returns (tasks, total_count).
    Ordered by created_at descending (newest first).
    """
    query = select(Task)
    count_query = select(func.count()).select_from(Task)

    if status_filter:
        query = query.where(Task.status == status_filter)
        count_query = count_query.where(Task.status == status_filter)

    query = query.order_by(Task.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await session.execute(query)
    tasks = list(result.scalars().all())

    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    return tasks, total


async def update_task_status(
    session: AsyncSession,
    task_id: uuid.UUID,
    *,
    status: str,
    executor_agent_id: uuid.UUID | None = None,
    executor_output_json: str | None = None,
    executor_confidence: float | None = None,
    execution_started_at: datetime | None = None,
    execution_completed_at: datetime | None = None,
    review_result_json: str | None = None,
    consensus_result: str | None = None,
    review_completed_at: datetime | None = None,
    vertex_event_hash: str | None = None,
    vertex_round: int | None = None,
    vertex_finalised_at: datetime | None = None,
    completed_at: datetime | None = None,
    failed_at: datetime | None = None,
    failure_reason: str | None = None,
    escalated_at: datetime | None = None,
    escalation_reason: str | None = None,
    retry_count: int | None = None,
) -> Task | None:
    """
    Update task status and any associated fields.
    This is the only mutation permitted on the tasks table.
    Returns the updated Task, or None if not found.
    """
    task = await get_task(session, task_id)
    if task is None:
        return None

    task.status = status

    # Apply optional field updates only if provided
    if executor_agent_id is not None:
        task.executor_agent_id = executor_agent_id
    if executor_output_json is not None:
        task.executor_output_json = executor_output_json
    if executor_confidence is not None:
        task.executor_confidence = executor_confidence
    if execution_started_at is not None:
        task.execution_started_at = execution_started_at
    if execution_completed_at is not None:
        task.execution_completed_at = execution_completed_at
    if review_result_json is not None:
        task.review_result_json = review_result_json
    if consensus_result is not None:
        task.consensus_result = consensus_result
    if review_completed_at is not None:
        task.review_completed_at = review_completed_at
    if vertex_event_hash is not None:
        task.vertex_event_hash = vertex_event_hash
    if vertex_round is not None:
        task.vertex_round = vertex_round
    if vertex_finalised_at is not None:
        task.vertex_finalised_at = vertex_finalised_at
    if completed_at is not None:
        task.completed_at = completed_at
    if failed_at is not None:
        task.failed_at = failed_at
    if failure_reason is not None:
        task.failure_reason = failure_reason
    if escalated_at is not None:
        task.escalated_at = escalated_at
    if escalation_reason is not None:
        task.escalation_reason = escalation_reason
    if retry_count is not None:
        task.retry_count = retry_count

    await session.flush()
    await session.refresh(task)
    return task

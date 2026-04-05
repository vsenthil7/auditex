"""
Auditex -- Execution worker.
Celery task that executes a submitted task using the Claude executor.

Phase 3 lifecycle:  QUEUED -> EXECUTING -> COMPLETED | FAILED
Phase 4 will insert: REVIEWING -> FINALISING between EXECUTING and COMPLETED.

The Celery task is synchronous (standard def) because Celery workers run in
their own process. Async DB and AI calls are wrapped with asyncio.run().
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from celery.utils.log import get_task_logger

from workers.celery_app import celery_app

logger = get_task_logger(__name__)

# Maximum retry attempts before routing to DLQ
_MAX_RETRIES = 3


@celery_app.task(
    name="workers.execution_worker.execute_task",
    queue="execution_queue",
    bind=True,
    max_retries=_MAX_RETRIES,
    default_retry_delay=1,  # initial delay -- overridden by exponential_backoff
)
def execute_task(self, task_id_str: str) -> dict:
    """
    Main execution Celery task.

    Args:
        task_id_str: UUID string of the task to execute.

    Returns:
        dict with task_id and final status (for Celery result backend).
    """
    return asyncio.run(_execute_task_async(self, task_id_str))


async def _execute_task_async(celery_task, task_id_str: str) -> dict:
    """
    Async implementation of the execution logic.
    Separated from the sync Celery wrapper to allow clean async/await usage.
    """
    # Import here to avoid circular imports at module load time
    from core.execution.claude_executor import execute_task as run_executor
    from core.execution.retry_handler import exponential_backoff, route_to_dlq
    from db.connection import AsyncSessionLocal
    from db.repositories import event_repo, task_repo
    from services.claude_service import ClaudeServiceError

    task_id = uuid.UUID(task_id_str)
    now = datetime.now(timezone.utc)

    logger.info("execute_task started | task_id=%s attempt=%d", task_id, celery_task.request.retries + 1)

    async with AsyncSessionLocal() as session:
        # ------------------------------------------------------------------
        # 1. Load task from DB
        # ------------------------------------------------------------------
        task = await task_repo.get_task(session, task_id)
        if task is None:
            logger.error("execute_task: task %s not found in DB -- aborting", task_id)
            return {"task_id": task_id_str, "status": "NOT_FOUND"}

        if task.status not in ("QUEUED", "EXECUTING"):
            logger.warning(
                "execute_task: task %s already in status=%s -- skipping",
                task_id, task.status,
            )
            return {"task_id": task_id_str, "status": task.status}

        # ------------------------------------------------------------------
        # 2. Mark EXECUTING
        # ------------------------------------------------------------------
        await task_repo.update_task_status(
            session,
            task_id=task_id,
            status="EXECUTING",
            execution_started_at=now,
        )
        await event_repo.insert_event(
            session,
            task_id=task_id,
            event_type="task_execution_started",
            payload={"attempt": celery_task.request.retries + 1},
        )
        await session.commit()

        # ------------------------------------------------------------------
        # 3. Parse payload
        # ------------------------------------------------------------------
        try:
            full_payload = json.loads(task.payload_json)
            # The API stores payload under a "payload" key alongside "metadata"
            payload = full_payload.get("payload", full_payload)
        except (json.JSONDecodeError, Exception) as exc:
            logger.error("execute_task: payload parse failed for %s: %s", task_id, exc)
            await route_to_dlq(session, task_id, f"Payload parse error: {exc}")
            await session.commit()
            return {"task_id": task_id_str, "status": "FAILED"}

        # ------------------------------------------------------------------
        # 4. Call Claude executor (with retry on failure)
        # ------------------------------------------------------------------
        attempt = celery_task.request.retries + 1
        try:
            result = await run_executor(
                task_id=task_id,
                task_type=task.task_type,
                payload=payload,
            )

        except (ClaudeServiceError, ValueError) as exc:
            logger.error(
                "execute_task: execution failed | task=%s attempt=%d/%d error=%s",
                task_id, attempt, _MAX_RETRIES, exc,
            )

            if attempt < _MAX_RETRIES:
                # Increment retry count in DB
                await task_repo.update_task_status(
                    session,
                    task_id=task_id,
                    status="EXECUTING",
                    retry_count=attempt,
                )
                await event_repo.insert_event(
                    session,
                    task_id=task_id,
                    event_type="task_execution_retry",
                    payload={"attempt": attempt, "error": str(exc)[:500]},
                )
                await session.commit()

                # Apply backoff then re-raise for Celery retry
                await exponential_backoff(attempt)
                raise celery_task.retry(exc=exc, countdown=0)

            else:
                # All retries exhausted -- route to DLQ
                await route_to_dlq(
                    session,
                    task_id,
                    f"Executor failed after {_MAX_RETRIES} attempts: {exc}",
                )
                await session.commit()
                return {"task_id": task_id_str, "status": "FAILED"}

        except Exception as exc:
            # Unexpected error -- route to DLQ immediately
            logger.exception("execute_task: unexpected error for %s: %s", task_id, exc)
            await route_to_dlq(session, task_id, f"Unexpected error: {exc}")
            await session.commit()
            return {"task_id": task_id_str, "status": "FAILED"}

        # ------------------------------------------------------------------
        # 5. Execution succeeded -- mark COMPLETED (Phase 3: skip review)
        # ------------------------------------------------------------------
        completed_at = datetime.now(timezone.utc)

        # Build the executor JSON blob that GET /tasks/{id} returns
        executor_output = {
            "model": result.model,
            "output": result.output,
            "confidence": result.confidence,
            "completed_at": completed_at.isoformat(),
        }

        await task_repo.update_task_status(
            session,
            task_id=task_id,
            status="COMPLETED",
            executor_output_json=json.dumps(executor_output),
            executor_confidence=result.confidence,
            execution_completed_at=completed_at,
            completed_at=completed_at,
        )
        await event_repo.insert_event(
            session,
            task_id=task_id,
            event_type="task_execution_completed",
            payload={
                "model": result.model,
                "confidence": result.confidence,
                "tokens_used": result.tokens_used,
            },
        )
        await session.commit()

        logger.info(
            "execute_task COMPLETED | task=%s model=%s confidence=%.3f tokens=%d",
            task_id, result.model, result.confidence, result.tokens_used,
        )

        return {"task_id": task_id_str, "status": "COMPLETED"}

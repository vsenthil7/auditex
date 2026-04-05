"""
Auditex -- Execution worker.
Celery task that executes a submitted task using the Claude executor,
then runs the full review pipeline, then submits to the Vertex consensus
layer (stub in Phase 5), then marks COMPLETED, then dispatches the
reporting task (Phase 6).

Phase 6 lifecycle:  QUEUED -> EXECUTING -> REVIEWING -> FINALISING -> COMPLETED
                    -> (async) reporting_worker.generate_poc_report

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

# In stub mode, sleep briefly after committing FINALISING so that the status
# is observable by pollers before COMPLETED is written.
# In production, real Vertex consensus (~26-100ms) provides this naturally.
_FINALISING_STUB_SLEEP_SECONDS = 2


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
    Async implementation of the execution + review + consensus logic.
    Separated from the sync Celery wrapper to allow clean async/await usage.
    """
    # Import here to avoid circular imports at module load time
    from core.execution.claude_executor import execute_task as run_executor
    from core.execution.retry_handler import exponential_backoff, route_to_dlq
    from core.review.coordinator import run_review_pipeline
    from core.review.hash_commitment import SecurityViolationError
    from core.consensus.event_builder import build_task_completed_event
    from core.consensus.foxmq_client import publish_event as foxmq_publish
    from core.consensus.vertex_client import submit_event as vertex_submit, _STUB_MODE as vertex_stub_mode
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

                await exponential_backoff(attempt)
                raise celery_task.retry(exc=exc, countdown=0)

            else:
                await route_to_dlq(
                    session,
                    task_id,
                    f"Executor failed after {_MAX_RETRIES} attempts: {exc}",
                )
                await session.commit()
                return {"task_id": task_id_str, "status": "FAILED"}

        except Exception as exc:
            logger.exception("execute_task: unexpected error for %s: %s", task_id, exc)
            await route_to_dlq(session, task_id, f"Unexpected error: {exc}")
            await session.commit()
            return {"task_id": task_id_str, "status": "FAILED"}

        # ------------------------------------------------------------------
        # 5. Execution succeeded -- build executor output blob
        # ------------------------------------------------------------------
        execution_completed_at = datetime.now(timezone.utc)

        executor_output_blob = {
            "model": result.model,
            "output": result.output,
            "confidence": result.confidence,
            "completed_at": execution_completed_at.isoformat(),
        }

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

        # ------------------------------------------------------------------
        # 6. Mark REVIEWING and persist executor output
        # ------------------------------------------------------------------
        await task_repo.update_task_status(
            session,
            task_id=task_id,
            status="REVIEWING",
            executor_output_json=json.dumps(executor_output_blob),
            executor_confidence=result.confidence,
            execution_completed_at=execution_completed_at,
        )
        await event_repo.insert_event(
            session,
            task_id=task_id,
            event_type="task_review_started",
            payload={"reviewers": ["gpt-4o", "gpt-4o", "claude-sonnet-4-6"]},
        )
        await session.commit()

        logger.info(
            "execute_task: execution complete, starting review pipeline | task=%s "
            "model=%s confidence=%.3f",
            task_id, result.model, result.confidence,
        )

        # ------------------------------------------------------------------
        # 7. Run review pipeline
        # ------------------------------------------------------------------
        try:
            review_result = await run_review_pipeline(
                task_id=task_id,
                task_type=task.task_type,
                payload=payload,
                executor_output=result.output,
            )

        except SecurityViolationError as exc:
            logger.error(
                "execute_task: SECURITY_VIOLATION in review pipeline | task=%s: %s",
                task_id, exc,
            )
            await event_repo.insert_event(
                session,
                task_id=task_id,
                event_type="security_violation",
                payload={"reason": str(exc)[:1000]},
            )
            await route_to_dlq(
                session, task_id, f"Security violation in review pipeline: {exc}"
            )
            await session.commit()
            return {"task_id": task_id_str, "status": "FAILED"}

        except Exception as exc:
            logger.exception(
                "execute_task: review pipeline failed | task=%s: %s", task_id, exc
            )
            await route_to_dlq(
                session, task_id, f"Review pipeline error: {exc}"
            )
            await session.commit()
            return {"task_id": task_id_str, "status": "FAILED"}

        # ------------------------------------------------------------------
        # 8. Build review result JSON blob
        # ------------------------------------------------------------------
        review_result_blob = {
            "consensus": review_result.consensus,
            "reviewers": [
                {
                    "model": r.model,
                    "verdict": r.verdict,
                    "confidence": r.confidence,
                    "commitment_verified": r.commitment_verified,
                }
                for r in review_result.reviewers
            ],
            "completed_at": review_result.completed_at,
        }

        await event_repo.insert_event(
            session,
            task_id=task_id,
            event_type="task_review_completed",
            payload={
                "consensus": review_result.consensus,
                "all_verified": review_result.all_verified,
                "verdicts": review_result.verdicts,
            },
        )

        # ------------------------------------------------------------------
        # 9. Mark FINALISING -- review done, submitting to Vertex (stub)
        #    Commit before the consensus calls so the status is immediately
        #    visible to pollers. In stub mode, sleep briefly to ensure the
        #    FINALISING status is observable (real Vertex takes 26-100ms+).
        # ------------------------------------------------------------------
        await task_repo.update_task_status(
            session,
            task_id=task_id,
            status="FINALISING",
            review_result_json=json.dumps(review_result_blob),
            consensus_result=review_result.consensus,
        )
        await event_repo.insert_event(
            session,
            task_id=task_id,
            event_type="task_finalising_started",
            payload={"consensus": review_result.consensus},
        )
        await session.commit()

        logger.info(
            "execute_task: review complete, entering FINALISING | task=%s consensus=%s stub=%s",
            task_id, review_result.consensus, vertex_stub_mode,
        )

        # Stub-mode pause: gives pollers a guaranteed window to observe FINALISING.
        # Remove when real Vertex is wired up -- consensus latency replaces this.
        if vertex_stub_mode:
            await asyncio.sleep(_FINALISING_STUB_SLEEP_SECONDS)

        # ------------------------------------------------------------------
        # 10. Consensus layer: FoxMQ publish + Vertex finalisation (stub)
        #     On failure: log error, complete task with vertex fields null.
        #     Rationale: stub failure must not block task completion.
        #     In production with real Vertex, route to DLQ instead.
        # ------------------------------------------------------------------
        vertex_event_hash: str | None = None
        vertex_round: int | None = None
        vertex_finalised_at_dt = None

        try:
            # Attach executor confidence to review_result so event_builder can use it
            review_result.executor_confidence = result.confidence

            # Build the canonical event payload
            event_payload = build_task_completed_event(
                task_id=task_id_str,
                task_type=task.task_type,
                executor_output=result.output,
                review_result=review_result,
            )

            # Publish to FoxMQ (stub: logs + returns True)
            foxmq_publish(event_payload)

            # Submit to Vertex (stub: SHA-256 + Redis round + timestamp)
            receipt = vertex_submit(event_payload)

            vertex_event_hash = receipt.event_hash
            vertex_round = receipt.round
            vertex_finalised_at_dt = datetime.fromisoformat(receipt.finalised_at)

            logger.info(
                "execute_task: Vertex finalised | task=%s hash=%s... round=%d stub=%s",
                task_id, receipt.event_hash[:16], receipt.round, receipt.is_stub,
            )

        except Exception as exc:
            # Consensus layer failure: log, continue to COMPLETED with null vertex fields
            logger.error(
                "execute_task: consensus layer error (non-blocking) | task=%s: %s",
                task_id, exc,
            )
            await event_repo.insert_event(
                session,
                task_id=task_id,
                event_type="consensus_layer_error",
                payload={"error": str(exc)[:500]},
            )

        # ------------------------------------------------------------------
        # 11. Mark COMPLETED
        # ------------------------------------------------------------------
        completed_at = datetime.now(timezone.utc)

        await task_repo.update_task_status(
            session,
            task_id=task_id,
            status="COMPLETED",
            vertex_event_hash=vertex_event_hash,
            vertex_round=vertex_round,
            vertex_finalised_at=vertex_finalised_at_dt,
            completed_at=completed_at,
        )
        await event_repo.insert_event(
            session,
            task_id=task_id,
            event_type="task_completed",
            payload={
                "consensus": review_result.consensus,
                "executor_model": result.model,
                "executor_confidence": result.confidence,
                "vertex_round": vertex_round,
                "vertex_event_hash": vertex_event_hash,
            },
        )
        await session.commit()

        logger.info(
            "execute_task COMPLETED | task=%s consensus=%s vertex_round=%s",
            task_id, review_result.consensus, vertex_round,
        )

        # ------------------------------------------------------------------
        # 12. Dispatch reporting task (Phase 6)
        #     Fire-and-forget: reporting runs on reporting_queue asynchronously.
        #     This import is deferred to avoid circular imports at module load.
        # ------------------------------------------------------------------
        try:
            from workers.reporting_worker import generate_poc_report as celery_report_task
            celery_report_task.delay(task_id_str)
            logger.info("execute_task: reporting task dispatched | task=%s", task_id)
        except Exception as exc:
            # Reporting dispatch failure must never block task completion.
            logger.error(
                "execute_task: failed to dispatch reporting task | task=%s: %s",
                task_id, exc,
            )

        return {"task_id": task_id_str, "status": "COMPLETED"}

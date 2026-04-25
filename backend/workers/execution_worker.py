"""
Auditex -- Execution worker.
Celery task that executes a submitted task using the Claude executor,
then runs the full review pipeline, then submits to the Vertex consensus
layer (stub in Phase 5), then marks COMPLETED, then dispatches the
reporting task (Phase 6).

Phase 7 fix (v2): The module-level engine in db/connection.py is created
once at import time and bound to the event loop that existed at that point.
When Celery runs a second task in a new asyncio.run() call, that loop is
gone. pool_pre_ping=True then tries to ping using the dead loop and raises:
    RuntimeError: Task got Future attached to a different loop

Fix: each task invocation creates its own engine + session factory from
scratch, uses it for the whole task, then disposes it in the finally block.
This means each task gets a fresh pool bound to its own event loop.

Phase 9 fix: _STUB_MODE removed from vertex_client (replaced by USE_REAL_VERTEX
env var). vertex_stub_mode now derived from env var directly in task body.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

from celery.utils.log import get_task_logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from workers.celery_app import celery_app

logger = get_task_logger(__name__)

_MAX_RETRIES = 3
_FINALISING_STUB_SLEEP_SECONDS = 2


def _make_engine_and_session():
    """
    Create a fresh async engine + session factory for this task invocation.
    Must be called inside the new event loop (after asyncio.new_event_loop()).
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=False,  # MUST be False — pre_ping uses the loop at engine creation time
    )
    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    return engine, session_factory


@celery_app.task(
    name="workers.execution_worker.execute_task",
    queue="execution_queue",
    bind=True,
    max_retries=_MAX_RETRIES,
    default_retry_delay=1,
)
def execute_task(self, task_id_str: str) -> dict:
    """
    Main execution Celery task.

    Creates a fresh event loop AND a fresh DB engine per invocation.
    This is the only reliable fix for the asyncpg "Future attached to
    a different loop" error when running multiple sequential Celery tasks.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    engine = None
    try:
        engine, session_factory = _make_engine_and_session()
        return loop.run_until_complete(
            _execute_task_async(self, task_id_str, session_factory)
        )
    finally:
        if engine is not None:
            try:
                loop.run_until_complete(engine.dispose())
                logger.info("execute_task: engine disposed for task %s", task_id_str)
            except Exception as e:
                logger.warning("execute_task: engine dispose error: %s", e)
        loop.close()


async def _execute_task_async(celery_task, task_id_str: str, AsyncSessionLocal) -> dict:
    from core.execution.claude_executor import execute_task as run_executor
    from core.execution.retry_handler import exponential_backoff, route_to_dlq
    from core.review.coordinator import run_review_pipeline
    from core.review.hash_commitment import SecurityViolationError
    from core.consensus.event_builder import build_task_completed_event
    from core.consensus.foxmq_client import publish_event as foxmq_publish
    from core.consensus.vertex_client import submit_event as vertex_submit
    from db.repositories import event_repo, task_repo, human_oversight_repo
    from core.review.oversight_policy import Policy as OversightPolicy, requires_human_oversight
    from services.claude_service import ClaudeServiceError

    # Phase 9: stub mode derived from env var (USE_REAL_VERTEX=true = LIVE mode)
    vertex_stub_mode = os.environ.get("USE_REAL_VERTEX", "false").lower() != "true"

    task_id = uuid.UUID(task_id_str)
    now = datetime.now(timezone.utc)

    logger.info("execute_task started | task_id=%s attempt=%d", task_id, celery_task.request.retries + 1)

    async with AsyncSessionLocal() as session:
        # 1. Load task
        task = await task_repo.get_task(session, task_id)
        if task is None:
            logger.error("execute_task: task %s not found -- aborting", task_id)
            return {"task_id": task_id_str, "status": "NOT_FOUND"}

        if task.status not in ("QUEUED", "EXECUTING"):
            logger.warning("execute_task: task %s already %s -- skipping", task_id, task.status)
            return {"task_id": task_id_str, "status": task.status}

        # 2. Mark EXECUTING
        await task_repo.update_task_status(session, task_id=task_id, status="EXECUTING", execution_started_at=now)
        await event_repo.insert_event(session, task_id=task_id, event_type="task_execution_started", payload={"attempt": celery_task.request.retries + 1})
        await session.commit()

        # 3. Parse payload
        try:
            full_payload = json.loads(task.payload_json)
            payload = full_payload.get("payload", full_payload)
        except Exception as exc:
            logger.error("execute_task: payload parse failed for %s: %s", task_id, exc)
            await route_to_dlq(session, task_id, f"Payload parse error: {exc}")
            await session.commit()
            return {"task_id": task_id_str, "status": "FAILED"}

        # 4. Claude executor
        attempt = celery_task.request.retries + 1
        try:
            result = await run_executor(task_id=task_id, task_type=task.task_type, payload=payload)

        except (ClaudeServiceError, ValueError) as exc:
            logger.error("execute_task: execution failed | task=%s attempt=%d/%d error=%s", task_id, attempt, _MAX_RETRIES, exc)
            if attempt < _MAX_RETRIES:
                await task_repo.update_task_status(session, task_id=task_id, status="EXECUTING", retry_count=attempt)
                await event_repo.insert_event(session, task_id=task_id, event_type="task_execution_retry", payload={"attempt": attempt, "error": str(exc)[:500]})
                await session.commit()
                await exponential_backoff(attempt)
                raise celery_task.retry(exc=exc, countdown=0)
            else:
                await route_to_dlq(session, task_id, f"Executor failed after {_MAX_RETRIES} attempts: {exc}")
                await session.commit()
                return {"task_id": task_id_str, "status": "FAILED"}

        except Exception as exc:
            logger.exception("execute_task: unexpected error for %s: %s", task_id, exc)
            await route_to_dlq(session, task_id, f"Unexpected error: {exc}")
            await session.commit()
            return {"task_id": task_id_str, "status": "FAILED"}

        # 5. Executor output blob
        execution_completed_at = datetime.now(timezone.utc)
        executor_output_blob = {"model": result.model, "output": result.output, "confidence": result.confidence, "completed_at": execution_completed_at.isoformat()}
        await event_repo.insert_event(session, task_id=task_id, event_type="task_execution_completed", payload={"model": result.model, "confidence": result.confidence, "tokens_used": result.tokens_used})

        # 6. Mark REVIEWING
        await task_repo.update_task_status(session, task_id=task_id, status="REVIEWING", executor_output_json=json.dumps(executor_output_blob), executor_confidence=result.confidence, execution_completed_at=execution_completed_at)
        await event_repo.insert_event(session, task_id=task_id, event_type="task_review_started", payload={"reviewers": ["gpt-4o", "gpt-4o", "claude-sonnet-4-6"]})
        await session.commit()
        logger.info("execute_task: execution complete, starting review | task=%s model=%s confidence=%.3f", task_id, result.model, result.confidence)

        # 7. Review pipeline
        try:
            review_result = await run_review_pipeline(task_id=task_id, task_type=task.task_type, payload=payload, executor_output=result.output)
        except SecurityViolationError as exc:
            logger.error("execute_task: SECURITY_VIOLATION | task=%s: %s", task_id, exc)
            await event_repo.insert_event(session, task_id=task_id, event_type="security_violation", payload={"reason": str(exc)[:1000]})
            await route_to_dlq(session, task_id, f"Security violation: {exc}")
            await session.commit()
            return {"task_id": task_id_str, "status": "FAILED"}
        except Exception as exc:
            logger.exception("execute_task: review pipeline failed | task=%s: %s", task_id, exc)
            await route_to_dlq(session, task_id, f"Review pipeline error: {exc}")
            await session.commit()
            return {"task_id": task_id_str, "status": "FAILED"}

        # 8. Review result blob
        review_result_blob = {
            "consensus": review_result.consensus,
            "reviewers": [{"model": r.model, "verdict": r.verdict, "confidence": r.confidence, "commitment_verified": r.commitment_verified} for r in review_result.reviewers],
            "completed_at": review_result.completed_at,
        }
        await event_repo.insert_event(session, task_id=task_id, event_type="task_review_completed", payload={"consensus": review_result.consensus, "all_verified": review_result.all_verified, "verdicts": review_result.verdicts})

        # 9. Mark FINALISING (or pause for Article 14 human oversight)
        await task_repo.update_task_status(session, task_id=task_id, status="FINALISING", review_result_json=json.dumps(review_result_blob), consensus_result=review_result.consensus)
        await event_repo.insert_event(session, task_id=task_id, event_type="task_finalising_started", payload={"consensus": review_result.consensus})
        await session.commit()
        logger.info("execute_task: review complete, FINALISING | task=%s consensus=%s", task_id, review_result.consensus)

        # 9b. HIL-6 Article 14 gate: load policy, decide if human review required
        oversight_row = await human_oversight_repo.get_policy(session, task_type=task.task_type)
        oversight_required = False
        if oversight_row is not None:
            try:
                oversight_policy = OversightPolicy(
                    task_type=oversight_row.task_type,
                    required=bool(oversight_row.required),
                    n_required=int(oversight_row.n_required),
                    m_total=int(oversight_row.m_total),
                    timeout_minutes=oversight_row.timeout_minutes,
                    auto_commit_on_timeout=bool(oversight_row.auto_commit_on_timeout),
                )
                oversight_required = requires_human_oversight(oversight_policy)
            except (ValueError, TypeError) as exc:
                logger.error("execute_task: invalid oversight policy for task_type=%s: %s; defaulting to required=False", task.task_type, exc)
        if oversight_required:
            awaiting_at = datetime.now(timezone.utc)
            await task_repo.update_task_status(session, task_id=task_id, status="AWAITING_HUMAN_REVIEW")
            await event_repo.insert_event(session, task_id=task_id, event_type="task_awaiting_human_review", payload={"task_type": task.task_type, "n_required": oversight_policy.n_required, "m_total": oversight_policy.m_total, "timeout_minutes": oversight_policy.timeout_minutes, "awaiting_since": awaiting_at.isoformat()})
            await session.commit()
            logger.info("execute_task: AWAITING_HUMAN_REVIEW | task=%s n_required=%d m_total=%d", task_id, oversight_policy.n_required, oversight_policy.m_total)
            return {"task_id": task_id_str, "status": "AWAITING_HUMAN_REVIEW"}

        if vertex_stub_mode:
            await asyncio.sleep(_FINALISING_STUB_SLEEP_SECONDS)

        # 10. Consensus layer
        vertex_event_hash: str | None = None
        vertex_round: int | None = None
        vertex_finalised_at_dt = None
        try:
            review_result.executor_confidence = result.confidence
            event_payload = build_task_completed_event(task_id=task_id_str, task_type=task.task_type, executor_output=result.output, review_result=review_result)
            foxmq_publish(event_payload)
            receipt = vertex_submit(event_payload)
            vertex_event_hash = receipt.event_hash
            vertex_round = receipt.round
            vertex_finalised_at_dt = datetime.fromisoformat(receipt.finalised_at)
            logger.info("execute_task: Vertex finalised | task=%s hash=%s... round=%d", task_id, receipt.event_hash[:16], receipt.round)
        except Exception as exc:
            logger.error("execute_task: consensus error (non-blocking) | task=%s: %s", task_id, exc)
            await event_repo.insert_event(session, task_id=task_id, event_type="consensus_layer_error", payload={"error": str(exc)[:500]})

        # 11. Mark COMPLETED
        completed_at = datetime.now(timezone.utc)
        await task_repo.update_task_status(session, task_id=task_id, status="COMPLETED", vertex_event_hash=vertex_event_hash, vertex_round=vertex_round, vertex_finalised_at=vertex_finalised_at_dt, completed_at=completed_at)
        await event_repo.insert_event(session, task_id=task_id, event_type="task_completed", payload={"consensus": review_result.consensus, "executor_model": result.model, "executor_confidence": result.confidence, "vertex_round": vertex_round, "vertex_event_hash": vertex_event_hash})
        await session.commit()
        logger.info("execute_task COMPLETED | task=%s consensus=%s vertex_round=%s", task_id, review_result.consensus, vertex_round)

        # 12. Dispatch reporting task
        try:
            from workers.reporting_worker import generate_poc_report as celery_report_task
            celery_report_task.delay(task_id_str)
            logger.info("execute_task: reporting task dispatched | task=%s", task_id)
        except Exception as exc:
            logger.error("execute_task: failed to dispatch reporting task | task=%s: %s", task_id, exc)

        return {"task_id": task_id_str, "status": "COMPLETED"}


# ============================================================
# HIL-8: Finalisation Celery task triggered after human quorum
# ============================================================

@celery_app.task(
    name="auditex.workers.finalise_after_human_review",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def finalise_after_human_review(self, task_id_str: str) -> dict:
    """Run Vertex submit + mark COMPLETED for a task that just reached human quorum.
    Triggered from app.api.v1.human_review.record_human_decision when quorum hits.
    Idempotent: if task already has a vertex_event_hash, returns without re-submitting.
    """
    engine, factory = _make_engine_and_session()
    try:
        return asyncio.run(_finalise_after_human_review_async(task_id_str, factory))
    finally:
        asyncio.run(engine.dispose())


async def _finalise_after_human_review_async(task_id_str: str, session_factory) -> dict:
    """Async core for finalise_after_human_review.
    Pure refactor: re-runs Vertex submit + COMPLETED + reporting dispatch using
    the persisted executor_output_json and review_result_json from the task row,
    plus the human_decisions table for the audit chain.
    """
    from types import SimpleNamespace
    from db.repositories import event_repo, task_repo, human_oversight_repo
    from core.consensus.event_builder import build_task_completed_event
    from core.consensus.foxmq_client import publish_event as foxmq_publish
    from core.consensus.vertex_client import submit_event as vertex_submit

    task_id = uuid.UUID(task_id_str)
    async with session_factory() as session:
        task = await task_repo.get_task(session, task_id=task_id)
        if task is None:
            logger.warning("finalise_after_human_review: task %s not found", task_id)
            return {"task_id": task_id_str, "status": "NOT_FOUND"}
        if task.status != "FINALISING":
            logger.info("finalise_after_human_review: task %s in status %s, skipping", task_id, task.status)
            return {"task_id": task_id_str, "status": task.status}
        if task.vertex_event_hash:
            logger.info("finalise_after_human_review: task %s already has vertex hash, idempotent skip", task_id)
            return {"task_id": task_id_str, "status": task.status}

        # Reconstruct executor_output and review_result-like object from persisted JSON
        executor_blob = json.loads(task.executor_output_json or "{}")
        executor_output = executor_blob.get("output", executor_blob)
        review_blob = json.loads(task.review_result_json or "{}")
        reviewers_data = review_blob.get("reviewers", [])
        reviewer_objs = [SimpleNamespace(
            model=r.get("model"),
            verdict=r.get("verdict"),
            committed_hash=r.get("committed_hash"),
        ) for r in reviewers_data]
        review_result_obj = SimpleNamespace(
            consensus=task.consensus_result,
            all_verified=review_blob.get("all_verified", True),
            reviewers=reviewer_objs,
            executor_confidence=float(task.executor_confidence) if task.executor_confidence is not None else None,
        )

        # Load human decisions for the audit chain
        decision_rows = await human_oversight_repo.list_decisions_for_task(session, task_id=task_id)
        human_decisions = [{
            "decision": d.decision,
            "reviewed_by": d.reviewed_by,
            "decided_at": d.decided_at.isoformat() if d.decided_at else None,
        } for d in decision_rows]

        # Submit to FoxMQ + Vertex
        vertex_stub_mode_local = os.environ.get("USE_REAL_VERTEX", "false").lower() != "true"
        if vertex_stub_mode_local:
            await asyncio.sleep(_FINALISING_STUB_SLEEP_SECONDS)
        vertex_event_hash = None
        vertex_round = None
        vertex_finalised_at_dt = None
        try:
            event_payload = build_task_completed_event(
                task_id=task_id_str,
                task_type=task.task_type,
                executor_output=executor_output,
                review_result=review_result_obj,
                human_decisions=human_decisions,
            )
            foxmq_publish(event_payload)
            receipt = vertex_submit(event_payload)
            vertex_event_hash = receipt.event_hash
            vertex_round = receipt.round
            vertex_finalised_at_dt = datetime.fromisoformat(receipt.finalised_at)
            logger.info("finalise_after_human_review: Vertex finalised | task=%s hash=%s... round=%d", task_id, receipt.event_hash[:16], receipt.round)
        except Exception as exc:
            logger.error("finalise_after_human_review: consensus error (non-blocking) | task=%s: %s", task_id, exc)
            await event_repo.insert_event(session, task_id=task_id, event_type="consensus_layer_error", payload={"error": str(exc)[:500]})

        # Mark COMPLETED + emit task_completed event with human signature in payload
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
                "consensus": review_result_obj.consensus,
                "vertex_round": vertex_round,
                "vertex_event_hash": vertex_event_hash,
                "human_decisions_count": len(human_decisions),
                "human_decisions_summary": [{"decision": d["decision"], "reviewed_by": d["reviewed_by"]} for d in human_decisions],
            },
        )
        await session.commit()
        logger.info("finalise_after_human_review COMPLETED | task=%s humans=%d", task_id, len(human_decisions))

    # Dispatch reporting (outside the session)
    try:
        from workers.reporting_worker import generate_poc_report as celery_report_task
        celery_report_task.delay(task_id_str)
        logger.info("finalise_after_human_review: reporting task dispatched | task=%s", task_id)
    except Exception as exc:
        logger.error("finalise_after_human_review: failed to dispatch reporting | task=%s: %s", task_id, exc)

    return {"task_id": task_id_str, "status": "COMPLETED"}

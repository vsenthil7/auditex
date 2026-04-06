"""
Auditex -- Reporting Celery worker.
Generates the PoC report (plain-English narrative + EU AI Act export)
for a completed task, then writes it to the reports table and sets
task.report_available = True.

Queue: reporting_queue
Task name: workers.reporting_worker.generate_poc_report

Phase 7/8 fix: apply the same _make_engine_and_session() pattern as
execution_worker.py to avoid the asyncpg "Future attached to a different
loop" RuntimeError that occurs when Celery runs multiple sequential tasks
(each asyncio.run() creates a new event loop, but the module-level engine
is bound to the original loop).
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from celery.utils.log import get_task_logger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from workers.celery_app import celery_app

logger = get_task_logger(__name__)


def _make_engine_and_session():
    """
    Create a fresh async engine + session factory for this task invocation.
    Must be called inside the new event loop (after asyncio.new_event_loop()).
    pool_pre_ping=False is required — pre_ping uses the loop at engine
    creation time and will fail on a subsequent Celery task invocation.
    """
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=False,
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
    name="workers.reporting_worker.generate_poc_report",
    queue="reporting_queue",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def generate_poc_report(self, task_id_str: str) -> dict:
    """
    Celery task: generate the PoC report for a completed task.

    Creates a fresh event loop AND a fresh DB engine per invocation —
    the only reliable fix for asyncpg "Future attached to a different loop".

    Args:
        task_id_str: UUID string of the COMPLETED task.

    Returns:
        dict with task_id and outcome.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    engine = None
    try:
        engine, AsyncSessionLocal = _make_engine_and_session()
        return loop.run_until_complete(
            _generate_report_async(self, task_id_str, AsyncSessionLocal)
        )
    finally:
        if engine is not None:
            try:
                loop.run_until_complete(engine.dispose())
                logger.info("generate_poc_report: engine disposed for task %s", task_id_str)
            except Exception as e:
                logger.warning("generate_poc_report: engine dispose error: %s", e)
        loop.close()


async def _generate_report_async(celery_task, task_id_str: str, AsyncSessionLocal) -> dict:
    from core.reporting.poc_generator import generate_report
    from core.reporting.eu_act_formatter import format_eu_ai_act
    from db.repositories import task_repo, report_repo

    task_id = uuid.UUID(task_id_str)

    logger.info("generate_poc_report started | task_id=%s", task_id)

    async with AsyncSessionLocal() as session:
        # ------------------------------------------------------------------
        # 1. Load task
        # ------------------------------------------------------------------
        task = await task_repo.get_task(session, task_id)
        if task is None:
            logger.error("generate_poc_report: task %s not found -- aborting", task_id)
            return {"task_id": task_id_str, "outcome": "NOT_FOUND"}

        if task.status != "COMPLETED":
            logger.warning(
                "generate_poc_report: task %s is not COMPLETED (status=%s) -- skipping",
                task_id, task.status,
            )
            return {"task_id": task_id_str, "outcome": "SKIPPED"}

        # Check if report already generated (idempotency guard)
        existing = await report_repo.get_report_by_task_id(session, task_id)
        if existing is not None:
            logger.info("generate_poc_report: report already exists for %s -- skipping", task_id)
            return {"task_id": task_id_str, "outcome": "ALREADY_EXISTS"}

        # ------------------------------------------------------------------
        # 2. Deserialise executor output and review result
        # ------------------------------------------------------------------
        executor_output: dict = {}
        if task.executor_output_json:
            try:
                executor_output = json.loads(task.executor_output_json)
            except Exception:
                executor_output = {}

        review_result: dict = {}
        if task.review_result_json:
            try:
                review_result = json.loads(task.review_result_json)
            except Exception:
                review_result = {}

        vertex_finalised_at_str = (
            task.vertex_finalised_at.isoformat()
            if task.vertex_finalised_at
            else None
        )

        # ------------------------------------------------------------------
        # 3. Generate plain-English narrative (calls Claude)
        # ------------------------------------------------------------------
        try:
            poc_data = await generate_report(
                task_id=task_id,
                task_type=task.task_type,
                executor_output=executor_output,
                review_result=review_result,
                vertex_event_hash=task.vertex_event_hash,
                vertex_round=task.vertex_round,
                vertex_finalised_at=vertex_finalised_at_str,
            )
        except Exception as exc:
            logger.error(
                "generate_poc_report: narrative generation failed | task=%s: %s",
                task_id, exc,
            )
            raise celery_task.retry(exc=exc, countdown=10)

        # ------------------------------------------------------------------
        # 4. Build EU AI Act structured export
        # ------------------------------------------------------------------
        eu_ai_act = format_eu_ai_act(
            task_type=task.task_type,
            executor_output=executor_output,
            review_result=review_result,
            vertex_event_hash=task.vertex_event_hash,
            vertex_round=task.vertex_round,
            vertex_finalised_at=vertex_finalised_at_str,
        )

        # ------------------------------------------------------------------
        # 5. Write Report record
        # ------------------------------------------------------------------
        report = await report_repo.create_report(
            session,
            task_id=task_id,
            narrative=poc_data.plain_english_summary,
            eu_ai_act_json=json.dumps(eu_ai_act),
            schema_version="poc_report_v1",
            vertex_event_hash=task.vertex_event_hash,
            generated_at=poc_data.generated_at,
            generator_model="claude-sonnet-4-6",
        )

        # ------------------------------------------------------------------
        # 6. Mark task.report_available = True
        # ------------------------------------------------------------------
        task.report_available = True
        await session.flush()
        await session.commit()

        logger.info(
            "generate_poc_report DONE | task=%s report=%s",
            task_id, report.id,
        )

        return {"task_id": task_id_str, "outcome": "GENERATED", "report_id": str(report.id)}

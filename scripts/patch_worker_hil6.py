p = r"C:/Users/v_sen/Documents/Projects/0001_Hack0014_Vertex_Swarm_Tashi/auditex/backend/workers/execution_worker.py"
t = open(p, 'r', encoding='utf-8').read()
old = """OLD_BLOCK
        # 9. Mark FINALISING
        await task_repo.update_task_status(session, task_id=task_id, status="FINALISING", review_result_json=json.dumps(review_result_blob), consensus_result=review_result.consensus)
        await event_repo.insert_event(session, task_id=task_id, event_type="task_finalising_started", payload={"consensus": review_result.consensus})
        await session.commit()
        logger.info("execute_task: review complete, FINALISING | task=%s consensus=%s", task_id, review_result.consensus)
"""
old = old.split("OLD_BLOCK", 1)[1].lstrip().rstrip()
new = """NEW_BLOCK
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
"""
new = new.split("NEW_BLOCK", 1)[1].lstrip().rstrip()
n = t.count(old)
t = t.replace(old, new, 1)
open(p, 'w', encoding='utf-8').write(t)
print('patched:', n)

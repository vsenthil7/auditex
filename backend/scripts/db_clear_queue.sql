-- Auditex -- Clear Stuck Queue + Status Report
-- Run via PowerShell (copy paste each line):
--
--   docker compose exec postgres psql -U auditex -d auditex -c "UPDATE tasks SET status='FAILED', failure_reason='Force-failed', updated_at=NOW() WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes'"
--   docker compose exec postgres psql -U auditex -d auditex -c "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"
--   docker compose exec postgres psql -U auditex -d auditex -c "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"

-- NOTE: correct column is failure_reason (not error_message — that column does not exist)

\echo 'STUCK TASKS:'
SELECT id::text, task_type, status,
       ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60)::int AS age_min
FROM tasks
WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
AND created_at < NOW() - INTERVAL '5 minutes'
ORDER BY created_at ASC;

\echo 'CLEARING...'
UPDATE tasks
SET status         = 'FAILED',
    failure_reason = 'Force-failed by db_clear_queue.sql — stuck in active state',
    updated_at     = NOW()
WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
AND created_at < NOW() - INTERVAL '5 minutes';

\echo 'STATUS AFTER CLEAR:'
SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC;

\echo 'ACTIVE IN PIPELINE (must be 0):'
SELECT COUNT(*) as active FROM tasks
WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING');

\echo 'LAST 10 TASKS:'
SELECT LEFT(id::text,8) AS id, task_type, status,
       to_char(created_at,'HH24:MI') AS time,
       report_available AS rpt,
       CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END AS ex,
       CASE WHEN review_result_json   IS NOT NULL THEN 'Y' ELSE 'N' END AS rev
FROM tasks ORDER BY created_at DESC LIMIT 10;

\echo 'REPORTS:'
SELECT COUNT(*) FROM reports;

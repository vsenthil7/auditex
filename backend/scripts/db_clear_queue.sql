-- Auditex -- Clear Stuck Queue + Status Report
-- Run: docker compose exec postgres psql -U auditex -d auditex -f /scripts/db_clear_queue.sql
-- Or inline: docker compose exec postgres psql -U auditex -d auditex < backend/scripts/db_clear_queue.sql

\echo ''
\echo '============================================================'
\echo '  STUCK TASKS (>5 min in active state)'
\echo '============================================================'
SELECT
    id::text,
    task_type,
    status,
    ROUND(EXTRACT(EPOCH FROM (NOW()-created_at))/60)::int AS age_min
FROM tasks
WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
AND created_at < NOW() - INTERVAL '5 minutes'
ORDER BY created_at ASC;

\echo ''
\echo '============================================================'
\echo '  FORCE-FAILING STUCK TASKS...'
\echo '============================================================'
UPDATE tasks
SET status        = 'FAILED',
    error_message = 'Force-failed by db_clear_queue.sql',
    updated_at    = NOW()
WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')
AND created_at < NOW() - INTERVAL '5 minutes';

\echo ''
\echo '============================================================'
\echo '  POST-CLEAR STATUS COUNTS'
\echo '============================================================'
SELECT status, COUNT(*) as count
FROM tasks
GROUP BY status
ORDER BY count DESC;

\echo ''
\echo '============================================================'
\echo '  ACTIVE IN PIPELINE (should be 0)'
\echo '============================================================'
SELECT COUNT(*) as active_count
FROM tasks
WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING');

\echo ''
\echo '============================================================'
\echo '  LAST 10 TASKS'
\echo '============================================================'
SELECT
    LEFT(id::text, 8) AS id,
    task_type,
    status,
    to_char(created_at, 'HH24:MI') AS time,
    report_available AS rpt,
    CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END AS ex,
    CASE WHEN review_result_json   IS NOT NULL THEN 'Y' ELSE 'N' END AS rev,
    CASE WHEN vertex_event_hash    IS NOT NULL THEN 'Y' ELSE 'N' END AS vtx
FROM tasks
ORDER BY created_at DESC
LIMIT 10;

\echo ''
\echo '============================================================'
\echo '  REPORTS IN DB'
\echo '============================================================'
SELECT COUNT(*) as report_count FROM reports;

\echo ''
\echo '  DONE'
\echo ''

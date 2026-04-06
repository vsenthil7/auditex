# Auditex -- Operations Runbook
# All commands you need to run manually — copy/paste directly into PowerShell
# No need to ask Claude. Updated: 06/04/2026
#
# RULE: Always run from project root:
#   C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex

# ==============================================================
# GIT COMMIT SEQUENCE (run each line one at a time)
# ==============================================================
# date
# git status
# powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "git add -A"
# git status
# git commit -m "YOUR MESSAGE"
# git status
# date

# ==============================================================
# DB -- QUEUE STATUS CHECK
# ==============================================================
# docker compose exec postgres psql -U auditex -d auditex -c "SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC"

# ==============================================================
# DB -- ACTIVE PIPELINE COUNT (must be 0 before Playwright)
# ==============================================================
# docker compose exec postgres psql -U auditex -d auditex -c "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"

# ==============================================================
# DB -- CLEAR STUCK QUEUE (verified working 06/04/2026 04:30 — UPDATE 8)
# Correct columns: status, failure_reason, created_at
# NO updated_at, NO error_message -- those columns do not exist
# ==============================================================
# docker compose exec postgres psql -U auditex -d auditex -c "UPDATE tasks SET status='FAILED', failure_reason='Force-failed' WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes'"

# ==============================================================
# DB -- CREATE STUCK TEST SCENARIO (2 fake stuck tasks)
# Use this to test db_clear_queue.sql works before trusting it
# ==============================================================
# docker compose exec postgres psql -U auditex -d auditex -c "INSERT INTO tasks (id, task_type, status, payload_json, created_at) VALUES (gen_random_uuid(), 'document_review', 'QUEUED', '{\"test\":true}', NOW() - INTERVAL '10 minutes'), (gen_random_uuid(), 'risk_analysis', 'EXECUTING', '{\"test\":true}', NOW() - INTERVAL '15 minutes')"

# ==============================================================
# DB -- RUN db_clear_queue.sql SCRIPT (PowerShell pipe method)
# ==============================================================
# Get-Content backend\scripts\db_clear_queue.sql | docker compose exec -T postgres psql -U auditex -d auditex

# ==============================================================
# DB -- LAST 10 TASKS DETAIL
# ==============================================================
# docker compose exec postgres psql -U auditex -d auditex -c "SELECT LEFT(id::text,8) AS id, task_type, status, to_char(created_at,'HH24:MI') AS time, report_available AS rpt, CASE WHEN executor_output_json IS NOT NULL THEN 'Y' ELSE 'N' END AS ex, CASE WHEN review_result_json IS NOT NULL THEN 'Y' ELSE 'N' END AS rev FROM tasks ORDER BY created_at DESC LIMIT 10"

# ==============================================================
# DB -- REPORTS TABLE
# ==============================================================
# docker compose exec postgres psql -U auditex -d auditex -c "SELECT LEFT(id::text,8) AS id, LEFT(task_id::text,8) AS task, to_char(generated_at,'HH24:MI') AS time, CASE WHEN narrative IS NOT NULL THEN 'Y' ELSE 'N' END AS narr, CASE WHEN eu_ai_act_json IS NOT NULL THEN 'Y' ELSE 'N' END AS eu FROM reports ORDER BY generated_at DESC LIMIT 5"

# ==============================================================
# DOCKER -- BUILD + RESTART SERVICES
# ==============================================================
# powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose up -d --build frontend"
# powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose up -d --build api celery-worker"
# powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose up -d --build api celery-worker frontend"

# ==============================================================
# DOCKER -- CELERY WORKER LOGS (see what worker is doing)
# ==============================================================
# powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose logs celery-worker --tail 50"

# ==============================================================
# PLAYWRIGHT -- RUN ALL TESTS
# Must be run from frontend/ directory
# Queue must be clear (active = 0) before running TC-02
# ==============================================================
# cd C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex\frontend
# npx playwright test --reporter=list

# ==============================================================
# PLAYWRIGHT -- FULL PRE-FLIGHT BEFORE RUNNING TESTS
# Run these in order, check each output before proceeding
# ==============================================================
# 1. Check queue
#    docker compose exec postgres psql -U auditex -d auditex -c "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
#
# 2. If active > 0, clear it
#    docker compose exec postgres psql -U auditex -d auditex -c "UPDATE tasks SET status='FAILED', failure_reason='Force-failed' WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING') AND created_at < NOW() - INTERVAL '5 minutes'"
#
# 3. Confirm active = 0
#    docker compose exec postgres psql -U auditex -d auditex -c "SELECT COUNT(*) as active FROM tasks WHERE status IN ('QUEUED','EXECUTING','REVIEWING','FINALISING')"
#
# 4. Run Playwright
#    cd C:\Users\v_sen\Documents\Projects\0001_Hack0014_Vertex_Swarm_Tashi\auditex\frontend
#    npx playwright test --reporter=list

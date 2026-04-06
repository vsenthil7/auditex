"""
Auditex -- Clear Stuck Queue + Full Status Report
Runs in the POSTGRES container (has psql), not the api container.

Run:
  docker compose exec postgres psql -U auditex -d auditex -f /dev/stdin < backend/scripts/db_clear_queue.sql

OR use the PowerShell wrapper below which is easier:
  powershell -ExecutionPolicy Bypass -File run.ps1 -cmd "docker compose exec postgres psql -U auditex -d auditex -c \"SELECT status, COUNT(*) FROM tasks GROUP BY status ORDER BY COUNT(*) DESC\""
"""
# This file is kept for reference — use db_clear_queue.sql instead
print("Use: docker compose exec postgres psql -U auditex -d auditex -f scripts/db_clear_queue.sql")
print("Or run the SQL commands directly — see db_clear_queue.sql")

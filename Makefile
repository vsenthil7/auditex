.PHONY: run stop test lint

run:
	docker compose up -d

stop:
	docker compose down

restart-workers:
	docker compose restart celery-worker

logs:
	docker compose logs -f

test-unit:
	cd backend && python -m pytest tests/unit -v --cov=app --cov=core

test:
	cd backend && python -m pytest tests/ -v

lint:
	cd backend && ruff check . && mypy .

format:
	cd backend && black . && ruff check --fix .

migrate:
	cd backend && alembic upgrade head

shell-db:
	docker compose exec postgres psql -U auditex -d auditex

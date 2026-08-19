.PHONY: help dev worker test lint format migrate migration seed clean frontend

PYTHON = python
UVICORN = uvicorn
ALEMBIC = alembic
PYTEST = pytest

help:
	@echo "Available Commands:"
	@echo "  make dev          Start FastAPI backend dev server with hot-reload"
	@echo "  make worker       Start Celery distributed background worker"
	@echo "  make frontend     Start Next.js frontend development server"
	@echo "  make test         Execute full pytest automated test suite"
	@echo "  make lint         Run static analysis and code checks"
	@echo "  make format       Auto-format codebase using ruff and black"
	@echo "  make migrate      Apply all pending database migrations"
	@echo "  make migration    Generate a new Alembic migration (e.g. make migration msg='add_col')"
	@echo "  make seed         Seed default admin account and initial data"
	@echo "  make clean        Remove cache and compiled bytecode files"

dev:
	cd backend && $(UVICORN) main:app --reload --host 0.0.0.0 --port 8000

worker:
	cd backend && celery -A core.celery_app.celery_app worker --loglevel=info -P solo

frontend:
	cd frontend && npm run dev

test:
	cd backend && $(PYTEST) tests -v --tb=short

lint:
	ruff check backend
	black --check backend

format:
	ruff check --fix backend
	black backend

migrate:
	cd backend && $(ALEMBIC) upgrade head

migration:
	cd backend && $(ALEMBIC) revision -m "$(msg)"

seed:
	cd backend && $(PYTHON) -c "from core.database import SessionLocal; from api.routes_auth import seed_admin_user; db = SessionLocal(); seed_admin_user(db); db.close()"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +

.PHONY: help install dev prod lint format type test \
        migrate upgrade downgrade clean

# -------------------------
# Default
# -------------------------

help:
	@echo "Available commands:"
	@echo "  make install     - Install dependencies + pre-commit"
	@echo "  make dev         - Run development server"
	@echo "  make prod        - Run production server"
	@echo "  make lint        - Run ruff linter"
	@echo "  make format      - Run ruff formatter"
	@echo "  make type        - Run mypy type checking"
	@echo "  make test        - Run pytest"
	@echo "  make migrate     - Create new migration"
	@echo "  make upgrade     - Apply migrations"
	@echo "  make downgrade   - Rollback last migration"
	@echo "  make clean       - Remove cache files"

# -------------------------
# Setup
# -------------------------

install:
	pip install -e ".[dev]"
	pre-commit install

# -------------------------
# Run Server
# -------------------------

dev:
	uvicorn app.main:app --reload

prod:
	uvicorn app.main:app --host 0.0.0.0 --port 8000

# -------------------------
# Code Quality
# -------------------------

lint:
	ruff check .

format:
	ruff format .

type:
	mypy app

# -------------------------
# Tests
# -------------------------

test:
	pytest

# -------------------------
# Database (Alembic)
# -------------------------

migrate:
	alembic revision --autogenerate -m "migration"

upgrade:
	alembic upgrade head

downgrade:
	alembic downgrade -1

# -------------------------
# Cleanup
# -------------------------

clean:
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
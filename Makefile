.PHONY: install dev test test-unit test-int migrate downgrade sync-perms sync-roles bootstrap check-rls lint format

install:
	python -m venv .venv
	.venv/Scripts/python -m pip install --upgrade pip
	.venv/Scripts/python -m pip install -e ".[dev]"

dev:
	.venv/Scripts/python -m uvicorn app.main:app --reload

test:
	.venv/Scripts/python -m pytest

test-unit:
	.venv/Scripts/python -m pytest tests/unit -q

test-int:
	.venv/Scripts/python -m pytest tests/integration -q

migrate:
	.venv/Scripts/python -m alembic upgrade head

downgrade:
	.venv/Scripts/python -m alembic downgrade -1

sync-perms:
	.venv/Scripts/python scripts/sync_permissions.py

sync-roles:
	.venv/Scripts/python scripts/sync_roles.py

bootstrap:
	.venv/Scripts/python scripts/bootstrap.py

check-rls:
	.venv/Scripts/python scripts/check_rls.py

lint:
	.venv/Scripts/python -m ruff check app tests scripts

format:
	.venv/Scripts/python -m ruff format app tests scripts
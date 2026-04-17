PYTHON ?= python
DOCKER_COMPOSE ?= docker compose

.PHONY: install format lint typecheck test run run-worker alembic-upgrade docker-up docker-down

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .[dev]

format:
	$(PYTHON) -m ruff format .

lint:
	$(PYTHON) -m ruff check .

typecheck:
	$(PYTHON) -m mypy app tests

test:
	$(PYTHON) -m pytest

run:
	$(PYTHON) -m uvicorn app.main:app --reload

run-worker:
	$(PYTHON) -m celery -A app.tasks.celery_app.celery_app worker -l info -Q pipeline

alembic-upgrade:
	$(PYTHON) -m alembic upgrade head

docker-up:
	$(DOCKER_COMPOSE) up --build

docker-down:
	$(DOCKER_COMPOSE) down

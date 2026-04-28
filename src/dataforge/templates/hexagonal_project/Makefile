.PHONY: up down migrate install test lint

up:
	docker compose up -d

down:
	docker compose down

install:
	pip install -e .

migrate:
	dfg migrate

test:
	pytest -v

lint:
	ruff check src tests
	ruff format --check src tests

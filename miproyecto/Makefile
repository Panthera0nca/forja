.PHONY: db db-down db-logs test lint fmt clean

db:
	docker compose up -d

db-down:
	docker compose down

db-logs:
	docker compose logs -f postgres

test:
	pytest -v

lint:
	ruff check src tests

fmt:
	ruff format src tests

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +

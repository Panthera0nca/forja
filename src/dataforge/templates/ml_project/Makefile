.PHONY: db db-down db-logs train infer test lint fmt clean

db:
	docker compose up -d

db-down:
	docker compose down

db-logs:
	docker compose logs -f postgres

train:
	python -m {{ package_name }}.pipelines.training

infer:
	python -m {{ package_name }}.pipelines.inference

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
	find . -name "*.joblib" -delete

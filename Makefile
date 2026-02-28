.PHONY: install dev test lint clean docker

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	python -m pytest tests/ -v --tb=short

coverage:
	python -m pytest tests/ --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/
	ruff format --check app/ tests/

format:
	ruff format app/ tests/

clean:
	rm -rf __pycache__ .pytest_cache *.egg-info
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

docker:
	docker compose up -d --build

docker-down:
	docker compose down

run:
	python -m app

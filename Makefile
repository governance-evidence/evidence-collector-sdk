.PHONY: install lint format test cov typecheck check clean pre-commit headers

install:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check src/ tests/ examples/
	ruff format --check src/ tests/ examples/

format:
	ruff check --fix src/ tests/ examples/
	ruff format src/ tests/ examples/

typecheck:
	mypy src/

test:
	pytest --cov=collector --cov-report=term-missing

cov:
	pytest --cov=collector --cov-report=term-missing --cov-report=html

headers:
	python scripts/check_headers.py

pre-commit:
	pre-commit run --all-files

check: lint typecheck test headers

clean:
	rm -rf .mypy_cache .pytest_cache .ruff_cache .hypothesis .coverage htmlcov
	find . -type d -name __pycache__ -exec rm -rf {} +

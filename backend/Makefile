.PHONY: help run test lint format format-check typecheck check clean

help:
	@echo "run          Start the development API server"
	@echo "test         Run the backend test suite"
	@echo "lint         Run Ruff lint checks"
	@echo "format       Format source files with Ruff"
	@echo "format-check Verify formatting without changing files"
	@echo "typecheck    Run mypy"
	@echo "check        Run all verification commands"

run:
	uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

test:
	python -m pytest tests/ -v

lint:
	python -m ruff check src/ tests/

format:
	python -m ruff format src/ tests/

format-check:
	python -m ruff format --check src/ tests/

typecheck:
	python -m mypy src/

check: lint format-check typecheck test

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name .ruff_cache -exec rm -rf {} +

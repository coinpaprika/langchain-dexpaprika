.PHONY: all lint format test integration_tests

all: lint test

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src/

format:
	uv run ruff format .
	uv run ruff check --fix .

test:
	uv run pytest --disable-socket --allow-unix-socket tests/unit_tests/

integration_tests:
	uv run pytest tests/integration_tests/

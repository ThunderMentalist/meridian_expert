.PHONY: install test lint format doctor-demo

install:
	python -m pip install -e .[dev]

test:
	pytest -q

lint:
	ruff check src tests

format:
	ruff check --fix src tests

doctor-demo:
	meridian-expert doctor

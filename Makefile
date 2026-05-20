.PHONY: help test test-v test-integration example notebook

help:
	@echo "make test              run all tests (quiet)"
	@echo "make test-v            run all tests (verbose)"
	@echo "make test-integration  run integration tests only"
	@echo "make example           run examples/modern_greek.py"
	@echo "make notebook          open interactive Marimo notebook"

test:
	uv run pytest -q

test-v:
	uv run pytest -v

test-integration:
	uv run pytest tests/test_integration.py -v

example:
	uv run python examples/modern_greek.py

notebook:
	uv run marimo run examples/modern_greek_notebook.py

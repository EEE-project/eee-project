.PHONY: help test test-v test-integration example-el example-grc notebook-el notebook-grc

help:
	@echo "make test              run all tests (quiet)"
	@echo "make test-v            run all tests (verbose)"
	@echo "make test-integration  run integration tests only"
	@echo "make example-el        run examples/modern_greek.py"
	@echo "make example-grc       run examples/ancient_greek.py"
	@echo "make notebook-el       open Modern Greek Marimo notebook"
	@echo "make notebook-grc      open Ancient Greek Marimo notebook"

test:
	uv run pytest -q

test-v:
	uv run pytest -v

test-integration:
	uv run pytest tests/test_integration.py -v

example-el:
	uv run python examples/modern_greek.py

example-grc:
	uv run python examples/ancient_greek.py

notebook-el:
	uv run marimo run examples/modern_greek_notebook.py

notebook-grc:
	uv run marimo run examples/ancient_greek_notebook.py

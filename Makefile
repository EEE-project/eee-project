.PHONY: help test test-v test-integration example-el example-grc example-unimorph example-backends notebook-el notebook-grc notebook

help:
	@echo "make test                  run all tests (quiet)"
	@echo "make test-v                run all tests (verbose)"
	@echo "make test-integration      run integration tests only"
	@echo "make example-el            run examples/modern_greek.py"
	@echo "make example-grc           run examples/ancient_greek.py"
	@echo "make example-unimorph      run examples/unimorph.py"
	@echo "make example-backends      run examples/backend_selection.py"
	@echo "make notebook              open combined el/grc Marimo notebook"
	@echo "make notebook-el           open Modern Greek Marimo notebook"
	@echo "make notebook-grc          open Ancient Greek Marimo notebook"

test:
	uv run pytest -q

test-v:
	uv run pytest -v

test-integration:
	uv run pytest tests/integration/ -v -m integration

example-el:
	uv run python examples/modern_greek.py

example-grc:
	uv run python examples/ancient_greek.py

example-unimorph:
	uv run python examples/unimorph.py

example-backends:
	uv run python examples/backend_selection.py

notebook-el:
	.venv/bin/marimo edit examples/modern_greek_notebook.py --no-token

notebook-grc:
	.venv/bin/marimo edit examples/ancient_greek_notebook.py --no-token

notebook:
	.venv/bin/marimo edit examples/greek_notebook.py --no-token

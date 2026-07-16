.PHONY: help test test-v check

help:
	@echo "make test / test-v       run tests (quiet / verbose)"
	@echo "make check               run ruff (curated rule set - see pyproject.toml)"
	@echo "make -C examples help    show example and notebook targets"

test:
	uv run python -m pytest -q

test-v:
	uv run python -m pytest -v

check:
	uv run ruff check

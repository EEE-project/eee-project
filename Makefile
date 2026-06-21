.PHONY: help test test-v

help:
	@echo "make test / test-v       run tests (quiet / verbose)"
	@echo "make -C examples help    show example and notebook targets"

test:
	uv run python -m pytest -q

test-v:
	uv run python -m pytest -v

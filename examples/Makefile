.PHONY: help el grc unimorph backends chain hooks comparison notebook-el notebook-grc notebook notebook-unimorph notebook-exercise notebook-config

help:
	@echo "make el                run modern_greek.py"
	@echo "make grc               run ancient_greek.py"
	@echo "make unimorph          run unimorph.py"
	@echo "make backends          run backend_selection.py"
	@echo "make chain             run backend_chain.py"
	@echo "make hooks             run chain_hooks.py"
	@echo "make comparison        run backend_comparison.py"
	@echo "make notebook-el       open modern_greek_notebook.py"
	@echo "make notebook-grc      open ancient_greek_notebook.py"
	@echo "make notebook          open greek_notebook.py"
	@echo "make notebook-unimorph open unimorph_notebook.py"
	@echo "make notebook-exercise open greek_exercise_notebook.py (GreekUtils exercises + vocab quiz)"
	@echo "make notebook-config   open config_store_notebook.py (ConfigStore — from_url / from_file / from_dict)"

el:
	cd .. && uv run python examples/modern_greek.py

grc:
	cd .. && uv run python examples/ancient_greek.py

unimorph:
	cd .. && uv run python examples/unimorph.py

backends:
	cd .. && uv run python examples/backend_selection.py

chain:
	cd .. && uv run python examples/backend_chain.py

hooks:
	cd .. && uv run python examples/chain_hooks.py

comparison:
	cd .. && uv run python examples/backend_comparison.py

notebook-el:
	cd .. && uv run marimo edit examples/modern_greek_notebook.py --no-token

notebook-grc:
	cd .. && uv run marimo edit examples/ancient_greek_notebook.py --no-token

notebook:
	cd .. && uv run marimo edit examples/greek_notebook.py --no-token

notebook-unimorph:
	cd .. && uv run marimo edit examples/unimorph_notebook.py --no-token

notebook-exercise:
	cd .. && uv run marimo edit examples/greek_exercise_notebook.py --no-token

notebook-config:
	cd .. && uv run marimo edit examples/config_store_notebook.py --no-token

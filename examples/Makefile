.PHONY: help el grc unimorph backends chain hooks comparison notebook-el notebook-grc notebook notebook-unimorph notebook-exercise notebook-config notebook-drill export-drill export-greek export-ancient-greek export-modern-greek export-unimorph export-exercise export-all

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
	@echo "make notebook-drill    open modern_greek_drill_notebook.py (paradigm drill — verb/noun/adj, TSV upload)"
	@echo ""
	@echo "make export-drill          export drill demo to dist/drill/"
	@echo "make export-greek          export greek demo to dist/greek/"
	@echo "make export-ancient-greek  export ancient-greek demo to dist/ancient-greek/"
	@echo "make export-modern-greek   export modern-greek demo to dist/modern-greek/"
	@echo "make export-unimorph       export unimorph demo to dist/unimorph/"
	@echo "make export-exercise       export exercise demo to dist/exercise/"
	@echo "make export-all            export all 6 live demos to dist/<name>/"
	@echo "  Each dist/<name>/ mirrors a live-demo directory on the pages branch"
	@echo "  (docs/examples.md) -- exports whatever source is in the current"
	@echo "  working tree, so pull origin/main first. Copy dist/<name>/ into the"
	@echo "  pages-branch worktree, commit, and sync to all 3 mirrors."

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

notebook-drill:
	cd .. && uv run marimo edit examples/modern_greek_drill_notebook.py --no-token

export-drill:
	cd .. && uv run marimo export html-wasm examples/modern_greek_drill_notebook.py -o examples/dist/drill --mode run -f

export-greek:
	cd .. && uv run marimo export html-wasm examples/greek_notebook.py -o examples/dist/greek --mode run -f

export-ancient-greek:
	cd .. && uv run marimo export html-wasm examples/ancient_greek_notebook.py -o examples/dist/ancient-greek --mode run -f

export-modern-greek:
	cd .. && uv run marimo export html-wasm examples/modern_greek_notebook.py -o examples/dist/modern-greek --mode run -f

export-unimorph:
	cd .. && uv run marimo export html-wasm examples/unimorph_notebook.py -o examples/dist/unimorph --mode run -f

export-exercise:
	cd .. && uv run marimo export html-wasm examples/greek_exercise_notebook.py -o examples/dist/exercise --mode run -f

export-all: export-drill export-greek export-ancient-greek export-modern-greek export-unimorph export-exercise
	@echo "All 6 demos exported to examples/dist/ -- copy each into the pages-branch worktree and publish."

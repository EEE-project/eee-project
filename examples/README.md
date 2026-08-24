# Examples

Runnable scripts and notebooks demonstrating the `eee` package. For API docs
rather than examples, see [../docs/api-patterns.md](../docs/api-patterns.md)
(notebook-authoring patterns) and [../docs/api-reference.md](../docs/api-reference.md)
(full function reference).

| File | Description |
|------|-------------|
| [`modern_greek.py`](modern_greek.py) | Verbs, nouns, adjectives — full paradigms (el) |
| [`ancient_greek.py`](ancient_greek.py) | Verbs, nouns, adjectives — full paradigms (grc) |
| [`unimorph.py`](unimorph.py) | UniMorph TSV backend — nouns/adjectives for el and grc |
| [`backend_selection.py`](backend_selection.py) | Named `backend=` selectors |
| [`backend_chain.py`](backend_chain.py) | Fallback chain setup and usage |
| [`chain_hooks.py`](chain_hooks.py) | Pre/post hook examples |
| [`backend_comparison.py`](backend_comparison.py) | Side-by-side: dedicated vs UniMorph coverage |
| [`modern_greek_notebook.py`](modern_greek_notebook.py) | Interactive paradigm viewer — Modern Greek (Marimo) |
| [`ancient_greek_notebook.py`](ancient_greek_notebook.py) | Interactive paradigm viewer — Ancient Greek (Marimo) |
| [`greek_notebook.py`](greek_notebook.py) | Combined interactive notebook — el + grc (Marimo) |
| [`unimorph_notebook.py`](unimorph_notebook.py) | Interactive browser for all 187 UniMorph languages with slot template support |
| [`greek_exercise_notebook.py`](greek_exercise_notebook.py) | `GreekUtils` full demo — verb drills, custom drill, `greek_compare`, vocab quiz (MG + AG) |
| [`config_store_notebook.py`](config_store_notebook.py) | `ConfigStore` demo — `from_url`, `from_file`, `from_dict` with `eee_topbar` |
| [`modern_greek_drill_notebook.py`](modern_greek_drill_notebook.py) | Modern Greek paradigm drill — verb/noun/adjective/pronoun, switchable, with personal vocab TSV upload |

**Live demos:** all 6 interactive notebooks below run in-browser via WebAssembly — no install needed, and each is mirrored on all 3 hosts. Start at a hub page — [GitHub](https://eee-project.github.io/eee-project/) · [GitLab](https://eee-project.gitlab.io/eee-project/) · [Codeberg](https://eee-project.codeberg.page/eee-project/) — or jump directly to a notebook:

- **Paradigm Drill** (`modern_greek_drill_notebook.py`) — [GitHub](https://eee-project.github.io/eee-project/drill/) · [GitLab](https://eee-project.gitlab.io/eee-project/drill/) · [Codeberg](https://eee-project.codeberg.page/eee-project/drill/)
- **Greek Morphology Explorer** (`greek_notebook.py`) — [GitHub](https://eee-project.github.io/eee-project/greek/) · [GitLab](https://eee-project.gitlab.io/eee-project/greek/) · [Codeberg](https://eee-project.codeberg.page/eee-project/greek/)
- **Ancient Greek Morphology** (`ancient_greek_notebook.py`) — [GitHub](https://eee-project.github.io/eee-project/ancient-greek/) · [GitLab](https://eee-project.gitlab.io/eee-project/ancient-greek/) · [Codeberg](https://eee-project.codeberg.page/eee-project/ancient-greek/)
- **Modern Greek Morphology** (`modern_greek_notebook.py`) — [GitHub](https://eee-project.github.io/eee-project/modern-greek/) · [GitLab](https://eee-project.gitlab.io/eee-project/modern-greek/) · [Codeberg](https://eee-project.codeberg.page/eee-project/modern-greek/)
- **UniMorph Browser** (`unimorph_notebook.py`) — [GitHub](https://eee-project.github.io/eee-project/unimorph/) · [GitLab](https://eee-project.gitlab.io/eee-project/unimorph/) · [Codeberg](https://eee-project.codeberg.page/eee-project/unimorph/)
- **Exercise & Quiz Demo** (`greek_exercise_notebook.py`) — [GitHub](https://eee-project.github.io/eee-project/exercise/) · [GitLab](https://eee-project.gitlab.io/eee-project/exercise/) · [Codeberg](https://eee-project.codeberg.page/eee-project/exercise/)

Run directly:

```bash
uv run python examples/modern_greek.py
uv run python examples/unimorph.py
uv run marimo edit examples/greek_notebook.py --no-token
uv run marimo edit examples/unimorph_notebook.py --no-token
uv run marimo edit examples/greek_exercise_notebook.py --no-token
uv run marimo edit examples/config_store_notebook.py --no-token
uv run marimo edit examples/modern_greek_drill_notebook.py --no-token
```

Or via the `Makefile` shortcuts (same scripts, just less typing):

```bash
make -C examples help         # list all example script targets
make -C examples el           # run examples/modern_greek.py
make -C examples grc          # run examples/ancient_greek.py
make -C examples unimorph     # run examples/unimorph.py
make -C examples backends     # run examples/backend_selection.py
make -C examples chain        # run examples/backend_chain.py
make -C examples hooks        # run examples/chain_hooks.py
make -C examples comparison        # run examples/backend_comparison.py
make -C examples notebook-el       # open examples/modern_greek_notebook.py
make -C examples notebook-grc      # open examples/ancient_greek_notebook.py
make -C examples notebook          # open examples/greek_notebook.py
make -C examples notebook-unimorph # open examples/unimorph_notebook.py
make -C examples notebook-exercise # open examples/greek_exercise_notebook.py
make -C examples notebook-config   # open examples/config_store_notebook.py
make -C examples notebook-drill    # open examples/modern_greek_drill_notebook.py
```

`make export-*` (see `make help` for the full list) exports a live demo and
wraps it in the shared deploy shell — `deploy/shell_template.html` +
`deploy/build_shell.py` — so `dist/<name>/` comes out as `index.html`
(loading animation, topbar, source footer) + `notebook.html` (the app),
ready to copy straight into the `pages`-branch worktree.

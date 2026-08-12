# Examples

All examples are in `examples/`:

| File | Description |
|------|-------------|
| `examples/modern_greek.py` | Verbs, nouns, adjectives — full paradigms (el) |
| `examples/ancient_greek.py` | Verbs, nouns, adjectives — full paradigms (grc) |
| `examples/unimorph.py` | UniMorph TSV backend — nouns/adjectives for el and grc |
| `examples/backend_selection.py` | Named `backend=` selectors |
| `examples/backend_chain.py` | Fallback chain setup and usage |
| `examples/chain_hooks.py` | Pre/post hook examples |
| `examples/backend_comparison.py` | Side-by-side: dedicated vs UniMorph coverage |
| `examples/modern_greek_notebook.py` | Interactive paradigm viewer — Modern Greek (Marimo) |
| `examples/ancient_greek_notebook.py` | Interactive paradigm viewer — Ancient Greek (Marimo) |
| `examples/greek_notebook.py` | Combined interactive notebook — el + grc (Marimo) |
| `examples/unimorph_notebook.py` | Interactive browser for all 187 UniMorph languages with slot template support |
| `examples/greek_exercise_notebook.py` | `GreekUtils` full demo — verb drills, custom drill, `greek_compare`, vocab quiz (MG + AG) |
| `examples/config_store_notebook.py` | `ConfigStore` demo — `from_url`, `from_file`, `from_dict` with `eee_topbar` |
| `examples/modern_greek_drill_notebook.py` | Modern Greek paradigm drill — verb/noun/adjective, switchable, with personal vocab TSV upload |

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

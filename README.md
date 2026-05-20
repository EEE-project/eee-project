# eee

Part of [Ελληνικά Εκπαιδευτικά Εργαλεία (EEE) — Greek Language Educational Tools](https://codeberg.org/EEE-project).

Language-agnostic morphology umbrella for the EEE project. Same API for Modern Greek, Ancient Greek, and any future language.

## Development

```bash
make            # show available commands
make test       # run all 116 tests
make example    # run examples/modern_greek.py
make notebook   # open interactive Marimo paradigm browser
```

## Installation

```bash
pip install git+https://codeberg.org/EEE-project/eee.git
```

Requires Python 3.12+.

## Quick Start

```python
import eee

eee.inflect("λύω",      {"Tense": "Pres", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb",      language="el")  # → {"λύω"}
eee.inflect("γυναίκα", {"Gender": "Fem",  "Number": "Plur", "Case": "Gen"},                 "noun",      language="el")  # → {"γυναικών"}
eee.inflect("καλός",   {"Degree": "Pos",  "Gender": "Fem", "Number": "Sing", "Case": "Nom"},"adjective", language="el")  # → {"καλή"}
```

Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).

## Examples

Runnable example scripts are in `examples/`:

| Script | Description |
|--------|-------------|
| `examples/modern_greek.py` | Verbs, nouns, adjectives — full paradigms for Modern Greek (`el`) |
| `examples/modern_greek_notebook.py` | Interactive Marimo notebook — enter any lemma, see its paradigm |

```bash
uv run python examples/modern_greek.py
uv run marimo run examples/modern_greek_notebook.py
```

Ancient Greek (`grc`) examples will be added when a `grc` backend is available.

## API

### `eee.inflect(lemma, features, pos, *, language) → set[str]`

Returns inflected forms matching the UD feature bundle. Returns an empty set if the requested combination doesn't exist in the paradigm.

`pos`: `"verb"`, `"noun"`, `"adjective"`, `"adverb"`

### `eee.analyze(form, language, pos=None) → list[dict]`

Morphological analysis. Not implemented in v0.1 — raises `AnalysisNotSupportedError`.

### `eee.supported_languages() → dict[str, str]`

Returns `{language_code: backend_class_name}` for all registered backends.

### `eee.register_backend(code, instance) → None`

Register a custom backend. Overrides built-ins for the same language code.

### `eee.set_fallback_backend(instance) → None`

Catch-all for all unregistered language codes.

## Adding a Language

Implement two methods and register:

```python
class MyBackend:
    language = "grc"
    def inflect(self, lemma, features, pos): ...
    def analyze(self, form, pos=None): ...

eee.register_backend("grc", MyBackend())
```

Or ship as a package with an entry point:

```toml
[project.entry-points."eee.backends.v1"]
grc = "my_grc_eee.backend:AncientGreekBackend"
```

## Exceptions

| Exception | Raised when |
|-----------|-------------|
| `eee.UnsupportedLanguageError` | No backend registered for `language` |
| `eee.BackendLoadError` | Backend found but failed to load |
| `eee.AnalysisNotSupportedError` | Backend does not implement `analyze()` |

## Status

v0.1.0 — Modern Greek (`el`) built-in. Ancient Greek (`grc`) backend planned.

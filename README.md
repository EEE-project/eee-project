# eee

Part of [Ελληνικά Εκπαιδευτικά Εργαλεία (EEE) — Greek Language Educational Tools](https://codeberg.org/EEE-project).

Language-agnostic morphology umbrella for the EEE project. Same API for Modern Greek (`el`), Ancient Greek (`grc`), and any future language. Language codes follow [ISO 639](https://en.wikipedia.org/wiki/ISO_639).

## Development

```bash
make                # show available commands
make test           # run all tests
make example-el     # run examples/modern_greek.py
make example-grc    # run examples/ancient_greek.py
make notebook-el    # open Modern Greek Marimo notebook
make notebook-grc   # open Ancient Greek Marimo notebook
make notebook       # open combined el/grc Marimo notebook
```

## Installation

```bash
pip install git+https://codeberg.org/EEE-project/eee.git
```

Requires Python 3.12+.

## Quick Start

```python
import eee

# Modern Greek (el) — built-in
eee.inflect("λύω",      {"Tense": "Pres", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb",      language="el")  # → {"λύω"}
eee.inflect("γυναίκα", {"Gender": "Fem",  "Number": "Plur", "Case": "Gen"},                 "noun",      language="el")  # → {"γυναικών"}
eee.inflect("καλός",   {"Degree": "Pos",  "Gender": "Fem", "Number": "Sing", "Case": "Nom"},"adjective", language="el")  # → {"καλή"}

# Ancient Greek (grc) — via ancient-greek-morphology-eee
eee.inflect("λύω",   {"VerbForm": "Fin", "Tense": "Aor", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"}, "verb", language="grc")  # → {"ἔλυσα"}
eee.inflect("θεός",  {"Case": "Gen", "Number": "Sing", "Gender": "Masc"},                   "noun",      language="grc")  # → {"θεοῦ"}
eee.inflect("ἀγαθός",{"Case": "Nom", "Number": "Sing", "Gender": "Fem",  "Degree": "Pos"},  "adjective", language="grc")  # → {"ἀγαθή"}
```

Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).

## Examples

Runnable example scripts are in `examples/`:

| Script | Language | Description |
|--------|----------|-------------|
| `examples/modern_greek.py` | `el` | Verbs, nouns, adjectives — full paradigms |
| `examples/modern_greek_notebook.py` | `el` | Interactive Marimo paradigm viewer |
| `examples/ancient_greek.py` | `grc` | Verbs, nouns, adjectives — full paradigms |
| `examples/ancient_greek_notebook.py` | `grc` | Interactive Marimo paradigm viewer |
| `examples/greek_notebook.py` | `el` / `grc` | Combined interactive notebook — full inflection paradigms for both languages |

```bash
uv run python examples/modern_greek.py
uv run python examples/ancient_greek.py
uv run marimo run examples/modern_greek_notebook.py
uv run marimo run examples/ancient_greek_notebook.py
uv run marimo run examples/greek_notebook.py
```

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

## Backends

| Language | Code | Package |
|----------|------|---------|
| Modern Greek | `el` | built-in |
| Ancient Greek | `grc` | [ancient-greek-morphology-eee](https://codeberg.org/EEE-project/ancient-greek-morphology-eee) |

## Status

v0.3.0

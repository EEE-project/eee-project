# eee

Part of [Ελληνικά Εκπαιδευτικά Εργαλεία (EEE) — Greek Language Educational Tools](https://codeberg.org/EEE-project).

Language-agnostic morphology umbrella for the EEE project. Same API for Modern Greek (`el`), Ancient Greek (`grc`), and any future language. Language codes follow [ISO 639](https://en.wikipedia.org/wiki/ISO_639).

## Development

```bash
make                      # show available commands
make test                 # run all tests
make test-integration     # run integration tests (requires bundled TSV data)
make example-el           # run examples/modern_greek.py
make example-grc          # run examples/ancient_greek.py
make example-unimorph     # run examples/unimorph.py
make example-backends     # run examples/backend_selection.py
make notebook-el          # open Modern Greek Marimo notebook
make notebook-grc         # open Ancient Greek Marimo notebook
make notebook             # open combined el/grc Marimo notebook
```

## Installation

```bash
pip install git+https://codeberg.org/EEE-project/eee.git
```

Requires Python 3.12+.

## Quick Start

```python
import eee

# Modern Greek (el) — default backend
eee.inflect("λύω",      {"Tense": "Pres", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb",      language="el")  # → {"λύω"}
eee.inflect("γυναίκα", {"Gender": "Fem",  "Number": "Plur", "Case": "Gen"},                 "noun",      language="el")  # → {"γυναικών"}

# Modern Greek via UniMorph TSV backend (language= + backend=)
eee.inflect("γυναίκα", {"Case": "Gen", "Number": "Plur"}, "noun", language="el", backend="unimorph")  # → {"γυναικών"}

# Ancient Greek (grc) — via ancient-greek-morphology-eee
eee.inflect("λύω",  {"VerbForm": "Fin", "Tense": "Aor", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"}, "verb", language="grc")  # → {"ἔλυσα"}
eee.inflect("θεός", {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun", language="grc")  # → {"θεοῦ"}

# Ancient Greek via UniMorph (complementary corpus — different lemma coverage)
eee.inflect("βοηθός", {"Case": "Gen", "Number": "Sing"}, "noun", language="grc", backend="unimorph")  # → {"βοηθοῦ"}

# Language inferred from single-language backend names
eee.inflect("λύω", {"Tense": "Pres", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb", backend="modern-greek")   # → {"λύω"}
eee.inflect("θεός", {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun",        backend="ancient-greek")          # → {"θεοῦ"}
```

Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).

## Examples

Runnable example scripts are in `examples/`:

| Script | Description |
|--------|-------------|
| `examples/modern_greek.py` | Verbs, nouns, adjectives — full paradigms (el) |
| `examples/ancient_greek.py` | Verbs, nouns, adjectives — full paradigms (grc) |
| `examples/unimorph.py` | UniMorph TSV backend — nouns/adjectives for el and grc |
| `examples/backend_comparison.py` | Side-by-side: dedicated vs UniMorph coverage |
| `examples/backend_selection.py` | All `backend=` selector forms and language inference |
| `examples/modern_greek_notebook.py` | Interactive Marimo paradigm viewer (el) |
| `examples/ancient_greek_notebook.py` | Interactive Marimo paradigm viewer (grc) |
| `examples/greek_notebook.py` | Combined interactive notebook (el + grc) |

```bash
uv run python examples/modern_greek.py
uv run python examples/unimorph.py
uv run python examples/backend_selection.py
uv run marimo run examples/greek_notebook.py
```

## API

### `eee.inflect(lemma, features, pos, *, language=None, backend=None) → set[str]`

Returns inflected forms matching the UD feature bundle. Returns an empty set if the form doesn't exist in the paradigm.

- `pos`: `"verb"`, `"noun"`, `"adjective"`, `"adverb"`
- `language`: IETF tag — `"el"`, `"grc"`, etc. May be omitted when `backend` maps to exactly one language.
- `backend`: named variant — `"unimorph"`, `"modern-greek"`, `"ancient-greek"`. `None` selects the default.

### `eee.supported_languages() → dict[str, str]`

Returns `{language_code: backend_class_name}` for all registered backends.

### `eee.register_backend(code, instance, backend=None) → None`

Register a custom backend. Pass `backend='name'` to register a named variant alongside the default.

### `eee.register_default_backends() → None`

Register `UniMorphBackend` as the fallback for languages without a dedicated backend. Call once at application startup.

### `eee.set_fallback_backend(instance) → None`

Catch-all for all unregistered language codes.

### `eee.language_info(code) → dict | None`

Return the manifest entry for a language code (name, tier, pos list), or `None` if unknown.

## Backends

| Language | Code | `backend=` | Package |
|----------|------|-----------|---------|
| Modern Greek | `el` | `"modern-greek"` (default) | built-in |
| Modern Greek | `el` | `"unimorph"` | built-in (TSV, ~212k forms, 8 373 lemmas) |
| Ancient Greek | `grc` | `"ancient-greek"` (default) | [ancient-greek-morphology-eee](https://codeberg.org/EEE-project/ancient-greek-morphology-eee) |
| Ancient Greek | `grc` | `"unimorph"` | built-in (TSV, ~44k forms, Byzantine/NT corpus) |

The two `grc` backends have **complementary coverage**: θεός is in `ancient-greek` only; βοηθός is in `unimorph` only.

See [`docs/backends.md`](docs/backends.md) for each backend's source, coverage, and known differences. [`docs/future-work.md`](docs/future-work.md) for future work.

## Adding a Language

Implement two methods and register:

```python
class MyBackend:
    language = "xx"
    def inflect(self, lemma, features, pos, language=None, **kw): ...

eee.register_backend("xx", MyBackend())
# Named variant:
eee.register_backend("xx", MyBackend(), backend="my-backend")
```

Or ship as a package with an entry point:

```toml
[project.entry-points."eee.backends.v1"]
xx = "my_xx_eee.backend:MyBackend"
```

## Exceptions

| Exception | Raised when |
|-----------|-------------|
| `eee.UnsupportedLanguageError` | No backend registered for `language` / `backend` combination |
| `eee.BackendLoadError` | Backend found but failed to load |

## Status

v0.4.0

# eee-project

Part of [Ελληνικά Εκπαιδευτικά Εργαλεία (EEE) — Greek Language Educational Tools](https://codeberg.org/EEE-project).

Language-agnostic morphology umbrella for the EEE project. Same API for Modern Greek (`el`), Ancient Greek (`grc`), and any future language. Language codes follow [ISO 639](https://en.wikipedia.org/wiki/ISO_639).

`eee-project` is a pure framework — no backends are bundled. Install the backend packages you need alongside it.

## Development

```bash
make test                     # run all tests (quiet)
make test-v                   # run all tests (verbose)

make -C examples help         # list example script targets
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
```

## Installation

```bash
pip install git+https://codeberg.org/EEE-project/eee-project.git

# Install the backends you need:
pip install git+https://codeberg.org/EEE-project/modern-greek-backend-eee.git
pip install git+https://codeberg.org/EEE-project/unimorph-backend-eee.git
pip install git+https://codeberg.org/EEE-project/ancient-greek-backend-eee.git
```

Requires Python 3.12+.

## Quick Start

Backends register themselves via entry points when installed, so `inflect()` finds them automatically:

```python
import eee_project as eee

# Modern Greek (el) — requires modern-greek-backend-eee
eee.inflect("λύω",      {"Tense": "Pres", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb", language="el")  # → {"λύω"}
eee.inflect("γυναίκα", {"Gender": "Fem",  "Number": "Plur", "Case": "Gen"},                 "noun", language="el")  # → {"γυναικών"}

# Ancient Greek (grc) — requires ancient-greek-backend-eee
eee.inflect("λύω",  {"VerbForm": "Fin", "Tense": "Aor", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"}, "verb", language="grc")  # → {"ἔλυσα"}
eee.inflect("θεός", {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun", language="grc")  # → {"θεοῦ"}
```

`language=` is required unless `backend` names a single-language backend (e.g. `backend="modern-greek"` infers `language="el"`).

Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).

### Named backends and chains

When multiple backends cover the same language, register them by name and configure a chain:

```python
from modern_greek_backend_eee import ModernGreekBackend
from unimorph_backend_eee import UniMorphBackend

eee.register_backend("el", ModernGreekBackend(),    backend="modern-greek")
eee.register_backend("el", UniMorphBackend("el"), backend="unimorph")
eee.set_chain("el", ["modern-greek", "unimorph"])  # try modern-greek first, fall back to unimorph

# Explicit named backend
eee.inflect("γυναίκα", {"Case": "Gen", "Number": "Plur"}, "noun", language="el", backend="unimorph")

# Chain with attribution
from eee_project import inflect_traced
result = inflect_traced("γυναίκα", {"Case": "Gen", "Number": "Plur"}, "noun", language="el")
print(result.source)   # "el:modern-greek"
print(result.tried)    # ["el:modern-greek"]
```

## Examples

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
| `examples/greek_exercise_notebook.py` | Exercise quiz demo — `GreekUtils`, `eee_topbar`, `greek_compare` (MG + AG) |
| `examples/config_store_notebook.py` | `ConfigStore` demo — `from_url`, `from_file`, `from_dict` with `eee_topbar` |

```bash
uv run python examples/modern_greek.py
uv run python examples/unimorph.py
uv run marimo edit examples/greek_notebook.py --no-token
uv run marimo edit examples/unimorph_notebook.py --no-token
uv run marimo edit examples/greek_exercise_notebook.py --no-token
uv run marimo edit examples/config_store_notebook.py --no-token
```

## API

### `eee.inflect(lemma, features, pos, *, language, backend=None) → set[str]`

Returns inflected forms matching the UD feature bundle. Returns an empty set if the form doesn't exist in the paradigm.

- `pos`: `"verb"`, `"noun"`, `"adjective"`, `"adverb"`
- `language`: IETF tag — `"el"`, `"grc"`, etc. Required unless `backend` names a single-language backend (e.g. `backend="modern-greek"` infers `language="el"`).
- `backend`: named variant — `"unimorph"`, `"modern-greek"`, `"ancient-greek"`. `None` selects the default or runs the registered chain.

### `eee.inflect_traced(lemma, features, pos, *, language, backend=None, chain=None, stop="first") → InflectResult`

Like `inflect()` but returns an `InflectResult` with `.forms`, `.source`, `.tried`, and `.by_backend`.

### `eee.supported_languages() → dict[str, list[str]]`

Returns `{language_code: [entry_point_value, ...]}` for entry-point-discovered backends. Multiple backends may register for the same language code; all are listed. Does not include explicitly registered backends or the fallback.

### `eee.register_backend(code, instance, backend=None) → None`

Register a backend instance. Pass `backend='name'` to register a named variant alongside the default.

### `eee.set_fallback_backend(instance) → None`

Catch-all for all unregistered language codes.

### `eee.set_chain(language, backends, *, pre_hook=None, post_hook=None) → None`

Register an ordered list of backend names for a language. Backends are tried in order; the first non-empty result is returned (`stop="first"`).

- `pre_hook`: `callable(lemma, features, pos, ctx) → (lemma, features, pos)` — transform inputs before the chain runs.
- `post_hook`: `callable(forms, ctx) → set[str]` — transform or supplement results after the chain runs. Used as an LLM gap-filler when `not forms`.

### `eee.language_info(code) → dict | None`

Return the manifest entry for a language code (name, tier, pos list), or `None` if unknown.

### Slot templates

Slot templates map human-readable labels to backend-native tags, enabling structured inflection tables for any language.

```python
from eee_project import SlotTemplate, inflect_slot, get_slot_templates, register_tag_type

# Inflect a single slot
slot = SlotTemplate(label="Present 3sg", tag_type="unimorph", tag="V;PRS;3;SG")
forms = eee.inflect_slot("λύω", slot, "verb", language="el")  # → {"λύει"}

# Pass an explicit backend instance (required for non-registered languages)
from unimorph_backend_eee import UniMorphBackend
backend = UniMorphBackend("jpn")
forms = eee.inflect_slot("歌う", slot, "verb", language="jpn", backend=backend)

# Load a saved TOML template via the active backend
slots = eee.get_slot_templates("verb", terms_lang="en", lang="ail")
# → list[SlotTemplate] or None

# Register a custom tag type
eee.register_tag_type("mytags", lambda backend, lemma, slot, pos, lang: {slot.tag})
```

`SlotTemplate` fields: `label` (str), `tag_type` (str), `tag` (str), `features` (Mapping[str, str] | None).
Built-in tag types: `"unimorph"` (direct tag lookup), `"ud"` (UD features dict via `slot.features`).

For `tag_type="ud"`, `tag` is auto-derived as feature values joined in sorted-key order (e.g. `{"Case": "Nom", "Number": "Sing"}` → `"Nom;Sing"`).

`inflect_slot` accepts an optional `backend=` keyword: a named variant string (e.g. `"unimorph"`), an explicit backend instance, or `None` to use the default registered backend. Pass an instance for languages not registered with eee (e.g. non-bundled UniMorph languages).

## Backends

| Language | Code | `backend=` | Package |
|----------|------|-----------|---------|
| Modern Greek | `el` | `"modern-greek"` | [modern-greek-backend-eee](https://codeberg.org/EEE-project/modern-greek-backend-eee) |
| Modern Greek | `el` | `"unimorph"` | [unimorph-backend-eee](https://codeberg.org/EEE-project/unimorph-backend-eee) |
| Ancient Greek | `grc` | `"ancient-greek"` | [ancient-greek-backend-eee](https://codeberg.org/EEE-project/ancient-greek-backend-eee) |
| Ancient Greek | `grc` | `"unimorph"` | [unimorph-backend-eee](https://codeberg.org/EEE-project/unimorph-backend-eee) |
| Latin | `la` | `"unimorph"` | [unimorph-backend-eee](https://codeberg.org/EEE-project/unimorph-backend-eee) |
| Russian | `ru` | `"unimorph"` | [unimorph-backend-eee](https://codeberg.org/EEE-project/unimorph-backend-eee) |
| Spanish | `es` | `"unimorph"` | [unimorph-backend-eee](https://codeberg.org/EEE-project/unimorph-backend-eee) |
| Turkish | `tr` | `"unimorph"` | [unimorph-backend-eee](https://codeberg.org/EEE-project/unimorph-backend-eee) |

The two `grc` backends have **complementary coverage**: θεός is in `ancient-greek` only; βοηθός is in `unimorph` only.

See [`docs/backends.md`](docs/backends.md) for each backend's source, lemma counts, and known differences.

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

Or ship as a package with an entry point (auto-discovered on install):

```toml
[project.entry-points."eee_project.backends.v1"]
xx = "my_xx_eee.backend:MyBackend"

# Optional: register a friendly name so callers can use backend="my-backend"
[project.entry-points."eee_project.named_backends.v1"]
my-backend = "my_xx_eee.backend:MyBackend"
```

## Exceptions

| Exception | Raised when |
|-----------|-------------|
| `eee.UnsupportedLanguageError` | No backend registered for `language` / `backend` combination |
| `eee.BackendLoadError` | Backend found but failed to load |

## Changelog

**v0.5.0** — `GreekUtils` and `notebook_utils`; slot template system; Latin, Russian, Spanish, Turkish added; new example notebooks.

**v0.4.0** — UniMorph TSV backend extracted to `unimorph-backend-eee`; backend chain machinery (`set_chain`, `inflect_traced`, pre/post hooks); `analyze()` removed.

**v0.3.0** — Combined el/grc Marimo notebook; `eee.supported_languages()`.

## Status

v0.5.0

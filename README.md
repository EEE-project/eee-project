# eee-project

Part of [Ελληνικά Εκπαιδευτικά Εργαλεία (EEE) — Greek Language Educational Tools](https://github.com/EEE-project).

Same API for general Modern/Ancient Greek flavours, with the possibility of
extending language coverage. Language codes follow
[ISO 639](https://en.wikipedia.org/wiki/ISO_639).

🔓 Open source:
- prod — https://github.com/EEE-project/eee-project
- prod mirror — https://gitlab.com/EEE-project/eee-project
- dev — https://codeberg.org/EEE-project/eee-project

💬 Community: https://telegram.me/eee_greek

## Installation

```bash
pip install eee-project

# Install the backends you need:
pip install modern-greek-backend-eee
pip install unimorph-backend-eee
pip install ancient-greek-backend-eee
```

Development version (latest, from Codeberg) — for any of the above, replace
with: `pip install "<name> @ git+https://codeberg.org/EEE-project/<name>.git"`

Requires Python 3.12+.

`eee-project` is a pure framework — no backends are bundled. Install the backend packages you need alongside it.

## Development

```bash
make test                     # run all tests (quiet)
make test-v                   # run all tests (verbose)
make check                    # run ruff (curated rule set - see [tool.ruff.lint] in pyproject.toml)
```

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

When multiple backends cover the same language, register them by name and
configure a chain (e.g. try `modern-greek` first, fall back to `unimorph`).
See [`docs/chains.md`](docs/chains.md) for the full chain API, `stop="all"`
union mode, and hook extension points.

## Greek diachronic coverage

Greek has a continuous documented history of ~3,500 years, with substantial
morphological and phonological change across periods and dialects.

| Variety | Approx. dates | Status |
|---------|--------------|--------|
| Mycenaean (Linear B) | ~1490–1200 BCE | Not covered |
| Arcado-Cypriot | ~1100–300 BCE | Not covered |
| Homeric/Epic | 800–500 BCE | Covered |
| Classical Attic | 480–323 BCE | Covered |
| Koine/Hellenistic | 323 BCE–400 CE | Covered |
| New Testament Greek | ~50–100 CE | Covered |
| Byzantine | 400–1453 CE | Partial |
| Katharevousa | 1830–1976 CE | Partial |
| Standard Demotic | 1976–present | Covered |

The major alphabetic dialects (Attic, Ionic, Doric, Aeolic) share the same
morphological paradigms and differ mainly in phonology and orthography;
Ancient Greek support here follows Classical Attic conventions.

```python
from ancient_greek_backend_eee import AncientGreekBackend

# Query the same lemma under different historical periods
epic  = AncientGreekBackend.for_period("epic")               # Homer
attic = AncientGreekBackend.for_period("attic")               # Classical Attic
koine = AncientGreekBackend.for_period("hellenistic_koine", "roman_koine")  # Septuagint + NT

# Epic verse allows the unaugmented aorist alongside the standard form;
# Attic and Koine require the augment.
form = {"VerbForm": "Fin", "Tense": "Aor", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"}
epic.inflect("λύω", form, "verb")   # {'λῦσα', 'ἔλυσα'}
attic.inflect("λύω", form, "verb")  # {'ἔλυσα'}
koine.inflect("λύω", form, "verb")  # {'ἔλυσα'}
```

See each backend's own README for exact lexicon-level coverage within each period.

## Examples

14 runnable scripts and notebooks in `examples/` — verbs/nouns/adjectives for
el and grc, UniMorph, named backends, chains, hooks, and interactive Marimo
viewers. See [examples/README.md](examples/README.md) for the full catalog and
how to run each one.

## API

Core functions: `inflect()` and `inflect_traced()` (shown in Quick Start above),
`list_lemmas()`/`list_lemmas_traced()`, `analyze()`/`analyze_traced()` (reverse
lookup), `register_backend()`, `set_chain()`, `set_fallback_backend()`,
`supported_languages()`, `language_info()` — plus a slot-template system for
building structured inflection tables, and three exception types
(`UnsupportedLanguageError`, `BackendLoadError`, `PosNotSupportedError`) with
chain-aware failure handling. Full signatures, the slot-template API, writing
a new backend, and exception semantics: [docs/api-reference.md](docs/api-reference.md).

## Backends

| Language | Code | Package |
|----------|------|---------|
| Modern Greek | `el` | [modern-greek-backend-eee](https://github.com/EEE-project/modern-greek-backend-eee) |
| Ancient Greek | `grc` | [ancient-greek-backend-eee](https://github.com/EEE-project/ancient-greek-backend-eee) |

[unimorph-backend-eee](https://github.com/EEE-project/unimorph-backend-eee) adds
a second, TSV-lookup rung for both Greek languages, plus several other
languages (Latin, Russian, Spanish, Turkish, and 187 more on demand) — see its
own README for bundled coverage and how it compares to the dedicated backends
above.

Each backend's own README is the canonical source for its lexicon flavors,
period/dialect coverage, lemma counts, and known limitations —
[modern-greek-backend-eee](https://github.com/EEE-project/modern-greek-backend-eee#readme),
[ancient-greek-backend-eee](https://github.com/EEE-project/ancient-greek-backend-eee#readme),
[unimorph-backend-eee](https://github.com/EEE-project/unimorph-backend-eee#readme).

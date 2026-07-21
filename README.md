# eee-project

Part of [Ελληνικά Εκπαιδευτικά Εργαλεία (EEE) — Greek Language Educational Tools](https://codeberg.org/EEE-project).

Language-agnostic morphology umbrella for the EEE project. Same API for Modern Greek (`el`), Ancient Greek (`grc`), and any future language. Language codes follow [ISO 639](https://en.wikipedia.org/wiki/ISO_639).

## Greek diachronic coverage

Greek has a continuous documented history of ~3,500 years with substantial
morphological and phonological change across periods. Current backends primarily
target two ends of this spectrum, with limited incidental coverage of
intermediate historical stages through `unimorph grc`. This table spans multiple
backends and packages, so it lives here rather than in any single backend's README.

| Variety | Approx. dates | Status |
|---------|--------------|--------|
| Mycenaean (Linear B) | ~1490–1200 BCE | Not covered |
| Arcado-Cypriot (Cypriot Syllabary) | ~1100–300 BCE | Not covered |
| Homeric/Archaic | 800–500 BCE | **Covered (verbs)** — `AncientGreekBackend(lexicons=["homer"])` provides ~2,335 Homeric verb stems with full paradigm generation; nouns/adjectives: Pratt lexicon only (~23/4) |
| Classical Attic | 480–323 BCE | **Partly covered** — hand-authored `lsj` lexicon adds Classical-Attic verbs + nouns via `AncientGreekBackend(lexicons=["pratt","ltrg","lsj"])`; Pratt is the teaching base (20 verbs); `unimorph grc` adds ~2,400 nouns/adjectives but skews Koine/NT |
| Koine / Hellenistic | 323 BCE – 400 CE | **Primary coverage of `unimorph grc`** — Wiktionary-derived dataset is heavily Koine/NT; for verbs: `AncientGreekBackend(lexicons=["lxx","morphgnt"])` adds ~3,300 stems |
| New Testament Greek | ~50–100 CE | **Well covered** — `unimorph grc` (nouns/adj); `AncientGreekBackend(lexicons=["morphgnt"])` (~1,848 verb stems) |
| Byzantine | 400–1453 CE | No dedicated support; some overlap with late Koine via `unimorph grc` |
| Katharevousa | 1830–1976 CE | Partially supported — many forms work, some explicitly suppressed in `modern-greek` |
| Standard Demotic | 1976–present | **Covered** — `modern-greek` (any lemma); UniMorph ell (fixed vocabulary) |

The major alphabetic dialects (Attic, Ionic, Doric, Aeolic) share the same
morphological paradigms; differences are primarily phonological and orthographic
(e.g. Attic -ττ- vs Ionic -σσ-, loss of digamma in Ionic). The `ancient-greek`
backend targets Classical Attic and is not optimised for other dialects.

## Installation

```bash
pip install git+https://codeberg.org/EEE-project/eee-project.git

# Install the backends you need:
pip install git+https://codeberg.org/EEE-project/modern-greek-backend-eee.git
pip install git+https://codeberg.org/EEE-project/unimorph-backend-eee.git
pip install git+https://codeberg.org/EEE-project/ancient-greek-backend-eee.git
```

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

When multiple backends cover the same language, register them by name and configure a chain.
See [`docs/chains.md`](docs/chains.md) for the full chain API, `stop="all"` union mode, and hook extension points.

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

13 runnable scripts and notebooks in `examples/` — verbs/nouns/adjectives for
el and grc, UniMorph, named backends, chains, hooks, and interactive Marimo
viewers. See [docs/examples.md](docs/examples.md) for the full catalog and how
to run each one.

## API

Core functions: `inflect()` and `inflect_traced()` (shown in Quick Start above),
`register_backend()`, `set_chain()`, `set_fallback_backend()`,
`supported_languages()`, `language_info()` — plus a slot-template system for
building structured inflection tables, and two exception types
(`UnsupportedLanguageError`, `BackendLoadError`) with chain-aware failure
handling. Full signatures, the slot-template API, writing a new backend, and
exception semantics: [docs/api-reference.md](docs/api-reference.md).

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

For each backend's source, license, implementation notes, lemma counts, and known
limitations, see its own README: [modern-greek-backend-eee](https://codeberg.org/EEE-project/modern-greek-backend-eee#readme),
[ancient-greek-backend-eee](https://codeberg.org/EEE-project/ancient-greek-backend-eee#readme),
[unimorph-backend-eee](https://codeberg.org/EEE-project/unimorph-backend-eee#readme).

## Changelog

**v0.7.0** — `GreekConfig.polytonic` field for Modern Greek's monotonic diacritics; `noun_paradigm_drill_form` gains `article`/`indefinite` toggles; new `make_paradigm_drill_state` helper; fixed an Enter-key focus-lock race in `make_paradigm_form`; new Modern Greek paradigm-drill exercise in `examples/`.

**v0.6.0** — paradigm-drill exercises, diachronic paradigm tables through Modern Greek, clickable interactive text, stanza-match/translation-presence quizzes, Byzantine lexicon rung, pronoun POS support, `magnify_image()` click-to-zoom images, refactored `eee_topbar`; mobile "Go" button support for `make_paradigm_form`; fixes to `parent_back_url()`/`eee_topbar()` link targets on molab; Google Analytics actually firing (real `anywidget`, not an inert inline `<script>`); notebook markdown tables rendering left-aligned; a dead CSS selector removed.

**v0.5.0** — `GreekUtils` and `notebook_utils`; slot template system; Latin, Russian, Spanish, Turkish added; new example notebooks.

**v0.4.0** — UniMorph TSV backend extracted to `unimorph-backend-eee`; backend chain machinery (`set_chain`, `inflect_traced`, pre/post hooks); `analyze()` removed.

**v0.3.0** — Combined el/grc Marimo notebook; `eee.supported_languages()`.

## Status

v0.7.0

# API Usage Patterns

The `eee` package exposes several layers of API. Choosing the right layer
depends on how much control the notebook needs over morphology routing and
how the results will be displayed.

For formal function signatures, see [api-reference.md](api-reference.md); for
backend chains and hooks, see [chains.md](chains.md).

---

## Setup (every notebook)

Every notebook that uses `eee` must register at least one backend and, when
multiple backends serve the same language, define an ordering between them.

```python
import eee_project as eee
from modern_greek_backend_eee import ModernGreekBackend

mg = ModernGreekBackend()
eee.register_backend("el", mg)               # single backend — no chain needed
```

```python
# grc — teaching notebook (single backend, limited vocabulary)
from eee_project import setup_ancient_greek
from ancient_greek_backend_eee import AncientGreekBackend

ag = AncientGreekBackend(lexicons=["pratt", "ltrg"])   # 20–54 teaching verbs
# AncientGreekBackend(lexicons=["pratt", "ltrg", "homer", "lxx", "morphgnt"])  # full
setup_ancient_greek(ag)   # registers ag as default + named "ancient-greek" backend and sets chain
```

```python
# grc — reading/display notebook (two backends, broad coverage)
import eee_project as eee
from ancient_greek_backend_eee import AncientGreekBackend
from unimorph_backend_eee import UniMorphBackend

eee.register_backend("grc", AncientGreekBackend(lexicons=["homer", "lxx", "morphgnt"]),
                     backend="ancient-greek")   # verbs (~5055) + Pratt nouns/adjectives
eee.register_backend("grc", UniMorphBackend(language="grc"), backend="unimorph")
eee.set_chain("grc", ["ancient-greek", "unimorph"])   # ag first; unimorph fills noun gaps
```

`set_chain` controls which backend `inflect()` and `inflect_traced()` try first.
It does not affect calls that pass `backend=` explicitly. Register the same
backend under its name even when it is the only one — callers that use
`backend="ancient-greek"` need the named registration.

---

## Pattern A — `GreekUtils` (exercise notebooks)

**Use when:** The notebook presents a standard verb/noun checking exercise with
Marimo UI elements (table selection, answer input, progress tracking).

```python
from eee_project import GreekUtils, MODERN_GREEK, ANCIENT_GREEK

# Modern Greek (default) — all positional args
gu = GreekUtils(mg, mo, pd, eee_module=eee)

# Ancient Greek — pd_module omitted (load_data/get_words not used for grc)
gu = GreekUtils(ag, mo, eee_module=eee, config=ANCIENT_GREEK)

# Word-form quiz only (no backend, no pandas — Odyssey-style)
gu = GreekUtils(mo_module=mo)

# All args have defaults — keyword form works in any case:
# gu = GreekUtils(backend=ag, mo_module=mo, eee_module=eee, config=ANCIENT_GREEK)

# Then in exercise cells:
result = gu.check_verb(word, tense, person, number, answer)
result = gu.check_noun(word, case, number, answer)
```

`GreekUtils` encapsulates the full routing chain:

- calls `eee.inflect_slot()` internally when `eee_module=` is provided
- constructs `SlotTemplate` objects from UD feature maps it knows
- returns structured results for Marimo feedback UI

The notebook sees only domain-level calls (`check_verb`, `check_noun`);
`eee` is not visible in exercise cells.

**`config=`** accepts a `GreekConfig` instance (`MODERN_GREEK` or
`ANCIENT_GREEK`) which controls:

| Config field | `MODERN_GREEK` | `ANCIENT_GREEK` |
|---|---|---|
| `language` | `"el"` | `"grc"` |
| noun cases | nom / acc / gen | + dative |
| verb labels | εγώ / εσύ / … | 1 sg / 2 sg / … |
| `indef_articles` | ένας / μια / ένα | `None` |
| `verb_prefix` | `{'future': 'θα'}` | `{}` |
| `compare_diacritics` | `True` (keep accents) | `True` (keep polytonic) |
| `polytonic` | `False` (acute + diaeresis only) | `True` (full mark set) |

`MODERN_GREEK` is the default — existing notebooks require no change. `polytonic` also drives `make_paradigm_form`'s diacritics bar automatically via `paradigm_drill_widgets` — no separate setting needed.

`indef_articles` is data the config carries, not something any Pattern A method reads on its own — pass `noun_paradigm_drill_form(..., indefinite=True)` to actually test it: appends one indefinite-article slot per singular case (indefinite articles don't inflect for plural) after the definite ones, each requiring its article regardless of the separate `article` param. Build the matching label list as `noun_slot_labels(active_cases) + [f"Ind. {l}" for l in noun_slot_labels(noun_indef_cells(active_cases))]`. `noun_indef_cells` no-ops safely (returns `[]`) when `config.indef_articles` is `None` (Ancient Greek) — fine to pass unconditionally from a notebook that doesn't branch on config itself.

**When `eee_module` is omitted**, `GreekUtils` falls back to calling the
backend's `.paradigm()` method directly — same results, bypasses the eee
routing layer. Avoid this for new notebooks: it couples the notebook to the
backend implementation and doesn't benefit from chain resolution or hooks.

---

## Pattern B — Direct API (paradigm display notebooks)

**Use when:** The notebook builds a paradigm table for display, uses two
backends for the same language, or targets Ancient Greek where there is no
`GreekUtils` equivalent.

The pattern has two steps: load the slot structure once, then inflect per slot.

### Step 1 — load slot templates

```python
slots = eee.get_slot_templates("grc", "noun", lang, backend="ancient-greek") or []
```

`get_slot_templates` returns a list of `SlotTemplate` objects, one per
paradigm cell. Each carries:

| Field | Purpose |
|-------|---------|
| `label` | tag string (e.g. `".NSM"`, `"PAI.1S"`) — backends no longer generate language-specific labels |
| `tag`   | same as `label`; used as the dict key when building a `slot_map` |
| `tag_type` | `"ud"` for all regular slots; `"ag-paradigm"` for the adjective `ADV` slot |
| `features` | UD feature dict, or `None` for `ag-paradigm` slots |

Returns `None` if the backend has no template data for that language/pos
combination. Always guard with `or []`.

Pass `backend=` when multiple backends are registered for the same language
and you want a specific one's slot structure. Omit it to use the default.

### Step 2 — inflect per slot

```python
for slot in slots:
    forms = eee.inflect_slot(lemma, slot, "noun", language="grc",
                              backend="ancient-greek")
```

`inflect_slot` reads `slot.tag_type` and dispatches accordingly:
- `"ud"` → calls `backend.inflect(lemma, slot.features, pos)`
- `"ag-paradigm"` → calls the backend's paradigm dispatch (used for the adjective `ADV` slot)
- `"unimorph"` → calls `backend.inflect(lemma, slot.tag, pos)` (raw tag lookup, legacy)

The `backend=` argument to `inflect_slot` must match the backend whose slot
structure was loaded in step 1. Mixing backends between the two calls
(e.g. loading unimorph slots then inflecting with ancient-greek) will
silently return empty sets or wrong forms.

### Caching verb forms

For verb paradigms the same slot may be needed in multiple table rows. Cache
by tag:

```python
slot_map = {s.tag: s for s in eee.get_slot_templates("grc", "verb", lang,
                                                       backend="ancient-greek") or []}
_vcache = {}
def _vf(tag):
    if tag not in _vcache:
        slot = slot_map.get(tag)
        _vcache[tag] = (
            eee.inflect_slot(lemma, slot, "verb", language="grc",
                             backend="ancient-greek")
            if slot else set()
        )
    return _vcache[tag]
```

---

## Choosing between `inflect_slot` and `inflect`

| | `inflect_slot` | `inflect` |
|---|---|---|
| Input | `SlotTemplate` | raw UD features dict |
| Slot labels | yes (from template) | no |
| Backend routing | via `slot.tag_type` | via `language=` / `backend=` |
| Typical caller | notebooks with paradigm tables | `GreekUtils` internals, scripts |
| When to use | you have slots from `get_slot_templates` | you know the UD features directly |

Use `inflect` when you construct the feature dict yourself and don't need
the label/tag machinery — for example, inside `GreekUtils` where the tense
and person are known from the exercise parameters.

---

## `inflect_traced` — chain debugging and word highlighting

`inflect_traced` behaves like `inflect` but returns an `InflectResult` that
includes which backend in the chain produced each form.

```python
result = eee.inflect_traced(lemma, features, pos, language="grc")
# result.forms  — set of surface forms
# result.source — backend name that resolved it, or None
```

Use it when:
- debugging why a word is or isn't returned
- the UI needs to show per-word backend provenance (e.g. colour-coding words
  from `ancient-greek` vs `unimorph` differently in a text display)

The Odyssey notebook uses chain-aware lookups to highlight words that at
least one registered backend recognises.

---

## Notebook utilities

Helper functions for Marimo notebooks, exported from `eee_project`:

### Navigation

```python
from eee_project import eee_topbar, eee_footer, load_ga_config
from eee_project.notebook_utils import eee_hero, eee_card_list

# load GA config from ga.json next to this notebook (returns None if missing)
_ga = load_ga_config(__file__)

# sticky topbar with back link (+ optional GA injection)
eee_topbar(mo, back_url="https://...", lang=lang_sel.value,
           titles={"ru": "Каподистриас", "en": "Kapodistrias"},
           ga_config=_ga)

# index-page hero title block
eee_hero(mo, lang_sel.value, {
    "ru": ("Каподистриас", "Серия уроков"),
    "el": ("Καποδίστριας", "Σειρά μαθημάτων"),
    "en": ("Kapodistrias", "Lesson series"),
})

# index-page lesson/course card list — see "Wiring to eee_card_list" below
eee_card_list(mo, cfg, lang_sel.value)

# source footer bar
eee_footer(mo, lang=lang_sel.value)
```

All four return `mo.Html()` (or `mo.md()` for `eee_card_list`'s load-error
case) and **must be the last expression in a marimo cell** (no trailing
`return`). `eee_hero` and `eee_card_list` both take `lang_fallback=` (default
`"el"`) — the language to fall back to when `lang` has no translation; pass
`lang_fallback="en"` for English-first notebooks.

`eee_topbar` supports two styles via `style=`:

- `style="back"` (default) — `◀ {title}` linking to `back_url`. For content
  pages one level below an index. Pass `back_url=None` or `""` to suppress
  the topbar entirely.
- `style="index"` — for index/landing pages. With no `back_url`: plain,
  non-clickable `{icon} {title}` (default `icon="●"`, this page's own name)
  — a top-level index, or one scoped only to its own level. With `back_url`
  set (an index that links up to a parent index): a real `◀ {parent_titles}`
  link — pass `parent_titles=` (the *parent's* name) alongside `back_url`,
  or the link falls back to `titles` (this page's own name) and mislabels
  itself with the wrong page's name.

```python
# index page with no parent to link to (top-level, or self-contained)
eee_topbar(mo, back_url=None, lang=lang_sel.value,
           titles="Kapodistrias", style="index")

# index page that links up to a parent index
eee_topbar(mo, back_url="https://.../b1greeklanguageandculture/",
           lang=lang_sel.value, titles="Kapodistrias",
           parent_titles="B1: Greek Language and Culture", style="index")
```

For a course-index page one level below a *grouping* index (e.g. Kapodistrias
under the B1 grouping page), use `parent_back_url()` instead of hand-rolling
the parent lookup — it fetches the parent's own `index.tsv` (remote-only;
molab never bundles a parent directory, so there's no local-first check) and
returns its `index_url`. Pass the same parent name as `parent_titles=` so the
link is labeled correctly:

```python
from eee_project.notebook_utils import parent_back_url

back_url = parent_back_url(f"{_ROOT}/modern_greek/b1greeklanguageandculture/index.tsv")
eee_topbar(mo, back_url=back_url, lang=lang_sel.value, titles="Kapodistrias",
           parent_titles="B1: Greek Language and Culture", style="index")
```

Put this in its own cell (no `lang_sel` dependency) alongside the notebook's
`cfg = ConfigStore.from_file_or_url(...)` call, and read `back_url` from the
render cell that actually calls `eee_topbar` — coupling the fetch itself to
`lang_sel` (a very likely UI interaction) re-runs it, including a real
network round-trip on molab, every time the language dropdown changes, even
though the value never depends on language.

#### Google Analytics

`eee_topbar` injects the GA4 gtag script when `ga_config=` is provided.
The config is loaded from a `ga.json` file that lives **outside the
repository** (add `ga.json` to `.gitignore`):

```json
{"measurement_id": "G-XXXXXXXXXX"}
```

```python
_ga = load_ga_config(__file__)          # looks for ga.json next to the notebook
_ga = load_ga_config("/path/to/dir")    # looks for ga.json in that directory
_ga = load_ga_config()                  # looks in the current working directory
```

Returns `None` silently if the file is missing — GA is disabled, the topbar
renders normally. When `back_url` is empty but `ga_config` is set, the topbar
is suppressed but the GA script is still injected.

### Config storage (`ConfigStore`)

`ConfigStore` is a unified abstraction for lesson navigation config and GA
settings. It replaces ad-hoc `pd.read_csv("index.tsv")` / `load_ga_config()`
calls with a single object whose source is swapped at construction time — the
rest of the notebook sees the same accessors regardless.

TSV columns: `url, icon, greek, label, title, desc, index_url`. `url` and
`index_url` are both complete URLs — the TSV owns hosting details, notebook
code never constructs a molab (or any other host's) URL itself.

**Use `from_url`** for molab notebooks (fetch `index.tsv` from Codeberg at
startup, GA config inline):

```python
from eee_project import ConfigStore

_ROOT = "https://codeberg.org/api/v1/repos/EEE-project/created_with_eee/raw"
_cfg = ConfigStore.from_url(
    f"{_ROOT}/ancient_greek/palaestra/index.tsv",   # per-course TSV
    ga=f"{_ROOT}/ga.json",              # shared GA config at repo root
)
```

`ga=` accepts a URL string (fetched as JSON) or a plain dict. `index.tsv`
lives per-course in `created_with_eee`; `ga.json` sits at the repo root and
is shared across all courses. HTTP errors propagate to the caller (bad URL →
startup exception, visible in the kernel log).

**Use `from_file`** for local development (files next to the notebook):

```python
_cfg = ConfigStore.from_file(__file__)   # reads index.tsv + ga.json
```

`from_file` looks for `index.tsv` and `ga.json` in the same directory as
the notebook, then one level up if not found. Missing files are silently
ignored.

**Use `from_dict`** to embed config inline (no file, no network):

```python
_cfg = ConfigStore.from_dict(
    lessons=[
        {"url": "https://molab.marimo.io/notebooks/nb_AAA/app", "icon": "Α", "greek": "Δίδαγμα α'",
         "label": "Занятие 1", "title": "Алфавит", "desc": "Буквы",
         "index_url": "https://molab.marimo.io/notebooks/nb_IDX/app"},
    ],
    ga={"measurement_id": "G-XXXXXXXXXX"},
)
```

**Accessors** (same interface regardless of source):

```python
_cfg.lessons()    # → list[dict] — all lesson rows
_cfg.index_url()  # → str | None — index_url from the first lesson row
_cfg.ga_config()  # → {"measurement_id": "G-..."} | None
```

**Wiring to `eee_topbar`:**

```python
eee_topbar(mo, back_url=_cfg.index_url(), lang=lang_sel.value,
           titles={"ru": "Занятие 1"}, ga_config=_cfg.ga_config())
```

**Wiring to `eee_card_list`** (index/landing pages — renders `_cfg.lessons()`
as a list of cards, one per row, each linking to that row's `url`):

```python
eee_card_list(mo, _cfg, lang_sel.value)
```

Each row needs `url`, `icon`, `greek`, and `label_<lang>`/`title_<lang>`/
`desc_<lang>` columns. `url` is used verbatim, whatever it points to — an
empty `url` renders a disabled "coming soon" card instead. Renders a
translated "couldn't load" message via `mo.md()` instead when
`_cfg.lessons()` is empty.

---

### String comparison

```python
from eee_project import greek_compare, strip_diacritics

# Remove diacritical marks (monotonic and polytonic)
strip_diacritics("λέγε")      # → "λεγε"
strip_diacritics("ἄνθρωπος") # → "ανθρωπος"

# Compare with configurable normalization
greek_compare("λεγε", "λέγε")                          # True  (default: strip accents)
greek_compare("λεγε", "λέγε", diacritics=True)         # False (accents must match)
greek_compare("Λέγε", "λέγε", case_sensitive=True)     # False (case must match)
```

`greek_compare` works for both Modern (monotonic) and Ancient (polytonic)
Greek. `diacritics=False` uses NFD decomposition to strip Unicode category Mn
marks; `diacritics=True` uses NFC normalization so accented forms must agree.

### Grammar labels

```python
from eee_project import fmt_ud_feats

fmt_ud_feats("Tense=Pres|Mood=Ind|Person=1|Number=Sing", "ru")  # → "наст. 1 ед."
fmt_ud_feats("Tense=Pres|Mood=Ind|Person=1|Number=Sing", "en")  # → "pres. 1 sg."
fmt_ud_feats("Case=Nom|Number=Sing|Gender=Masc", "en")           # → "sg. Nom. m."
```

Parses a UD FEATS string and returns a concise human-readable label in `"ru"`,
`"en"`, or `"el"`. Indicative mood is suppressed (it's the unmarked default).
Unknown languages fall back to `"en"`. Malformed strings pass through unchanged.

Used in paradigm display notebooks (e.g. Odyssey) where each slot needs a
readable column or row header rather than a raw UD tag.

### Loading drill data from TSV

For exercises where correct answers are pre-computed from a TSV file using UD
FEATS, `GreekUtils` provides a loader that replaces the `get_slot_templates` →
filter by PAD tag → `inflect_slot` boilerplate:

```python
_IMP = {"VerbForm": "Fin", "Tense": "Pres", "Voice": "Act", "Mood": "Imp"}
VERBS = gu.load_slot_drill(
    Path(__file__).parent / "verbs.tsv",
    {
        "verb": None,   # None = copy the Word column as-is
        "sg": {**_IMP, "Person": "2", "Number": "Sing"},
        "pl": {**_IMP, "Person": "2", "Number": "Plur"},
    },
    pos="verb",
)
# → [{"verb": "λύω", "meaning": "освобождать", "sg": "λῦε", "pl": "λύετε"}, ...]
```

The TSV must have `Word` and `Translation` columns. Each field mapped to `None` gets the word
copied verbatim; each field with a UD features dict gets inflected via
`eee.inflect` using `self._cfg.language`. Pass `backend=` to pin a specific backend instead of the registered chain.
Requires `eee_module=eee` at `GreekUtils` construction — `self._eee.inflect`
is used internally.

**Why not `inflect_slot` with PAD tags?** PAD.2S, PAD.2P etc. are
backend-internal identifiers from ancient-greek-backend-eee. `GreekUtils`
methods use `eee.inflect` with UD FEATS directly — the same level as
`_verb_forms`, `_noun_forms` etc.

### Vocabulary TSV (`ensure_file` + `load_vocab_tsv` / `load_inflected_vocab_tsv`)

For notebooks that show a vocabulary table and run word-quiz / word-drill
exercises, use this pair:

```python
# setup cell — define NB_DIR and NB_REMOTE once
from pathlib import Path as _Path
NB_DIR    = _Path(__file__).parent
NB_REMOTE = f"{cfg.raw_base}/2026_06_23"   # Codeberg raw URL for this lesson

# vocab load cell — flat vocab (Word/Translation columns)
VOCAB_WORDS = gu.load_vocab_tsv(
    "verbs.tsv", "nouns.tsv",          # one or more TSV filenames
    nb_dir=NB_DIR, remote_base=NB_REMOTE,
)
# → [{"form": "λύω", "meaning": "освобождать"}, ...]

# vocab load cell — inflected-text vocab (form/lemma/pos/context/meaning columns)
QUIZ_WORDS_RAW = gu.resolve_word_grammar(
    gu.load_inflected_vocab_tsv("vocab.tsv", nb_dir=NB_DIR, remote_base=NB_REMOTE),
    ag_backend, lang,
)
# → [{"form": "ἔγνω", "lemma": "γιγνώσκω", "pos": "verb", "context": "...",
#     "meaning": "узнал", "grammar_label": "..."}, ...]
```

`load_vocab_tsv` calls `ensure_file` for each filename, then concatenates the
`Word` / `Translation` columns into the standard vocab dict shape consumed by
`word_quiz_form` and `word_drill_form`. `load_inflected_vocab_tsv` is its
peer for inflected-text sources (Odyssey): same `ensure_file`-backed
local-then-remote loading, but the TSV's own `form`/`lemma`/`pos`/`context`/
`meaning` columns are returned as-is (nothing to remap, unlike the flat
case) — pair it with `resolve_word_grammar` to add `grammar_label`.

**`form`/`lemma` and `meaning`/`context` — a real distinction, not aliasing.**
`form` is the surface form being tested; `lemma` is the dictionary/citation
form used for lookup and paradigm generation. Flat vocab (`load_vocab_tsv`
above) has no inflection concept, so `lemma`/`context` are simply absent —
consumers (`word_quiz_feedback`, `build_grc_paradigm_table`) fall back to
`form`/`meaning`. Inflected-text vocab (e.g. Odyssey, built from
`load_inflected_vocab_tsv` + `resolve_word_grammar`) supplies a real `lemma`
that can differ from `form` — e.g. surface `ἔγνω` with lemma `γιγνώσκω` —
and `word_quiz_feedback` shows a "form → lemma" arrow in that case instead of
just the bare form. Don't "simplify" the vocab dict shape by dropping
`lemma`/`context` from the contract — inflected-text vocab needs them.

**Vocab entry schema** (plain reference, not a `TypedDict` — see the note
above for why `lemma`/`context` are optional rather than a design flaw):

| Field           | Status   | Meaning                                              |
|-----------------|----------|-------------------------------------------------------|
| `form`          | required | surface form shown/tested                             |
| `meaning`       | optional | gloss (`meaning_en`/`meaning_el` variants also used)   |
| `lemma`         | optional | dictionary/citation form; falls back to `form`         |
| `context`       | optional | source/context line; falls back to `""`                |
| `pos`           | optional | `"noun"` / `"verb"` / `"adj"` / `"adv"` / etc.          |
| `grammar`       | optional | UD FEATS string (e.g. `"Case=Nom|Number=Sing"`)         |
| `grammar_label` | derived  | human-readable grammar, set by `resolve_word_grammar`   |
| `lexicon_tag`   | optional | source/backend label shown in paradigm table captions   |

**`ensure_file` behaviour:**

```python
path = gu.ensure_file("filename.pdf", nb_dir=NB_DIR, remote_base=NB_REMOTE)
```

- If the file already exists in `nb_dir` — returns its `Path` immediately.
- If missing — tries to download from `{remote_base}/{filename}`.
- On success — saves to `nb_dir` and returns the `Path`.
- **On failure (404, network error, etc.) — prints a one-line warning and
  returns `None`.** The cell continues; only callers that use the return value
  need to guard against `None`.

This means PDF links in homework cells gracefully degrade when the PDF has not
yet been uploaded to the remote — the notebook still loads, vocabulary cells
still run, and only the download warning appears in the kernel log.

### Drill exercises

For custom exercise types — multiple fields per item, non-standard slots —
`GreekUtils` provides a pair of methods:

```python
# Build input widgets (call inside the cell that depends on clear_btn.value)
inputs_2d, rows = gu.make_item_drill_rows(
    items,                          # list of dicts
    ["field_a", "field_b"],        # keys to test per item
    meaning_key="meaning",          # key for the row prompt label (default: "meaning")
    placeholders=["sg…", "pl…"],   # hint text per field; shorter lists are extended with "…"
)
# rows is a list of mo.hstack widgets — splice into mo.vstack alongside buttons
# inputs_2d[i][j] is the mo.ui.text for item i, field j
```

```python
# Check answers on submit
feedback = gu.check_item_drill(
    items, inputs_2d,
    ["field_a", "field_b"],
    field_labels=["sg", "pl"],      # display names per field (default: field key)
    meaning_key="meaning",
    strict=strict_switch.value,     # True/False override; None (default) uses config.compare_diacritics
) if submit_btn.value else []
# feedback is a list of mo.md(…) elements — pass to mo.vstack
```

Empty inputs are silently skipped. Wrong answers show the expected form inline.

**Clear-button pattern:** Inputs are Marimo UI state. To reset them on "Clear",
create them inside a cell that reads `clear_btn.value` as a dependency (`_dep = clear_btn.value`).
Re-execution recreates fresh `mo.ui.text` elements, resetting all fields.

### Word-form quiz (Odyssey-style)

For multiple-choice vocabulary quizzes where the student picks the correct
inflected form from a list of distractors — no backend needed:

```python
# No backend required — construct with mo only
gu = GreekUtils(mo_module=mo)

# Question cell: returns (radio_widget, word_dict)
answer_radio, w = gu.word_quiz_question(cv(), QUIZ_WORDS, lang_sel.value, random)

# Feedback cell: returns a marimo element
mo.vstack([answer_radio,
           gu.word_quiz_feedback(w, answer_radio.value, score(), lang_sel.value,
                                 build_paradigm_table=build_paradigm_table)])
```

`QUIZ_WORDS` is a list of dicts with a required `"form"` key and usually
`"meaning"` / `"meaning_en"` / `"meaning_el"` (for multilingual labels). Inflected-text
vocab (Odyssey-style) may also include `"lemma"` and `"context"` — when `"lemma"`
is absent (flat vocab from `load_vocab_tsv`), consumers fall back to `"form"`.
`"pos"` (`"noun"`, `"verb"`, `"adj"`, `"adv"`) and `"grammar"` (UD FEATS string)
are also optional.

`build_paradigm_table` is an optional `(word_dict, lang=lang) -> str | None`
callable that returns an HTML paradigm table to display on a correct answer.
It runs as a local closure in the notebook (it needs access to `eee` and slot
configs) — pass it as a keyword argument, not as a `GreekUtils` method.

State cells (reactive graph, must live in the notebook):

```python
cv, set_cv = mo.state(None)                           # current word
score, set_score = mo.state({"correct": 0, "total": 0})
remaining, set_remaining = mo.state(None)
```

#### Compact multiple-choice quiz (3-cell API)

`word_quiz_widgets` + `word_quiz_form` replace the separate question cell,
feedback cell, and nav handler with 3 cells:

```python
# Cell 1 — state (12 values for full history navigation)
cv, set_cv                   = mo.state(None)
remaining, set_remaining     = mo.state(None)   # None = uninitialized
score, set_score             = mo.state({"correct": 0, "total": 0})
restore_entry, set_restore   = mo.state(None)
history, set_history         = mo.state([])
future, set_future           = mo.state([])
```

```python
# Cell 2 — widgets (must reference cv() and restore_entry() so marimo resets on each word)
_ = cv(); _ = restore_entry()
answer_radio, next_btn, prev_btn = gu.word_quiz_widgets(
    cv=cv(), remaining=remaining(), vocab=VOCAB,
    restore_entry=restore_entry(),
    history_len=len(history()),
)
```

```python
# Cell 3 — form (handler + display in one call; last expression in the cell)
gu.word_quiz_form(
    cv, set_cv, remaining, set_remaining,
    score, set_score, restore_entry, set_restore,
    history, set_history, future, set_future,
    answer_radio, next_btn, prev_btn,
    vocab=VOCAB,
    title="## Упражнение 1",
    build_paradigm_table=build_lexicon_tabs,  # optional — see below
)
```

Feedback appears immediately when the user selects a radio option. Clicking
"Следующий" before selecting an option re-renders in place without advancing.

`build_paradigm_table=` is optional (default `None`, just the ✓/✗ feedback
line, no table). Pass a `(word_dict, lang=lang) -> str | None` callable — e.g.
`build_lexicon_tabs` or `build_paradigm_table` from
["Ancient Greek paradigm tables"](#ancient-greek-paradigm-tables-odyssey-style)
below — and on a *correct* answer it renders the paradigm table underneath
the feedback line.
Three outcomes: table HTML → shown; `None` (lemma has no paradigm data at
all) → an explicit "`{form}` — отсутствует в парадигме `{lemma}`" fallback
line, never silence; an exception → the exception text, same as
`word_quiz_feedback`. Wrong answers never call it. Prefer `build_lexicon_tabs`
over the plain single-table `build_paradigm_table` here — it adds per-lexicon
tab selectors when a word is attested in more than one AG lexicon (homer/lxx/
morphgnt), falling back to a single table when there's only one.

---

### Write-the-word drill (3-cell API)

For exercises where the student types an inflected form — `word_drill_widgets`
+ `word_drill_form`:

```python
# Cell 1 — state
cv, set_cv                   = mo.state(None)
remaining, set_remaining     = mo.state(None)   # None = uninitialized
score, set_score             = mo.state({"correct": 0, "total": 0})
restore_entry, set_restore   = mo.state(None)
history, set_history         = mo.state([])
future, set_future           = mo.state([])
```

```python
# Cell 2 — widgets (must reference cv() and restore_entry() so marimo resets on each word)
_ = cv(); _ = restore_entry()
write_input, dia, check_btn, prev_btn, next_btn = gu.word_drill_widgets(
    cv=cv(), remaining=remaining(),
    restore_entry=restore_entry(),
    history_len=len(history()),
)
```

```python
# Cell 3 — form (handler + display in one call; last expression in the cell)
gu.word_drill_form(
    cv, set_cv, remaining, set_remaining,
    score, set_score, restore_entry, set_restore,
    history, set_history, future, set_future,
    write_input, dia, check_btn, prev_btn, next_btn,
    vocab=VOCAB,
    title="## Упражнение 2",
)
```

`VOCAB` is a list of dicts with `"meaning"` and `"form"` keys (and whatever
`meaning_key=` / `form_key=` name). The drill shuffles on first run and
again on restart. Prev/Next navigation replays history; the pre-fill
`restore_entry` shows the previous answer so the student can review it.

### Paradigm drill (3-cell API)

For exercises where the student fills in an entire paradigm at once (every
verb-tense form, every noun case) rather than one field — the high-level
sibling of Pattern C's hand-rolled `make_paradigm_form` recipe below.
`paradigm_drill_widgets` + `verb_paradigm_drill_form` / `noun_paradigm_drill_form`
/ `adjective_paradigm_drill_form` collapse that recipe's seven cells down to
three:

```python
# Cell 1 — state (the 10 mo.state() pairs, as one flat call)
(words, set_words, hist, set_hist, msg, set_msg, cap, set_cap,
 entered, set_entered, sub_cnt, set_sub_cnt, prev_cnt, set_prev_cnt,
 nxt_cnt, set_nxt_cnt, entercnt, set_entercnt, restart_cnt,
 set_restart_cnt) = gu.make_paradigm_drill_state(list(VERBS))
```

```python
# Cell 2 — widgets (form + Prev/Next/Restart) + check button, separately
cv = words()[0] if words() else None
form, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
    labels=gu.verb_slot_labels(),
    values=entered().get(cv["form"]) if cv else None,
    history_len=len(hist()), remaining_len=len(words()),
)
check_btn = gu.dirty_check_button(form, cap, cv, "verb_word")
```

```python
# Cell 3 — handler + display in one call (last expression in the cell)
gu.verb_paradigm_drill_form(
    words, set_words, hist, set_hist, msg, set_msg, cap, set_cap,
    entered, set_entered, sub_cnt, set_sub_cnt, prev_cnt, set_prev_cnt,
    nxt_cnt, set_nxt_cnt, entercnt, set_entercnt, restart_cnt, set_restart_cnt,
    cv, form, check_btn, prev_btn, nxt_btn, restart_btn,
    vocab=VERBS, title="## Упражнение 5",
)
```

The state tuple from Cell 1 unpacks directly as the first 20 positional args
of Cell 3's call — same order, no repacking. `check_btn` is built in its own
cell (not bundled into `paradigm_drill_widgets`) because it depends on `cap`,
which changes on every check; bundling it would rebuild `form` from scratch
on each check and lose whatever the student just typed.

For nouns, swap in `noun_paradigm_drill_form` and pass `noun_meta` (from
`gu.noun_drill_meta(cv["form"])` — active cases vary per word for pluralia
tantum) plus two independent toggles:

- `article: bool = True` — require the definite article in each answer
  (`False` checks the bare noun only).
- `indefinite: bool = False` — when `True`, `form`'s labels/slots must
  include one indefinite-article slot per singular case (indefinite
  articles don't inflect for plural), appended after the definite ones and
  always requiring the article regardless of `article`. Build the label
  list as `gu.noun_slot_labels(active_cases, lang=lang) + [f"{ind_prefix} {l}"
  for l in gu.noun_slot_labels(gu.noun_indef_cells(active_cases), lang=lang)]`
  (`ind_prefix` from your own UI strings, or hardcode `"Ind."` if the
  notebook is English-only). No-ops safely when `config.indef_articles` is
  unset (Ancient Greek) — fine to pass unconditionally from a notebook that
  doesn't branch on config itself.

For adjectives, swap in `adjective_paradigm_drill_form` and pass
`mode: str = "simple"` (nominative only, 6 slots — matches
`adjective_slot_labels("simple")`; anything else drills every case in
`config.adj_cases`).

`noun_slot_labels`/`adjective_slot_labels` both take `lang: str = "en"` —
routes through `get_slot_templates(..., terms_lang=lang)`, backed by
`data/labels/{noun,adj}-{lang}.tsv`. Pass the notebook's own
`language_selector.value`; never hand-roll per-language label text in the
notebook itself.

For a verb-tense **selector** (which of present/imperfect/aorist/future/...
to test — distinct from `verb_slot_labels()`'s pronoun slot labels above),
build the dropdown options from `gu.tense_dropdown_options(lang=lang)` →
`{"Continuous Future (Συνεχής Μέλλοντας)": "future_continuous", ...}`,
backed by `data/labels/tense-{lang}.tsv`. Same rule: don't hardcode
per-language tense names in the notebook.

For the paradigm-drill widget's own **chrome** (test headings, Check-button
label, empty-state text, "TSV not found" messages — anything that isn't
grammar content) call `gu.ui_label(key, lang)`, backed by
`data/labels/ui-{lang}.tsv`. Unlike the label methods above this isn't
Config-scoped — the widget chrome is the same across courses. A notebook
that already has ~30 `t_ui("key", lang)` call sites scattered through its
cells doesn't need to touch every one: assign `t_ui = gu.ui_label` once
(after constructing `gu`) instead of defining a local `UI_STRINGS` dict +
`t_ui()` closure, and every existing call site keeps working unchanged.

Pressing Enter in any field locks it read-only until the reply for that
Enter comes back (correct → advance focus to the next field; wrong or last
field → just unlocks) — this recipe implements the reply side of that
protocol correctly, unlike Pattern C's raw `make_paradigm_form` recipe.

---

### Ancient Greek paradigm tables (Odyssey-style)

For notebooks that show inflection paradigm tables for Ancient Greek words
across multiple lexicons (Homer, LXX, MorphGNT, UniMorph):

```python
from eee_project import build_grc_paradigm_table, build_grc_lexicon_tabs

# Backends — typically set up in a shared cell
ag_backend  = AncientGreekBackend(lexicons=["homer", "lxx", "morphgnt"])
ag_homer    = AncientGreekBackend(lexicons=["homer"])
ag_lxx      = AncientGreekBackend(lexicons=["lxx"])
ag_morphgnt = AncientGreekBackend(lexicons=["morphgnt"])
um_backend  = UniMorphBackend(language="grc")

# Create closures once at notebook startup — bound to the backends
build_paradigm_table = eee.build_grc_paradigm_table(ag_backend, um_backend)
build_lexicon_tabs   = eee.build_grc_lexicon_tabs(
    ag_backend, um_backend,
    lexicons={"homer": ag_homer, "lxx": ag_lxx, "morphgnt": ag_morphgnt},
)

# Then in display cells:
html = build_paradigm_table(word_dict)   # single table, word-quiz compatible
html = build_lexicon_tabs(word_dict)     # multi-tab table across lexicons
```

`build_grc_paradigm_table(ag_backend, um_backend, *, lang="ru")` returns a closure:

```python
build_paradigm_table(w, *, _backend=None, _cap=None) -> str | None
```

- `w` — word dict with `"pos"` (`"noun"`, `"verb"`, `"adj"`, `"pronoun"`),
  `"form"` (the tested form to highlight), optionally `"lemma"` (dictionary
  form the paradigm is built from — falls back to `"form"` when absent) and
  `"lexicon_tag"` (caption fallback)
- `_backend=` — override which AG backend inflects (defaults to `ag_backend`)
- `_cap=` — override the caption text shown below the table
- For nouns: falls back to UniMorph when the AG backend returns no forms
- Returns `None` when POS is unsupported or no forms are found at all

`build_grc_lexicon_tabs(ag_backend, um_backend, *, lexicons, el_backend=None, lang="ru")` returns a closure:

```python
build_lexicon_tabs(w) -> str | None
```

- `lexicons` — `dict[str, backend]` mapping lexicon name to its per-lexicon
  backend instance (e.g. `{"homer": ag_homer, "lxx": ag_lxx, "morphgnt": ag_morphgnt}`)
- When a word's `"lexicon_tag"` matches a key in `lexicons`, only that lexicon's
  backend is used; otherwise all available lexicons are shown as CSS radio tabs
- Falls back to UniMorph when no AG lexicon produces any forms
- Highlights the cell that matches `w["form"]` across all tabs
- Drop-in compatible: pass as `build_paradigm_table=build_lexicon_tabs` to
  `word_quiz_feedback` or `word_quiz_form`

Both closures cache slot templates internally — call the factory once at
notebook startup, not once per word.

### Filtering `QUIZ_WORDS_RAW` and coverage highlighting

For inflected-text lessons (Odyssey-style) offering a lexicon filter
(current/Homer/all words), use these instead of hand-rolling the filter
predicates per notebook — the previous per-lesson `_has_displayable_form`/
`_in_homer`/`_words_for_coverage` trio was identical boilerplate duplicated
across every Odyssey lesson:

```python
QUIZ_WORDS = eee.filter_grc_quiz_words(
    QUIZ_WORDS_RAW, filter_mode.value,
    build_paradigm_table=build_paradigm_table,
    lexicons={"homer": ag_homer, "lxx": ag_lxx, "morphgnt": ag_morphgnt},
)
eee.add_labels(QUIZ_WORDS)

WORDS_COMBINED = eee.grc_coverage_words(
    QUIZ_WORDS_RAW, SHOW_COVERAGE.value,
    build_paradigm_table=build_paradigm_table,
    lexicons={"homer": ag_homer, "lxx": ag_lxx, "morphgnt": ag_morphgnt},
)
```

- `filter_grc_quiz_words(words_raw, mode, *, build_paradigm_table, lexicons)`
  — `mode="none"`: no filtering. When `mode` names a lexicon key in `lexicons`
  (e.g. `"homer"`, `"lxx"`, `"morphgnt"`) — the same `lexicons` dict passed to
  `build_grc_lexicon_tabs` above — keep only words whose tested surface form
  actually appears in *that lexicon's own* paradigm (not merely the combined
  paradigm). Any other mode (the "current lexicon" default): just the
  highlighted-form check (not `#f97316` irregular/absent) against the combined
  `build_paradigm_table(w)`.
- `grc_coverage_words(words_raw, mode, *, build_paradigm_table, lexicons)`
  — same filter semantics, but returns a `set[str]` of *normalized surface
  forms* for poem-text highlighting instead of a filtered word-dict list.
  `mode=None` (Python `None`, not the string `"none"`) means highlighting
  is off — empty set.
- Both take the *same* `build_paradigm_table`/`lexicons` you already have in
  scope from Pattern B/setup — no new backend wiring needed.

---

## Pattern C — `make_paradigm_form` (paradigm drill notebooks)

**Use when:** The student fills in a full inflection paradigm (verb conjugation
or noun declension) — one text field per slot — rather than a single answer.

```python
from eee_project import make_paradigm_form
```

`make_paradigm_form(mo, labels)` returns a `mo.ui.anywidget` whose
`.widget.values` is a list of strings (one per label). Use it as the input
surface; wire submission via a button cell that reads `.widget.values`.
Pass `polytonic=False` (or better, `polytonic=config.polytonic` — this is
exactly what `paradigm_drill_widgets` does automatically) to limit the
diacritics bar to acute accent + diaeresis for Modern Greek content, instead
of the full polytonic mark set (default `True`, unchanged behavior).

### Verb paradigm (6 slots)

```python
# Cell 1 — state
w4t, set_w4t     = mo.state(list(WORDS))
hist, set_hist   = mo.state([])
msg, set_msg     = mo.state("")
cap, set_cap     = mo.state(None)
sub_cnt, set_sub = mo.state(0)
prev_cnt, set_prev = mo.state(0)
nxt_cnt,  set_nxt  = mo.state(0)
prev_btn = mo.ui.button(label="Предыдущее", on_click=lambda v: (v or 0) + 1)
nxt_btn  = mo.ui.button(label="Следующее",  on_click=lambda v: (v or 0) + 1)
return (cap, hist, msg, nxt_btn, nxt_cnt, prev_btn, prev_cnt,
        set_cap, set_hist, set_msg, set_nxt, set_prev, set_sub, set_w4t,
        sub_cnt, w4t)
```

```python
# Cell 2 — form (resets widget when word changes)
cv = w4t()[0] if w4t() else None
verb_form = make_paradigm_form(mo, ["1 sg:", "2 sg:", "3 sg:", "1 pl:", "2 pl:", "3 pl:"])
check_btn = mo.ui.button(label="Проверить", on_click=lambda v: (v or 0) + 1)
set_sub(0)
return check_btn, cv, verb_form
```

```python
# Cell 3 — submit (fires on Проверить)
from types import SimpleNamespace as _NS
if (check_btn.value or 0) > sub_cnt():
    set_sub(check_btn.value)
    if cv:
        set_cap(_NS(verb_word=cv["Word"], tense="present",
                    value=list(verb_form.widget.values)))
return
```

```python
# Cell 4 — CHECK (computes verb_ok + verb_fb; downstream cells depend on these)
_c = cap()
verb_ok = False
verb_fb = ""
if cv and _c and getattr(_c, "verb_word", None) == cv["Word"]:
    verb_ok, verb_fb = gu.check_verb_test(cv["Word"], _c, "present")
return verb_fb, verb_ok
```

```python
# Cell 5 — PASS (advances when correct)
if verb_ok:
    set_hist(hist() + [cv])
    set_w4t([w for w in w4t() if w["Word"] != cv["Word"]])
    set_msg(f"✅ {cv['Word']} — {cv['Translation']}")
    set_cap(None)
return
```

```python
# Cell 6 — PREV / NEXT navigation
if (nxt_btn.value or 0) > nxt_cnt():
    set_nxt(nxt_btn.value); set_cap(None); set_sub(0)
    if w4t() and cv:
        set_hist(hist() + [cv])
        set_w4t([w for w in w4t() if w["Word"] != cv["Word"]])

if (prev_btn.value or 0) > prev_cnt():
    set_prev(prev_btn.value); set_cap(None); set_sub(0)
    if hist():
        _p = hist()[-1]
        set_hist(hist()[:-1])
        set_w4t([_p] + [w for w in w4t() if w["Word"] != _p["Word"]])
return
```

```python
# Cell 7 — display
if not w4t():
    _out = mo.md("**✅ Все глаголы пройдены!**")
else:
    _fback = mo.md(verb_fb) if verb_fb else mo.md("")
    _out = mo.vstack([
        mo.md(f"Перевод: **{cv['Translation']}**") if cv else mo.md(""),
        verb_form,
        mo.hstack([check_btn, prev_btn, nxt_btn], justify="end"),
        _fback,
    ])
_out
return
```

### Noun paradigm (8 slots, with article validation)

Use `gu.create_noun_test_ui([cv])` to get `noun_meta` with `.active_cases`;
pass `[f"{n} {c}:" for n,c in noun_meta.active_cases]` as labels.
Pass `article=True` to `check_noun_test` — the library validates the definite
article against `_AG_ARTS` using the backend's gender information. No separate
article stripping or lookup table is needed in the notebook.

```python
# Cell 2 — form
cv = w4t()[0] if w4t() else None
_, _, noun_meta = gu.create_noun_test_ui([cv] if cv else [])
_ac = getattr(noun_meta, "active_cases", [])
noun_form = make_paradigm_form(mo, [f"{n} {c}:" for n, c in _ac])
check_btn = mo.ui.button(label="Проверить", on_click=lambda v: (v or 0) + 1)
set_sub(0)
return check_btn, cv, noun_form, noun_meta
```

```python
# Cell 4 — CHECK
from types import SimpleNamespace as _NS
_c = cap()
noun_ok = False
noun_fb = ""
if cv and _c and getattr(_c, "test_word", None) == cv["Word"]:
    _snap = _NS(test_word=_c.test_word, is_pluralia_tantum=_c.is_pluralia_tantum,
                active_cases=_c.active_cases, value=[v.strip() for v in _c.value])
    noun_ok, noun_fb = gu.check_noun_test(cv["Word"], _snap, article=True)
return noun_fb, noun_ok
```

### Notes

- The widget includes a shared polytonic diacritics bar above the fields.
- `.widget.values` is a plain `list[str]`; all 6/8 values are `""` on init.
- Paste is handled correctly: active diacritic marks are not applied to pasted
  text (Chrome's `insertFromPaste` inputType is whitelisted).
- Requires `anywidget`; raises `ImportError` if not installed.
- Pressing Enter in any field locks it read-only client-side until
  `.widget.focus_request` replies with that field's current
  `.widget.submit_count` as `request_id` (see `make_paradigm_form`'s
  docstring) — this recipe above never does, since it only reacts to the
  Check button, so an Enter press here just locks and self-releases after
  3s with no other effect. Harmless, but if you want Enter to actually
  advance focus, don't hand-roll it on top of this recipe — use the
  "Paradigm drill (3-cell API)" recipe above, which already implements the
  reply side of this protocol correctly.

---

## Decision summary

```
One backend for the language?
  Standard exercise format (verb/noun/adjective quiz)?
    Modern Greek → GreekUtils(mg, mo, pd, eee_module=eee)
    Ancient Greek → GreekUtils(ag, mo, eee_module=eee, config=ANCIENT_GREEK)
  Word-form multiple-choice quiz (Odyssey-style, no backend)?
    compact: → GreekUtils(mo_module=mo) + word_quiz_widgets + word_quiz_form
    low-level: → word_quiz_question + word_quiz_feedback
  Write-the-word drill (typed input, history navigation, no backend)?
    → GreekUtils(mo_module=mo) + word_drill_widgets + word_drill_form
  Custom display / non-standard UX?
    → get_slot_templates + inflect_slot   (or inflect for raw UD)
Two backends for the same language?
  → register both with backend= names, set_chain for fallback
  → pass backend= to get_slot_templates and inflect_slot in each table section
Need to know which backend resolved a form?
  → inflect_traced
Need to compare student input against correct forms?
  → greek_compare(student, correct, diacritics=config.compare_diacritics)
Drill data comes from a TSV with pre-computed slot answers?
  → gu.load_slot_drill(path, {field: ud_feats_dict, ...}, pos)
Custom drill (multiple fields per item, all shown at once)?
  → gu.make_item_drill_rows + gu.check_item_drill
Multi-field drill with Prev/history?
  → expand items to flat VERB_ENTRIES (one per field) + word_drill_widgets + word_drill_form
Need a readable label for a UD FEATS string?
  → fmt_ud_feats(grammar_str, lang)
Want Google Analytics in the notebook?
  → load_ga_config(__file__) + ga_config= on eee_topbar; add ga.json to .gitignore
Need to manage lesson nav config + GA together (molab or local)?
  → ConfigStore.from_url(codeberg_raw_url, ga={...})  (molab — fetch TSV at startup)
  → ConfigStore.from_file(__file__)                    (local dev — index.tsv + ga.json)
Paradigm table for an Ancient Greek word-form quiz?
  → build_grc_paradigm_table(ag, um) + build_grc_lexicon_tabs(ag, um, lexicons={...})
  → pass build_lexicon_tabs as build_paradigm_table= to word_quiz_feedback or word_quiz_form
Student fills in a full paradigm (verb conjugation / noun declension)?
  → make_paradigm_form(mo, labels) + check_verb_test / check_noun_test (Pattern C)
```

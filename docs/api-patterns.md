# API Usage Patterns

The `eee` package exposes several layers of API. Choosing the right layer
depends on how much control the notebook needs over morphology routing and
how the results will be displayed.

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
import eee_project as eee
from ancient_greek_backend_eee import AncientGreekBackend

ag = AncientGreekBackend(lexicons=["pratt", "ltrg"])   # 20–54 teaching verbs
# AncientGreekBackend(lexicons=["pratt", "ltrg", "homer", "lxx", "morphgnt"])  # full
eee.register_backend("grc", ag, backend="ancient-greek")
eee.set_chain("grc", ["ancient-greek"])
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
| `compare_diacritics` | `True` (keep accents) | `False` (strip accents) |

`MODERN_GREEK` is the default — existing notebooks require no change.

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

# load GA config from ga.json next to this notebook (returns None if missing)
_ga = load_ga_config(__file__)

# sticky topbar with back link (+ optional GA injection)
eee_topbar(mo, back_url="https://...", lang=lang_sel.value,
           titles={"ru": "Каподистриас", "en": "Kapodistrias"},
           ga_config=_ga)

# source footer bar
eee_footer(mo, lang=lang_sel.value)
```

Both return `mo.Html()` and **must be the last expression in a marimo cell**
(no trailing `return`).

`eee_topbar` supports two styles via `style=`:

- `style="back"` (default) — `◀ {title}` linking to `back_url`. For content
  pages one level below an index. Pass `back_url=None` or `""` to suppress
  the topbar entirely.
- `style="index"` — `{icon} {title}` (default `icon="●"`). For index/landing
  pages. Linked to `back_url` when given (an index that points up to a
  parent index), plain text when not (a top-level index, or one scoped only
  to its own level) — the topbar still renders, it just isn't clickable.

```python
# index page with no parent to link to (top-level, or self-contained)
eee_topbar(mo, back_url=None, lang=lang_sel.value,
           titles="Kapodistrias", style="index")

# index page that links up to a parent index
eee_topbar(mo, back_url="https://.../created_with_eee/", lang=lang_sel.value,
           titles="Kapodistrias", style="index")
```

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
settings. It replaces ad-hoc `pd.read_csv("lessons.tsv")` / `load_ga_config()`
calls with a single object whose source is swapped at construction time — the
rest of the notebook sees the same accessors regardless.

TSV columns: `nb_id, icon, greek, label, title, desc, index_url`.

**Use `from_url`** for molab notebooks (fetch `lessons.tsv` from Codeberg at
startup, GA config inline):

```python
from eee_project import ConfigStore

_ROOT = "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main"
_cfg = ConfigStore.from_url(
    f"{_ROOT}/palaestra/lessons.tsv",   # per-course TSV
    ga=f"{_ROOT}/ga.json",              # shared GA config at repo root
)
```

`ga=` accepts a URL string (fetched as JSON) or a plain dict. `lessons.tsv`
lives per-course in `created_with_eee`; `ga.json` sits at the repo root and
is shared across all courses. HTTP errors propagate to the caller (bad URL →
startup exception, visible in the kernel log).

**Use `from_file`** for local development (files next to the notebook):

```python
_cfg = ConfigStore.from_file(__file__)   # reads lessons.tsv + ga.json
```

`from_file` looks for `lessons.tsv` and `ga.json` in the same directory as
the notebook, then one level up if not found. Missing files are silently
ignored.

**Use `from_dict`** to embed config inline (no file, no network):

```python
_cfg = ConfigStore.from_dict(
    lessons=[
        {"nb_id": "nb_AAA", "icon": "Α", "greek": "Δίδαγμα α'",
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
fmt_ud_feats("Tense=Pres|Mood=Ind|Person=1|Number=Sing", "en")  # → "pres 1 sing"
fmt_ud_feats("Case=Nom|Number=Sing|Gender=Masc", "en")           # → "nom sing masc"
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
    strict=strict_switch.value,     # passed as diacritics= to greek_compare
) if submit_btn.value else []
# feedback is a list of mo.md(…) elements — pass to mo.vstack
```

Empty inputs are silently skipped. Wrong answers show the expected form inline.

**Clear-button pattern:** Inputs are Marimo UI state. To reset them on "Clear",
create them inside a cell that reads `clear_btn.value` as a dependency (`_dep = clear_btn.value`).
Re-execution recreates fresh `mo.ui.text` elements, resetting all fields.

### Single-input slot drill

For exercises that step through fields one at a time — one text box, one item,
one field — `GreekUtils` provides a state-machine pair:

```python
# State cells (must live in the notebook — one cell each)
cv, set_cv           = mo.state(None)
remaining, set_remaining = mo.state(None)
field_idx, set_field_idx = mo.state(0)
score, set_score     = mo.state({"correct": 0, "total": 0})

# Input widgets cell (recreated on each state change)
write_input = gu.diacritics_text(placeholder="Greek word…")
check_btn   = mo.ui.button(label="✓ Check")
next_btn    = mo.ui.button(label="→ Next")
```

```python
# Handler cell — call unconditionally; no-op when next_btn.value is falsy
FIELDS = [("verb", "словарная форма"), ("sg", "ед."), ("pl", "мн.")]
gu.slot_drill_advance(
    next_btn.value, write_input.value.strip(),
    cv(), remaining(), field_idx(), score(),
    FIELDS, VERBS, random,
    set_cv, set_remaining, set_field_idx, set_score,
)
```

```python
# Display cell — last expression in the cell
gu.slot_drill_display(
    cv(), field_idx(), score(), write_input, check_btn, next_btn,
    fields=FIELDS,
    title="## Упражнение 1",
    n_items=len(VERBS),
    # meaning_key="meaning"    # default — key in each item dict used as prompt
    # prompt_sep="—"           # default — separator between meaning and field label
)
```

`VERBS` is a list of dicts with the field keys from `FIELDS` plus a `"meaning"` key
(or whichever key `meaning_key` names). Typically produced by `gu.load_slot_drill()`.

`prompt_sep` lets you customise the prompt: `prompt_sep="→"` renders
`*μικρός (маленький)* → **наречие**` instead of the default dash.

`gu.diacritics_text(placeholder=…)` is a convenience wrapper around the
module-level `diacritics_text(mo, *, placeholder, label)` — a polytonic
diacritics bar + text input widget that returns a `.value` string (drop-in for
`mo.ui.text`). Falls back to plain `mo.ui.text` when `anywidget` is unavailable.

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

`QUIZ_WORDS` is a list of dicts with keys `"form"`, `"lemma"`, `"context"`, and
optionally `"meaning"` / `"meaning_en"` / `"meaning_el"` (for multilingual labels),
`"pos"` (`"noun"`, `"verb"`, `"adj"`, `"adv"`), and `"grammar"` (UD FEATS string).

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

---

## Decision summary

```
One backend for the language?
  Standard exercise format (verb/noun/adjective quiz)?
    Modern Greek → GreekUtils(mg, mo, pd, eee_module=eee)
    Ancient Greek → GreekUtils(ag, mo, eee_module=eee, config=ANCIENT_GREEK)
  Word-form multiple-choice quiz (Odyssey-style, no backend)?
    → GreekUtils(mo_module=mo) + word_quiz_question / word_quiz_feedback
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
Single-input drill (one field at a time, state-machine advance)?
  → gu.slot_drill_advance + gu.slot_drill_display
Need a readable label for a UD FEATS string?
  → fmt_ud_feats(grammar_str, lang)
Want Google Analytics in the notebook?
  → load_ga_config(__file__) + ga_config= on eee_topbar; add ga.json to .gitignore
Need to manage lesson nav config + GA together (molab or local)?
  → ConfigStore.from_url(codeberg_raw_url, ga={...})  (molab — fetch TSV at startup)
  → ConfigStore.from_file(__file__)                    (local dev — lessons.tsv + ga.json)
```

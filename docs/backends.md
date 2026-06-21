# Backends

The `eee` package routes inflection requests to different backends. Each is
backed by a different lexicon or algorithm.

Greek has a continuous documented history of ~3,500 years with substantial
morphological and phonological change across periods. Current backends primarily
target two ends of this spectrum, with limited incidental coverage of
intermediate historical stages through `unimorph grc`.

| Variety | Approx. dates | Status |
|---------|--------------|--------|
| Mycenaean (Linear B) | ~1490–1200 BCE | Not covered |
| Arcado-Cypriot (Cypriot Syllabary) | ~1100–300 BCE | Not covered |
| Homeric/Archaic | 800–500 BCE | **Covered (verbs)** — `AncientGreekBackend(lexicons=["homer"])` provides ~2,335 Homeric verb stems with full paradigm generation; nouns/adjectives: Pratt lexicon only (~23/4) |
| Classical Attic | 480–323 BCE | **Partly covered** — `ancient-greek` default (20 verbs, Pratt); `unimorph grc` adds ~2,400 nouns/adjectives but skews Koine/NT |
| Koine / Hellenistic | 323 BCE – 400 CE | **Primary coverage of `unimorph grc`** — Wiktionary-derived dataset is heavily Koine/NT; for verbs: `AncientGreekBackend(lexicons=["lxx","morphgnt"])` adds ~3,300 stems |
| New Testament Greek | ~50–100 CE | **Well covered** — `unimorph grc` (nouns/adj); `AncientGreekBackend(lexicons=["morphgnt"])` (~1,848 verb stems) |
| Byzantine | 400–1453 CE | No dedicated support; some overlap with late Koine via `unimorph grc` |
| Katharevousa | 1830–1976 CE | Partially supported — many forms work, some explicitly suppressed in `modern-greek` |
| Standard Demotic | 1976–present | **Covered** — `modern-greek` (any lemma); UniMorph ell (fixed vocabulary) |

The major alphabetic dialects (Attic, Ionic, Doric, Aeolic) share the same
morphological paradigms; differences are primarily phonological and orthographic
(e.g. Attic -ττ- vs Ionic -σσ-, loss of digamma in Ionic). The `ancient-greek`
backend targets Classical Attic and is not optimised for other dialects.

---

## Ancient Greek (`language="grc"`)

### `ancient-greek` backend (default)

**Source**

[greek-inflexion-eee](https://codeberg.org/EEE-project/greek-inflexion-eee), a
packaged fork of James Tauber's
[greek-inflexion](https://github.com/jtauber/greek-inflexion). License: **MIT**.

Per the upstream README, the library "can precisely generate (i.e. without
over-generation) all the forms in the verbal paradigms in Louise Pratt's _The
Essentials of Greek Grammar_, Helma Dik's _Nifty Greek Handouts_, and Keller
and Russell's _Learn to Read Greek_. It can also generate the nouns in Pratt."
In the EEE package, nominal coverage remains limited to those Pratt nouns.

**Period:** Classical Attic Greek (~5th–4th century BCE). Accentuation logic
broadly follows Classical Attic conventions. Ionic and Doric forms are not
generated.

**Implementation**

Rule-based generator. A YAML stem database stores principal stems
(e.g. `βαλλ`, `βαλ`) for each lemma; `stemming.yaml` maps morphological keys
to stem-slots and endings; a separate accentuation engine applies Attic accent
rules. Forms are generated on demand — not pre-computed.

Adding a new lemma requires annotating its principal stems; the rule engine
then generates the full paradigm automatically.

**Coverage**

| POS | Lemmas |
|-----|-------:|
| Verb | 20–5055 (depends on `lexicons=`) |
| Noun | 23 |
| Adjective | 4 |

**Verb lexicons**

Pass one or more named lexicons at construction time:
`AncientGreekBackend(lexicons=["homer"])`. Nouns and adjectives always use
the Pratt paradigm lexicon regardless.

| Name | Verbs | Period / dialect |
|------|------:|-----------------|
| `"pratt"` (default) | 20 | teaching |
| `"dik"` | 10 | teaching |
| `"ltrg"` | 34 | teaching |
| `"homer"` | 2335 | Epic/Ionic, ~800 BCE |
| `"lxx"` | 1905 | Biblical κοινή, ~250–100 BCE |
| `"morphgnt"` | 1848 | κοινή, ~1st c. CE |

Multiple names are merged additively. Absolute file paths (same YAML format)
are also accepted for project-specific vocabulary.

**Limitations**

- Two-termination adjectives (ἀληθής, ἄδικος) share Masc/Fem forms. The
  database stores only Fem keys for oblique cases; `eee` falls back to Fem
  automatically when a Masc key is absent.
- Nominal coverage is limited to Pratt. Nouns from Dik and Keller/Russell are
  not yet included.

---

### `unimorph` backend — `grc.tsv`

**Source**

[UniMorph](https://unimorph.github.io/) Ancient Greek dataset, derived from
Wiktionary's Ancient Greek inflection tables. Distributed via the
`unimorph-backend-eee` package. License: **CC BY-SA 3.0** (see `NOTICE`).

**Period:** Predominantly Koine/New Testament, without period labelling.
Wiktionary's Ancient Greek coverage is skewed toward NT and early Christian
vocabulary (e.g. ἄγγελος, ἀγαπητός, ἁγιασμός dominate the dataset). Classical
Attic literary words (ἄναξ, ξεῖνος, ἔπος, μῦθος, κλέος) are mostly absent;
Homeric vocabulary is not meaningfully covered.

**Implementation**

Static lookup table: each row is `lemma → form → tag`. No rule engine — absent
cells stay empty.

Tag format: `N;CASE;NUMBER` for nouns (gender omitted);
`ADJ;CASE;NUMBER;GENDER` for adjectives.

**Coverage**

| POS | Lemmas |
|-----|-------:|
| Noun | 2,224 |
| Adjective | 207 |
| Verb | 0 |

**Limitations**

- No verb data in the grc UniMorph dataset. Use the `ancient-greek` backend for
  verbs.
- Noun tags omit gender — passing `Gender` in the feature bundle returns an
  empty set. Gender cannot be inferred from the TSV alone, so the notebooks fall
  back to bare forms for nouns (no definite article).

---

## Modern Greek (`language="el"`)

### `modern-greek` backend (default)

**Source**

[modern-greek-inflexion-eee](https://github.com/EEE-project/modern-greek-inflexion-eee),
a fork of Picus Zeus's
[modern-greek-inflexion](https://github.com/PicusZeus/modern-greek-inflexion).
Deployed at [ellinika.com.pl](https://ellinika.com.pl). License: **MIT**.

Per the upstream README, the library "works thanks to a big corpus on which it
tests forms it tries to create." Word lists from
[Wikileksiko](https://wikilex.gr/) are used as lexical reference data for
accentuation and declension details (genitive existence, vocative endings in
-ος nouns).

**Period:** Standard Modern Greek (Demotic, post-1976). Primarily targets Νέα
Ελληνική Κοινή after the 1976 language reform that established Demotic as the
official standard. Some archaic forms are explicitly suppressed.

**Implementation**

Rule-based algorithm. Accepts any lemma as input, applies Modern Greek
morphological rules, and validates candidate forms against the corpus. Returns
an empty set only when the lemma is unrecognizable. Because there is no finite
lexicon, `list_lemmas()` is not supported for this backend and no corpus table
is shown in the notebooks.

**Coverage**

Accepts any valid Modern Greek lemma (unbounded).

**Limitations**

- Perfect and pluperfect not modeled — these tenses are periphrastic in Modern
  Greek (`έχω γράψει`, `είχα γράψει`) and require a separate auxiliary.
  `eee.inflect()` returns an empty set for `{"Tense": "Perf"}` or
  `{"Tense": "Pqp"}`.
- Some Katharevousa forms are explicitly suppressed.

---

### `unimorph` backend — `ell.tsv`

**Source**

[UniMorph](https://unimorph.github.io/) Modern Greek dataset, derived from
Wiktionary's Modern Greek inflection tables. Distributed via the
`unimorph-backend-eee` package. License: **CC BY-SA 3.0** (see `NOTICE`).

**Period:** Contemporary Standard Modern Greek (Demotic).

**Implementation**

Static lookup table. Particle prefixes (θα/να) present in the raw TSV are
stripped during index load; display code re-adds the appropriate prefix at
render time. `eee.inflect()` always returns bare forms.

Tag format: verbs use aspect tags (`IPFV`/`PFV`) rather than tense labels;
nouns use `N;CASE;NUMBER` (gender omitted).

**Coverage**

| POS | Lemmas |
|-----|-------:|
| Verb | 1,094 |
| Noun | 8,351 |
| Adjective | 2,492 |

**Limitations**

- Noun tags omit gender — passing `Gender` returns an empty set; the notebooks
  fall back to bare forms for nouns (no definite article).
- In the current `ell.tsv`, imperative entries are tagged `V;2;SG;IMP`
  with no aspect distinction — Cont/Aor imperatives return identical forms with
  this backend.
- Perfect cells contain the perfective-stem verbal adjective (e.g.
  `αγαναχτήσει`), not a finite form; the same string is returned for all
  person/number combinations.
- The Wiktionary scrape occasionally includes alternate Aor 3pl forms in `-αν`
  alongside the standard `-σαν`; the result set may be a superset of the
  `modern-greek` backend for those cells.

---

## Backend comparison — Modern Greek verbs

| Feature | `modern-greek` | `unimorph` |
|---------|:--------------|:-----------|
| Perfect / pluperfect | empty set | verbal adjective (same form for all persons) |
| Imp Cont vs Imp Aor | correctly distinct | identical (no aspect tag in bundled `ell.tsv`) |
| Aor 3pl | standard -σαν only | may include -αν variant |
| Particle prefix (θα/να) | not included | stripped on load, re-added on display |


---

## Other languages via UniMorph

Latin, Russian, Spanish, and Turkish are supported via the `unimorph` backend
(`unimorph-backend-eee`). Coverage is a static lookup from UniMorph 4.0 TSV
files derived from Wiktionary. License: **CC BY-SA 3.0**.

| Language | Code | Noun lemmas | Adj lemmas | Verb lemmas |
|----------|------|------------:|-----------:|------------:|
| Latin    | `la` | 13,436 | 9,072 | 0 |
| Russian  | `ru` | 15,682 | 5,365 | 0 |
| Spanish  | `es` | 48,353 | 16,984 | 0 |
| Turkish  | `tr` | 2,924  | 0 | 0 |

**Limitations:** No verb data exists for these languages in the bundled UniMorph
datasets. Noun tags omit gender (same as `grc`/`ell` — passing `Gender` returns
an empty set). No dedicated backend or chain is registered by default; callers
must pass an explicit `backend=` or instantiate `UniMorphBackend(lang)` directly.

---

## Backend chains

eee supports **backend chains** — an ordered list of backends tried in sequence
for a given language. Chains have no defaults and must be registered explicitly
at application startup:

```python
import eee
from ancient_greek_backend_eee import AncientGreekBackend
from unimorph_backend_eee import UniMorphBackend

eee.register_backend("grc", AncientGreekBackend(), backend="ancient-greek")
# or select a corpus lexicon:
# AncientGreekBackend(lexicons=["homer"])                     # Homeric (~2335 verbs)
# AncientGreekBackend(lexicons=["homer", "lxx", "morphgnt"])  # all corpora (~5055 verbs)
eee.register_backend("grc", UniMorphBackend(), backend="unimorph")
eee.set_chain("grc", ["ancient-greek", "unimorph"])
```

When `inflect(lemma, features, pos, language="grc")` is called with `backend=None`
and a chain is registered, the chain runs with `stop="first"`: backends are tried in
order and the first non-empty result is returned. Callers that pass an explicit
`backend=` bypass the chain entirely.

### Chain API

```python
from eee import set_chain, get_chain, inflect_traced

# Override the default chain for grc
set_chain("grc", ["ancient-greek", "unimorph"])

# Per-call chain override (does not modify the registry)
result = inflect_traced("θεός", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "noun",
                        language="grc", chain=["unimorph", "ancient-greek"])

# Union mode — aggregate results from all backends
result = inflect_traced("θεός", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "noun",
                        language="grc", stop="all")
```

`inflect_traced()` returns an `InflectResult` with:
- `forms` — the inflected forms
- `source` — backend key that produced the result (e.g. `"grc:unimorph"`), or `None` for `stop="all"`
- `tried` — backend keys attempted in order
- `by_backend` — maps each backend key that ran to the forms it returned; useful for attribution with `stop="all"`

### Hook extension points

Hooks are optional callables that wrap the chain for preprocessing or
post-processing:

```python
from eee import HookContext

def normalize(lemma, features, pos, ctx: HookContext):
    """Pre-hook: rewrite inputs before any backend sees them."""
    return lemma.strip(), features, pos

def gap_fill(forms: set[str], ctx: HookContext) -> set[str]:
    """Post-hook: extend or filter results after the chain completes."""
    if not forms:
        # e.g., call an LLM backend here
        pass
    return forms

set_chain("grc", ["ancient-greek", "unimorph"],
          pre_hook=normalize, post_hook=gap_fill)
```

Pre-hooks run once before the chain starts; post-hooks run once after all
backends have been tried and the stop condition applied.

Per-call hooks override the chain's registered hooks for that call only:

```python
inflect_traced("θεός", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "noun",
               language="grc", post_hook=gap_fill)
```

Hook exceptions propagate to the caller (unlike backend exceptions, which are
swallowed and logged at DEBUG level).

See `examples/backend_chain.py` and `examples/chain_hooks.py` for complete
worked examples.

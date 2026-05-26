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
| Homeric/Archaic | 800–500 BCE | Not covered |
| Classical Attic | 480–323 BCE | **Partly covered** — fixed vocabulary (`ancient-greek` + UniMorph grc) |
| Koine / Hellenistic | 323 BCE – 400 CE | Partly covered in `unimorph grc` (unlabelled) |
| New Testament Greek | ~50–100 CE | Same partial Koine coverage (`unimorph grc`) |
| Byzantine | 400–1453 CE | No dedicated support; some overlap with late Koine via `unimorph grc` |
| Katharevousa | 1830–1976 CE | Partially supported — many forms work, some explicitly suppressed in `modern-greek` |
| Standard Demotic | 1976–present | **Covered** — `modern-greek` (any lemma); UniMorph ell (fixed vocabulary) |

The major alphabetic dialects (Attic, Ionic, Doric, Aeolic) share the same
morphological paradigms; differences are primarily phonological and orthographic
(e.g. Attic -ττ- vs Ionic -σσ-, loss of digamma in Ionic). The `ancient-greek`
backend targets Classical Attic and is not optimised for other dialects.

See [future-work.md](future-work.md) for what each unimplemented variety would require and
[corpora.md](corpora.md) for available corpora per period.

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
| Verb | 20 |
| Noun | 23 |
| Adjective | 4 |

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
Wiktionary's Ancient Greek inflection tables. Bundled as
`src/eee/data/unimorph/grc.tsv`. License: **CC BY-SA 3.0** (see `NOTICE`).

**Period:** Mixed. Wiktionary's Ancient Greek entries span Classical Attic,
Koine, and Hellenistic Greek without systematic period labelling. Many common
lemmas are Classical Attic, but later forms are also present.

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
Wiktionary's Modern Greek inflection tables. Bundled as
`src/eee/data/unimorph/ell.tsv`. License: **CC BY-SA 3.0** (see `NOTICE`).

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
| Verb | 1,106 |
| Noun | 8,373 |
| Adjective | 2,492 |

**Limitations**

- Noun tags omit gender — passing `Gender` returns an empty set; the notebooks
  fall back to bare forms for nouns (no definite article).
- In the current bundled `ell.tsv`, imperative entries are tagged `V;2;SG;IMP`
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

See also: [future-work.md](future-work.md) — known gaps and future work.
[corpora.md](corpora.md) — available corpora per period (for new backend authors).

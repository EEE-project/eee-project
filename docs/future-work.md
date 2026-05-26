# Future Work

Known gaps and possible improvements for the `eee` package and its backends.

---

## Built-in backend improvements

**`ancient-greek` backend**

- Expand the lexicon with nominal forms from Dik and Keller/Russell (currently
  only Pratt nouns are included).
- Add dual forms (present in some paradigms; currently omitted).
- Broaden adjective and pronoun coverage.

**`unimorph grc`**

- No verb data in the UniMorph grc dataset — consider adding a verb lookup
  layer from [MorphGNT](https://github.com/morphgnt/sblgnt) (NT/Koine verbs)
  or [PROIEL](https://proiel.github.io/) treebanks.
- Noun gender absent from tags — a post-processing step could infer gender from
  nominative singular patterns.

**`modern-greek` backend**

- Periphrastic perfect/pluperfect: generate the verbal adjective and prefix with
  the appropriate form of έχω/είχα.

**`unimorph el`**

- Noun gender absent from tags — same inference approach as for grc.
- Imperative aspect cannot be distinguished from the tag alone — consider
  splitting `IMP` entries by stem morphology.

---

## New backends

**Koine / Hellenistic**

Koine differs from Attic mainly in: loss of the dual, simplified optative,
iotacism (ει/ι/η/οι convergence), and some vocabulary shifts. The Pratt rule
engine could in principle be extended with Koine stem data. Potential sources:
[MorphGNT](https://github.com/morphgnt/sblgnt) (NT morphological annotation —
Koine/New Testament Greek verbs only),
[PROIEL](https://proiel.github.io/) treebanks (NT, Herodotus, Sallust).

**Katharevousa**

Archaizing register with varying degrees of Classical morphology (dative
retention in some registers) combined with modern vocabulary. The Pratt engine
is a possible starting point; the main gap is a Katharevousa-specific lexicon
and polytonic accentuation rules.

See [backends.md](backends.md) for the full period overview and
[corpora.md](corpora.md) for available corpora per period.

---

## Morphological analysis (`analyze`)

No built-in backend currently supports reverse lookup (inflected form → lemma +
feature bundle). Feasible approaches per backend:

- `unimorph` grc/ell: reverse the TSV index (form → rows).
- `ancient-greek`: `greek-inflexion` already has a parse/conjecture path in
  the upstream library — it could be exposed.
- `modern-greek`: no obvious reverse path from the rule engine; would need a
  separate lookup structure.

---

## Adding a new backend

Any class with `inflect(lemma, features, pos, **kw) → set[str]` and optionally
`list_lemmas(pos) → list[str]` can be registered via the `eee.backends.v1`
entry point group:

```toml
[project.entry-points."eee.backends.v1"]
xx = "my_xx_eee.backend:MyBackend"
```

A new backend can be a standalone package (like `ancient-greek-morphology-eee`)
installed alongside `eee`.

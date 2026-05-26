# Greek Corpora Landscape

Reference for anyone planning a new backend. No single corpus covers all periods;
the table below maps period to available open sources with morphological annotation.

## Corpus overview

| Corpus | Period | Open | Morphology | Notes |
|--------|--------|:----:|:----------:|-------|
| [Diorisis](https://www.turing.ac.uk/news/publications/diorisis-ancient-greek-corpus) | Homeric → Early Byzantine (~800 BCE – 500 CE) | ✓ | POS + lemma + morphology | ~820 texts, ~10M tokens; best diachronic coverage for ancient Greek |
| [Perseus Digital Library](http://www.perseus.tufts.edu/) | Archaic → Classical, some Koine | ✓ | Yes, for most texts | Standard open baseline; source for Diorisis and other corpora |
| [MorphGNT](https://github.com/morphgnt/sblgnt) | NT Greek / Koine (~50–100 CE) | ✓ | Full morphology + lemma | Per-word annotation of SBLGNT; NT only |
| [PROIEL](https://proiel.github.io/) | Koine + Late Antiquity (NT, Herodotus) | ✓ | Morphology + dependency syntax | Best for syntactic research; smaller coverage than Diorisis |
| [Papyri.info](https://papyri.info/) | Hellenistic → Late Antiquity | ✓ | Partial | Documentary papyri; useful for non-literary Koine |
| [TLG](https://stephanus.tlg.uci.edu/) | Homeric → Byzantine (~800 BCE – 1453 CE) | ✗ | Yes (varies) | Largest corpus; institutional subscription required |
| Byzantine Text Archive | Byzantine (400–1453 CE) | Partial | Varies by project | No consolidated open resource; see TLG for broad coverage |
| [Hellenic National Corpus](http://hnc.ilsp.gr/) | Modern Greek | Restricted | Yes | Primary Modern Greek reference corpus |
| [Greek Parliament Proceedings](https://arxiv.org/abs/2210.12883) | Modern Greek (1989–2020) | ✓ | No | 1M+ speeches; useful for diachronic Modern Greek study |

## Per-period source map

| Period | Best open sources |
|--------|------------------|
| Mycenaean | Linear B corpora (no morphological NLP tooling) |
| Homeric / Archaic | Diorisis, Perseus |
| Classical Attic | Diorisis, Perseus, (TLG) |
| Koine / Hellenistic | Diorisis, MorphGNT, PROIEL, Papyri.info |
| Byzantine | TLG (not open); no consolidated open alternative |
| Katharevousa | Digitized newspapers, Google Books |
| Modern Greek | Greek Parliament Proceedings, Hellenic National Corpus |

## Notes for backend authors

**Diorisis** is the most practical starting point for a new ancient Greek backend
covering periods beyond Classical Attic. Its downloadable dataset includes lemma
and morphological annotation across a wide diachronic range, making it a realistic
source for a Homeric or Koine lookup table.

**MorphGNT + PROIEL** are the standard sources for Koine/NT morphology; both are
already referenced in the `unimorph grc` improvement notes in [future-work.md](future-work.md).

**Byzantine** has no consolidated open corpus with morphological annotation. TLG
is the only comprehensive source but requires an institutional subscription.

See [backends.md](backends.md) for the period coverage overview and
[future-work.md](future-work.md) for future work.

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "eee @ git+https://codeberg.org/EEE-project/eee.git",
#     "ancient-greek-morphology-eee @ git+https://codeberg.org/EEE-project/ancient-greek-morphology-eee.git",
# ]
#
# [tool.uv.sources]
# eee = { git = "https://codeberg.org/EEE-project/eee.git" }
# ancient-greek-morphology-eee = { git = "https://codeberg.org/EEE-project/ancient-greek-morphology-eee.git" }
# ///
"""Side-by-side comparison of all eee backends.

Key findings shown here:
  - MG dedicated (el) and UniMorph (ell) agree on nouns/adjectives when ell.tsv has the lemma.
  - ell.tsv is missing many common words (λόγος, άνθρωπος); coverage depends on the corpus.
  - UniMorph ell verb tags (V;1;SG;IPFV;PRS) differ from eee's UD mapping → always ∅ for verbs.
  - AG dedicated (grc) covers classical lexicon; grc.tsv covers a different (Byzantine/NT) corpus.
  - The two AG backends have COMPLEMENTARY coverage: θεός ∈ dedicated, βοηθός ∈ UniMorph.

Run standalone:
    uv run examples/backend_comparison.py

Run from within the repo (uses local packages):
    uv run python examples/backend_comparison.py
"""
from __future__ import annotations

import eee
from eee.backends.modern_greek import ModernGreekBackend
from eee.backends.unimorph import UniMorphBackend

eee.register_default_backends()

mg = ModernGreekBackend()
um = UniMorphBackend()

try:
    from ancient_greek_morphology_eee.backend import AncientGreekBackend
    ag: object | None = AncientGreekBackend()
    ag_label = "grc dedicated"
except ImportError:
    ag = None
    ag_label = "grc (not installed)"


def fmt(result: set[str]) -> str:
    return ", ".join(sorted(result)) if result else "∅"


def call(backend: object | None, lemma: str, features: dict, pos: str, language: str) -> str:
    if backend is None:
        return "(not installed)"
    try:
        return fmt(backend.inflect(lemma, features, pos, language=language))  # type: ignore[union-attr]
    except Exception as e:
        return f"[{type(e).__name__}]"


def table(
    title: str,
    lemma: str,
    slots: list[tuple[str, dict]],
    pos: str,
    col_a_label: str,
    col_a_lang: str,
    col_a_backend: object | None,
    col_b_label: str,
    col_b_lang: str,
    col_b_backend: object | None,
) -> None:
    w = 26
    print(f"\n{'─' * 74}")
    print(f"  {title}  —  {lemma}  [{pos}]")
    print(f"{'─' * 74}")
    print(f"  {'Form':<18}  {col_a_label:<{w}}  {col_b_label}")
    print(f"  {'─' * 16}  {'─' * w}  {'─' * w}")
    for slot_name, features in slots:
        a = call(col_a_backend, lemma, features, pos, col_a_lang)
        b = call(col_b_backend, lemma, features, pos, col_b_lang)
        flag = "≠ " if a not in ("∅", "(not installed)") and b not in ("∅", "(not installed)") and a != b else "  "
        print(f"  {slot_name:<18}  {a:<{w}}  {flag}{b}")


# ── Modern Greek nouns: el dedicated vs ell UniMorph ─────────────────────────
# γυναίκα and σπίτι are both in ell.tsv → backends should agree.
# λόγος is absent from ell.tsv → shows coverage gap.

MG_NOUN_SLOTS = [
    (f"{c} {n[:2]}", {"Case": c, "Number": n})
    for n in ("Sing", "Plur") for c in ("Nom", "Gen", "Acc", "Voc")
]

for lemma in ("γυναίκα", "σπίτι", "λόγος"):
    table(
        "MG noun  el(dedicated) vs ell(UniMorph)", lemma,
        MG_NOUN_SLOTS, "noun",
        "el dedicated", "el", mg,
        "ell UniMorph",  "ell", um,
    )

# ── Modern Greek verbs: el dedicated vs ell UniMorph ─────────────────────────
# UniMorph always returns ∅ — ell.tsv uses V;1;SG;IPFV;PRS order (no mood/voice),
# but eee generates V;IND;PRS;ACT;1;SG. Tag format mismatch, not a missing lemma.

MG_VERB_SLOTS = [
    (f"{p}{'sg' if n == 'Sing' else 'pl'} {label}",
     {"Tense": t, "Mood": "Ind", "Voice": "Act", "Person": p, "Number": n, **extra})
    for label, t, extra in [("prs", "Pres", {}), ("impf", "Past", {"Aspect": "Imp"})]
    for p, n in [("1", "Sing"), ("2", "Sing"), ("3", "Sing")]
]

table(
    "MG verb  el(dedicated) vs ell(UniMorph) — tag format mismatch", "λύω",
    MG_VERB_SLOTS, "verb",
    "el dedicated", "el", mg,
    "ell UniMorph",  "ell", um,
)

# ── Ancient Greek verbs: grc dedicated only ───────────────────────────────────
# AG verbs require VerbForm in features; UniMorph has no verbs in grc.tsv.

AG_VERB_SLOTS = [
    (f"{p}{'sg' if n == 'Sing' else 'pl'} {label}",
     {"VerbForm": "Fin", "Tense": t, "Mood": "Ind", "Voice": "Act", "Person": p, "Number": n})
    for label, t in [("prs", "Pres"), ("aor", "Aor")]
    for p, n in [("1", "Sing"), ("2", "Sing"), ("3", "Sing")]
]

table(
    "AG verb  grc(dedicated) vs grc(UniMorph) — no verbs in grc.tsv", "λύω",
    AG_VERB_SLOTS, "verb",
    ag_label,       "grc", ag,
    "grc UniMorph", "grc", um,
)

# ── Ancient Greek nouns: complementary coverage ───────────────────────────────
# θεός  → in dedicated lexicon, absent from grc.tsv
# βοηθός → absent from dedicated, present in grc.tsv (Byzantine/NT corpus)

AG_NOUN_SLOTS = [
    (f"{c} {n[:2]}", {"Case": c, "Number": n})
    for n in ("Sing", "Plur") for c in ("Nom", "Gen", "Dat", "Acc", "Voc")
]

for lemma in ("θεός", "βοηθός"):
    table(
        "AG noun  grc(dedicated) vs grc(UniMorph) — complementary coverage", lemma,
        AG_NOUN_SLOTS, "noun",
        ag_label,       "grc", ag,
        "grc UniMorph", "grc", um,
    )

# ── Ancient Greek adjectives: complementary coverage ─────────────────────────
# ἀγαθός  → in dedicated lexicon, absent from grc.tsv
# μυστικός → absent from dedicated, present in grc.tsv

AG_ADJ_SLOTS = [
    (f"{c} {n[:2]} {g[0]}", {"Case": c, "Number": n, "Gender": g})
    for n in ("Sing", "Plur")
    for c in ("Nom", "Gen", "Acc")
    for g in ("Masc", "Fem", "Neut")
]

for lemma in ("ἀγαθός", "μυστικός"):
    table(
        "AG adj  grc(dedicated) vs grc(UniMorph) — complementary coverage", lemma,
        AG_ADJ_SLOTS, "adjective",
        ag_label,       "grc", ag,
        "grc UniMorph", "grc", um,
    )

# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'─' * 74}")
print("  Backend registry")
print(f"{'─' * 74}")
for code, cls in eee.supported_languages().items():
    print(f"  {code:<6}  {cls}")
print(f"  {'ell':<6}  UniMorphBackend (fallback — nouns/adjectives from ell.tsv)")
print()
print("  ell.tsv:  ~212k forms, 8 373 lemmas (corpus-derived, not full lexicon)")
print("  grc.tsv:  ~44k forms, 2 431 lemmas (Byzantine/NT corpus)")
print()
print("  ≠ = backends disagree    ∅ = backend has no result")

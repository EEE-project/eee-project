# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "eee @ git+https://codeberg.org/EEE-project/eee.git",
#     "modern-greek-backend-eee @ git+https://codeberg.org/EEE-project/modern-greek-backend-eee.git",
#     "unimorph-backend-eee @ git+https://codeberg.org/EEE-project/unimorph-backend-eee.git",
#     "ancient-greek-backend-eee @ git+https://codeberg.org/EEE-project/ancient-greek-backend-eee.git",
# ]
#
# [tool.uv.sources]
# eee = { git = "https://codeberg.org/EEE-project/eee.git" }
# modern-greek-backend-eee = { git = "https://codeberg.org/EEE-project/modern-greek-backend-eee.git" }
# unimorph-backend-eee = { git = "https://codeberg.org/EEE-project/unimorph-backend-eee.git" }
# ancient-greek-backend-eee = { git = "https://codeberg.org/EEE-project/ancient-greek-backend-eee.git" }
# ///
"""Side-by-side comparison of all eee backends.

Key findings shown here:
  - MG dedicated (el) and UniMorph (ell) agree on nouns/adjectives when ell.tsv has the lemma.
  - ell.tsv is missing many common words (λόγος, άνθρωπος); coverage depends on the corpus.
  - Both backends agree on MG verbs (ell.tsv uses V;PERSON;NUMBER;ASPECT;TENSE; eee maps to it).
  - AG dedicated (grc) covers classical lexicon; grc.tsv covers a different (Byzantine/NT) corpus.
  - The two AG backends have COMPLEMENTARY coverage: θεός ∈ dedicated, βοηθός ∈ UniMorph.

Run standalone:
    uv run examples/backend_comparison.py

Run from within the repo (uses local packages):
    uv run python examples/backend_comparison.py
"""
from __future__ import annotations

import eee_project as eee
from modern_greek_backend_eee import ModernGreekBackend
from unimorph_backend_eee import UniMorphBackend

try:
    from ancient_greek_backend_eee import AncientGreekBackend
    ag: object | None = AncientGreekBackend()
    ag_label = "grc dedicated"
except ImportError:
    ag = None
    ag_label = "grc (not installed)"

mg = ModernGreekBackend()
um = UniMorphBackend()


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
        "ell UniMorph",  "el", um,
    )

# ── Modern Greek verbs: el dedicated vs ell UniMorph ─────────────────────────
# Both backends use V;PERSON;NUMBER;ASPECT;TENSE tag order. When ell.tsv has the
# lemma, both backends agree. ell.tsv verb coverage is limited (~1,094 lemmas).

MG_VERB_SLOTS = [
    (f"{p}{'sg' if n == 'Sing' else 'pl'} {label}",
     {"Tense": t, "Mood": "Ind", "Person": p, "Number": n, **extra})
    for label, t, extra in [("prs", "Pres", {}), ("impf", "Past", {"Aspect": "Imp"}), ("aor", "Past", {"Aspect": "Perf"})]
    for p, n in [("1", "Sing"), ("2", "Sing"), ("3", "Sing")]
]

table(
    "MG verb  el(dedicated) vs ell(UniMorph)", "ακούω",
    MG_VERB_SLOTS, "verb",
    "el dedicated", "el", mg,
    "ell UniMorph",  "el", um,
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
for code, backends in eee.supported_languages().items():
    print(f"  {code:<6}  {', '.join(backends)}")
print()
print("  ell.tsv:  ~11,937 lemmas — verb 1,094 · noun 8,351 · adj 2,492 (corpus-derived, not full lexicon)")
print("  grc.tsv:  ~2,431 lemmas — noun 2,224 · adj 207 (mixed Attic/Koine/Hellenistic)")
print()
print("  ≠ = backends disagree    ∅ = backend has no result")

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "eee @ git+https://codeberg.org/EEE-project/eee.git",
# ]
#
# [tool.uv.sources]
# eee = { git = "https://codeberg.org/EEE-project/eee.git" }
# ///
"""UniMorph TSV-lookup backend — nouns and adjectives for Modern and Ancient Greek.

Covers ~212k MG forms (8 373 lemmas) and ~44k AG forms bundled in the package.
Important: the ell.tsv dataset does NOT include all common words — λόγος, άνθρωπος,
χρόνος etc. are absent. Coverage is best for technical/literary vocabulary.

Verb inflection is not supported by this backend (ell.tsv tag format differs
from eee's UD→UniMorph mapping).

Run standalone:
    uv run examples/unimorph.py

Run from within the repo (uses local package):
    uv run python examples/unimorph.py
"""

import eee
from eee.backends.unimorph import UniMorphBackend


def show(label: str, result: set[str]) -> None:
    forms = ", ".join(sorted(result)) if result else "(not in corpus)"
    print(f"  {label:<45} → {forms}")


def inflect(lemma, features, pos, **kw):
    return eee.inflect(lemma, features, pos, backend="unimorph", **kw)


# ── Modern Greek nouns (el) ───────────────────────────────────────────────────

print("=== Modern Greek nouns (el, backend='unimorph') ===")
print()
print("γυναίκα — all cases")
for number in ("Sing", "Plur"):
    for case in ("Nom", "Gen", "Acc", "Voc"):
        show(f"{case} {number}", inflect(
            "γυναίκα", {"Case": case, "Number": number}, "noun", language="el",
        ))

print()
print("σπίτι — all cases")
for number in ("Sing", "Plur"):
    for case in ("Nom", "Gen", "Acc", "Voc"):
        show(f"{case} {number}", inflect(
            "σπίτι", {"Case": case, "Number": number}, "noun", language="el",
        ))

print()
print("λόγος — (absent from ell.tsv, shows coverage limitation)")
show("Nom Sing", inflect("λόγος", {"Case": "Nom", "Number": "Sing"}, "noun", language="el"))

# ── Modern Greek adjectives (el) ──────────────────────────────────────────────

print()
print("=== Modern Greek adjectives (el, backend='unimorph') ===")
print()
print("ανιαρός — Nom/Gen/Acc Sing, all genders")
for gender in ("Masc", "Fem", "Neut"):
    for case in ("Nom", "Gen", "Acc"):
        show(f"{case} Sing {gender}", inflect(
            "ανιαρός",
            {"Case": case, "Number": "Sing", "Gender": gender},
            "adjective", language="el",
        ))

# ── Ancient Greek nouns (grc) — gender stripped ───────────────────────────────
# grc.tsv uses N;CASE;NUM (no gender). Gender in features is stripped automatically.

print()
print("=== Ancient Greek nouns (grc, backend='unimorph') ===")
print()
print("βοηθός — all cases (Gender=Masc passed but stripped; same result without it)")
for number in ("Sing", "Plur"):
    for case in ("Nom", "Gen", "Dat", "Acc", "Voc"):
        show(f"{case} {number}", inflect(
            "βοηθός", {"Case": case, "Number": number, "Gender": "Masc"}, "noun",
            language="grc",
        ))

# ── Ancient Greek adjectives (grc) ───────────────────────────────────────────
# grc.tsv: ADJ;CASE;NUM for masc/fem (gender stripped), ADJ;CASE;NUM;NEUT for neuter.

print()
print("=== Ancient Greek adjectives (grc, backend='unimorph') ===")
print()
print("ἄγναπτος — Nom/Gen Sing, all genders (Masc/Fem share form; Neut distinct)")
for gender in ("Masc", "Fem", "Neut"):
    for case in ("Nom", "Gen"):
        show(f"{case} Sing {gender}", inflect(
            "ἄγναπτος",
            {"Case": case, "Number": "Sing", "Gender": gender},
            "adjective", language="grc",
        ))

# ── Coverage summary ─────────────────────────────────────────────────────────

print()
print("=== Coverage ===")
print()
print("  UniMorph backend (ell tier):")
for code in UniMorphBackend().supported_languages():
    info = eee.language_info(code)
    name = info.get("name", code) if info else code
    pos_list = info.get("pos", []) if info else []
    print(f"  {code}  {name:<30} pos: {', '.join(pos_list)}")
print()
print("  grc nouns/adjectives also available via backend='unimorph';")
print("  default grc routing uses AncientGreekBackend (tier: dedicated).")

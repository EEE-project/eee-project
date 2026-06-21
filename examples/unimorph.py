# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "eee-project @ git+https://codeberg.org/EEE-project/eee.git",
#     "unimorph-backend-eee @ git+https://codeberg.org/EEE-project/unimorph-backend-eee.git",
# ]
#
# [tool.uv.sources]
# eee-project = { git = "https://codeberg.org/EEE-project/eee.git" }
# unimorph-backend-eee = { git = "https://codeberg.org/EEE-project/unimorph-backend-eee.git" }
# ///
"""UniMorph TSV-lookup backend — nouns, adjectives, and verbs across six languages.

Bundled datasets:
  ell  Modern Greek   — ~11,937 lemmas: verb 1,094 · noun 8,351 · adj 2,492
  grc  Ancient Greek  — ~2,431 lemmas: noun 2,224 · adj 207
  lat  Latin          — nouns and adjectives only
  rus  Russian        — nouns and adjectives only
  spa  Spanish        — nouns and adjectives only (no case; Gender+Number)
  tur  Turkish        — nouns only

Modern Greek verb inflection works via a UD→UniMorph tag mapping
(V;PERSON;NUMBER;ASPECT;TENSE). Pass {Person, Number, Tense} — Aspect and Mood
are optional. Coverage note: ell.tsv omits many common words (λόγος, άνθρωπος);
coverage is strongest for technical/literary vocabulary.

Run standalone:
    uv run examples/unimorph.py

Run from within the repo (uses local package):
    uv run python examples/unimorph.py
"""

import eee_project as eee
from unimorph_backend_eee import UniMorphBackend

eee.register_backend("el", UniMorphBackend("el"), backend="unimorph")
eee.register_backend("grc", UniMorphBackend("grc"), backend="unimorph")
eee.register_backend("la", UniMorphBackend("la"), backend="unimorph")
eee.register_backend("ru", UniMorphBackend("ru"), backend="unimorph")
eee.register_backend("es", UniMorphBackend("es"), backend="unimorph")
eee.register_backend("tr", UniMorphBackend("tr"), backend="unimorph")


def show(label: str, result: set[str]) -> None:
    forms = ", ".join(sorted(result)) if result else "(not in corpus)"
    print(f"  {label:<45} → {forms}")


def inflect(lemma, features, pos, **kw):
    return eee.inflect(lemma, features, pos, backend="unimorph", **kw)


# ── Modern Greek verbs (el) ───────────────────────────────────────────────────
# ell.tsv tag format: V;PERSON;NUMBER;ASPECT;TENSE — matched by UD→UniMorph mapping.
# Pass {Person, Number, Tense}; Aspect defaults to imperfective when omitted.

print("=== Modern Greek verbs (el, backend='unimorph') ===")
print()
print("ιατρεύω — indicative forms")
for tense, aspect, label in [
    ("Pres", None,   "present"),
    ("Past", "Imp",  "imperfect"),
    ("Past", "Perf", "aorist"),
    ("Fut",  None,   "future (both aspects)"),
]:
    feats: dict = {"Tense": tense, "Mood": "Ind"}
    if aspect:
        feats["Aspect"] = aspect
    for person, number in [("1", "Sing"), ("2", "Sing"), ("3", "Sing"), ("1", "Plur"), ("2", "Plur"), ("3", "Plur")]:
        show(f"{label} {person}{'sg' if number == 'Sing' else 'pl'}",
             inflect("ιατρεύω", {**feats, "Person": person, "Number": number}, "verb", language="el"))

print()
print("ιατρεύω — subjunctive")
for aspect, label in [("Imp", "ipfv sbjv"), ("Perf", "pfv sbjv")]:
    for person, number in [("1", "Sing"), ("2", "Sing"), ("3", "Sing")]:
        show(f"{label} {person}sg",
             inflect("ιατρεύω", {"Mood": "Sub", "Aspect": aspect, "Person": person, "Number": number},
                     "verb", language="el"))

# ── Modern Greek nouns (el) ───────────────────────────────────────────────────

print()
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

# ── Latin nouns and adjectives (la) ──────────────────────────────────────────

print()
print("=== Latin nouns (la, backend='unimorph') ===")
print()
print("puella — all cases incl. ablative")
for number in ("Sing", "Plur"):
    for case in ("Nom", "Gen", "Dat", "Acc", "Abl", "Voc"):
        show(f"{case} {number}", inflect(
            "puella", {"Case": case, "Number": number}, "noun", language="la",
        ))

print()
print("=== Latin adjectives (la, backend='unimorph') ===")
print()
print("lūminōsus — three-termination (separate MASC/FEM/NEUT forms)")
for gender in ("Masc", "Fem", "Neut"):
    for case in ("Nom", "Acc"):
        show(f"{case} Sing {gender}", inflect(
            "lūminōsus",
            {"Case": case, "Number": "Sing", "Gender": gender},
            "adjective", language="la",
        ))

print()
print("algēnsis — two-termination (MASC+FEM shared form)")
for gender in ("Masc", "Fem", "Neut"):
    show(f"Nom Sing {gender}", inflect(
        "algēnsis",
        {"Case": "Nom", "Number": "Sing", "Gender": gender},
        "adjective", language="la",
    ))

# ── Russian nouns and adjectives (ru) ─────────────────────────────────────────

print()
print("=== Russian nouns (ru, backend='unimorph') ===")
print()
print("работа — all cases (incl. instrumental + locative/prepositional)")
for number in ("Sing", "Plur"):
    for case in ("Nom", "Gen", "Dat", "Acc", "Ins", "Loc"):
        show(f"{case} {number}", inflect(
            "работа", {"Case": case, "Number": number}, "noun", language="ru",
        ))

print()
print("=== Russian adjectives (ru, backend='unimorph') ===")
print()
print("красивый — Nom/Acc Sing all genders; animacy contrast on ACC Masc")
for gender in ("Masc", "Fem", "Neut"):
    show(f"Nom Sing {gender}", inflect(
        "красивый", {"Case": "Nom", "Number": "Sing", "Gender": gender},
        "adjective", language="ru",
    ))
show("Acc Sing Masc (animate)",   inflect("красивый", {"Case": "Acc", "Number": "Sing", "Gender": "Masc", "Animacy": "Anim"},  "adjective", language="ru"))
show("Acc Sing Masc (inanimate)", inflect("красивый", {"Case": "Acc", "Number": "Sing", "Gender": "Masc", "Animacy": "Inan"},  "adjective", language="ru"))
show("Acc Sing Fem",              inflect("красивый", {"Case": "Acc", "Number": "Sing", "Gender": "Fem"},  "adjective", language="ru"))
show("Ins Sing Fem",              inflect("красивый", {"Case": "Ins", "Number": "Sing", "Gender": "Fem"},  "adjective", language="ru"))
show("Nom Plur",                  inflect("красивый", {"Case": "Nom", "Number": "Plur"},  "adjective", language="ru"))

# ── Spanish nouns and adjectives (es) ─────────────────────────────────────────

print()
print("=== Spanish nouns (es, backend='unimorph') ===")
print()
print("casa — gender+number (no case)")
for gender in ("Fem",):
    for number in ("Sing", "Plur"):
        show(f"{gender} {number}", inflect(
            "casa", {"Gender": gender, "Number": number}, "noun", language="es",
        ))

print()
print("=== Spanish adjectives (es, backend='unimorph') ===")
print()
print("grande — invariant (shared MASC+FEM form, only PL inflects)")
show("Plur (invariant)", inflect("grande", {"Number": "Plur"}, "adjective", language="es"))

# ── Turkish nouns (tr) ────────────────────────────────────────────────────────

print()
print("=== Turkish nouns (tr, backend='unimorph') ===")
print()
print("köpek — all cases")
for number in ("Sing", "Plur"):
    for case in ("Nom", "Gen", "Dat", "Acc", "Abl", "Loc"):
        show(f"{case} {number}", inflect(
            "köpek", {"Case": case, "Number": number}, "noun", language="tr",
        ))

# ── Coverage summary ─────────────────────────────────────────────────────────

print()
print("=== Coverage ===")
print()
_UNIMORPH_TO_ISO = {"ell": "ell", "grc": "grc", "lat": "la", "rus": "ru", "spa": "es", "tur": "tr"}
print("  UniMorph backend (unimorph code → ISO code):")
for code in UniMorphBackend().supported_languages():
    iso = _UNIMORPH_TO_ISO.get(code, code)
    info = eee.language_info(iso)
    name = info.get("name", iso) if info else iso
    pos_list = info.get("pos", []) if info else []
    print(f"  {code} ({iso})  {name:<28} pos: {', '.join(pos_list)}")
print()
print("  grc verbs not supported (grc.tsv has no verb data); use AncientGreekBackend for verbs.")
print()
print("  entry points discovered by eee:")
for lang, backends in eee.supported_languages().items():
    print(f"    {lang} → {', '.join(backends)}")

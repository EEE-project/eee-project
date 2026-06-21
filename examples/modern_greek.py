# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "eee-project @ git+https://codeberg.org/EEE-project/eee.git",
#     "modern-greek-backend-eee @ git+https://codeberg.org/EEE-project/modern-greek-backend-eee.git",
# ]
#
# [tool.uv.sources]
# eee-project = { git = "https://codeberg.org/EEE-project/eee.git" }
# modern-greek-backend-eee = { git = "https://codeberg.org/EEE-project/modern-greek-backend-eee.git" }
# ///
"""Modern Greek morphology examples using the eee package.

Run standalone:
    uv run examples/modern_greek.py

Run from within the repo (uses local package):
    uv run python examples/modern_greek.py
"""

import eee_project as eee
from modern_greek_backend_eee import ModernGreekBackend

eee.register_backend("el", ModernGreekBackend())


def show(label: str, result: set[str]) -> None:
    forms = ", ".join(sorted(result)) if result else "(empty)"
    print(f"  {label:<45} → {forms}")


print("=== Verbs ===")
print()
print("λύω — present active indicative")
for person, number in [("1", "Sing"), ("2", "Sing"), ("3", "Sing"),
                        ("1", "Plur"), ("2", "Plur"), ("3", "Plur")]:
    label = f"{person}{'sg' if number == 'Sing' else 'pl'} pres act ind"
    show(label, eee.inflect(
        "λύω",
        {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin",
         "Voice": "Act", "Person": person, "Number": number},
        "verb", language="el",
    ))

print()
print("λύω — other tenses and moods (1sg)")
show("imperfect active",    eee.inflect("λύω", {"Tense": "Past", "Aspect": "Imp",  "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb", language="el"))
show("perfective subj act (bare)", eee.inflect("λύω", {"Mood": "Sub",  "Aspect": "Perf", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb", language="el"))
show("aorist passive",       eee.inflect("λύω", {"Tense": "Past", "Aspect": "Perf", "Voice": "Pass", "Person": "1", "Number": "Sing"}, "verb", language="el"))

print()
print("φοβάμαι — deponent (1sg present, Voice=Act falls back to passive tree)")
show("1sg pres", eee.inflect("φοβάμαι", {"Tense": "Pres", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb", language="el"))

print()
print("πάω — suppletive (imperfective aspect uses πηγαίνω internally)")
show("1sg pres impf", eee.inflect("πάω", {"Tense": "Pres", "Aspect": "Imp", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb", language="el"))

print()
print("=== Nouns ===")
print()
print("γυναίκα (fem) — all cases")
for number in ("Sing", "Plur"):
    for case in ("Nom", "Gen", "Acc", "Voc"):
        show(f"{case} {number}", eee.inflect(
            "γυναίκα", {"Gender": "Fem", "Number": number, "Case": case},
            "noun", language="el",
        ))

print()
print("γιατρός (common gender) — Nom Sing without Gender specified")
show("Nom Sing (no gender → all)", eee.inflect("γιατρός", {"Number": "Sing", "Case": "Nom"}, "noun", language="el"))

print()
print("=== Adjectives ===")
print()
print("καλός — positive degree")
for gender in ("Masc", "Fem", "Neut"):
    for case in ("Nom", "Gen", "Acc"):
        show(f"Pos {gender} Sing {case}", eee.inflect(
            "καλός",
            {"Degree": "Pos", "Gender": gender, "Number": "Sing", "Case": case},
            "adjective", language="el",
        ))

print()
print("καλός — comparative and superlative (Masc Nom Sing)")
show("Cmp Masc Sing Nom", eee.inflect("καλός", {"Degree": "Cmp", "Gender": "Masc", "Number": "Sing", "Case": "Nom"}, "adjective", language="el"))
show("Sup Masc Sing Nom", eee.inflect("καλός", {"Degree": "Sup", "Gender": "Masc", "Number": "Sing", "Case": "Nom"}, "adjective", language="el"))

print()
print("=== Registry ===")
print()
print("  registered: el → ModernGreekBackend (explicit)")
for lang, backends in eee.supported_languages().items():
    print(f"  entry points: {lang} → {', '.join(backends)}")

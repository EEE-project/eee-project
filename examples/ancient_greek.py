# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "eee-project @ git+https://codeberg.org/EEE-project/eee.git",
#     "ancient-greek-backend-eee @ git+https://codeberg.org/EEE-project/ancient-greek-backend-eee.git",
# ]
#
# [tool.uv.sources]
# eee-project = { git = "https://codeberg.org/EEE-project/eee.git" }
# ancient-greek-backend-eee = { git = "https://codeberg.org/EEE-project/ancient-greek-backend-eee.git" }
# ///
"""Ancient Greek morphology examples using the eee package.

Run standalone:
    uv run examples/ancient_greek.py

Run from within the repo (uses local packages):
    uv run python examples/ancient_greek.py
"""

import eee_project as eee
from ancient_greek_backend_eee import AncientGreekBackend

eee.register_backend("grc", AncientGreekBackend())


def show(label: str, result: set[str]) -> None:
    forms = ", ".join(sorted(result)) if result else "(empty)"
    print(f"  {label:<45} → {forms}")


print("=== Verbs ===")
print()
print("λύω — present and aorist active indicative")
for tense, tense_label in [("Pres", "pres"), ("Aor", "aor")]:
    for person, number in [("1", "Sing"), ("2", "Sing"), ("3", "Sing"),
                            ("1", "Plur"), ("2", "Plur"), ("3", "Plur")]:
        label = f"{person}{'sg' if number == 'Sing' else 'pl'} {tense_label} act ind"
        show(label, eee.inflect(
            "λύω",
            {"VerbForm": "Fin", "Tense": tense, "Voice": "Act",
             "Mood": "Ind", "Person": person, "Number": number},
            "verb", language="grc",
        ))

print()
print("λύω — other forms (1sg)")
show("aor pass ind 1sg",     eee.inflect("λύω", {"VerbForm": "Fin",  "Tense": "Aor",  "Voice": "Pass", "Mood": "Ind", "Person": "1", "Number": "Sing"}, "verb", language="grc"))
show("pres mid ind 1sg",     eee.inflect("λύω", {"VerbForm": "Fin",  "Tense": "Pres", "Voice": "Mid",  "Mood": "Ind", "Person": "1", "Number": "Sing"}, "verb", language="grc"))
show("pres act inf",         eee.inflect("λύω", {"VerbForm": "Inf",  "Tense": "Pres", "Voice": "Act"}, "verb", language="grc"))
show("pres act part NSM",    eee.inflect("λύω", {"VerbForm": "Part", "Tense": "Pres", "Voice": "Act",  "Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "verb", language="grc"))
show("aor act part NSM",     eee.inflect("λύω", {"VerbForm": "Part", "Tense": "Aor",  "Voice": "Act",  "Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "verb", language="grc"))

print()
print("εἰμί — present indicative")
for person, number in [("1", "Sing"), ("2", "Sing"), ("3", "Sing"),
                        ("1", "Plur"), ("2", "Plur"), ("3", "Plur")]:
    label = f"{person}{'sg' if number == 'Sing' else 'pl'} pres act ind"
    show(label, eee.inflect(
        "εἰμί",
        {"VerbForm": "Fin", "Tense": "Pres", "Voice": "Act",
         "Mood": "Ind", "Person": person, "Number": number},
        "verb", language="grc",
    ))

print()
print("=== Nouns ===")
print()
print("θεός (masc, 2nd decl) — all cases")
for number in ("Sing", "Plur"):
    for case in ("Nom", "Gen", "Dat", "Acc", "Voc"):
        show(f"{case} {number}", eee.inflect(
            "θεός", {"Case": case, "Number": number, "Gender": "Masc"},
            "noun", language="grc",
        ))

print()
print("σοφία (fem, 1st decl) — Nom/Gen Sing")
show("Nom Sing", eee.inflect("σοφία", {"Case": "Nom", "Number": "Sing", "Gender": "Fem"}, "noun", language="grc"))
show("Gen Sing", eee.inflect("σοφία", {"Case": "Gen", "Number": "Sing", "Gender": "Fem"}, "noun", language="grc"))

print()
print("πόλις (fem, 3rd decl) — Nom/Gen Sing")
show("Nom Sing", eee.inflect("πόλις", {"Case": "Nom", "Number": "Sing", "Gender": "Fem"}, "noun", language="grc"))
show("Gen Sing", eee.inflect("πόλις", {"Case": "Gen", "Number": "Sing", "Gender": "Fem"}, "noun", language="grc"))

print()
print("=== Adjectives ===")
print()
print("ἀγαθός — positive degree, all genders Nom Sing")
for gender in ("Masc", "Fem", "Neut"):
    show(f"Pos {gender} Sing Nom", eee.inflect(
        "ἀγαθός",
        {"Case": "Nom", "Number": "Sing", "Gender": gender, "Degree": "Pos"},
        "adjective", language="grc",
    ))

print()
print("ἀληθής — contract adj (3rd decl), Nom/Acc Sing")
show("Masc Nom Sing", eee.inflect("ἀληθής", {"Case": "Nom", "Number": "Sing", "Gender": "Masc", "Degree": "Pos"}, "adjective", language="grc"))
show("Neut Nom Sing", eee.inflect("ἀληθής", {"Case": "Nom", "Number": "Sing", "Gender": "Neut", "Degree": "Pos"}, "adjective", language="grc"))
show("Masc Gen Sing", eee.inflect("ἀληθής", {"Case": "Gen", "Number": "Sing", "Gender": "Masc", "Degree": "Pos"}, "adjective", language="grc"))

print()
print("=== Registry ===")
print()
print("  registered: grc → AncientGreekBackend (explicit)")
for lang, backends in eee.supported_languages().items():
    print(f"  entry points: {lang} → {', '.join(backends)}")

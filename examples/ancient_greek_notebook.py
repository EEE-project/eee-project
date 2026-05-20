# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.19.4",
#     "eee @ git+https://codeberg.org/EEE-project/eee.git",
#     "ancient-greek-morphology-eee @ git+https://codeberg.org/EEE-project/ancient-greek-morphology-eee.git",
# ]
#
# [tool.uv.sources]
# eee = { git = "https://codeberg.org/EEE-project/eee.git" }
# ancient-greek-morphology-eee = { git = "https://codeberg.org/EEE-project/ancient-greek-morphology-eee.git" }
# ///
"""Ancient Greek morphology demo using the eee package.

Run standalone (fetches packages from Codeberg):
    uv run marimo run examples/ancient_greek_notebook.py

Run from within the repo (uses local packages):
    uv run marimo edit examples/ancient_greek_notebook.py
"""

import marimo

__generated_with = "0.23.6"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import eee
    return eee, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Ancient Greek Morphology
    **[eee](https://codeberg.org/EEE-project/eee)** — language-agnostic morphology for the EEE project.

    Enter a polytonic Greek lemma and select its part of speech to see the inflection paradigm.
    Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    lemma_input = mo.ui.text(
        value="λύω",
        placeholder="e.g. λύω, θεός, ἀγαθός",
        label="Lemma",
    )
    pos_selector = mo.ui.dropdown(
        options={"Verb": "verb", "Noun": "noun", "Adjective": "adjective"},
        value="Verb",
        label="Part of speech",
    )
    gender_selector = mo.ui.dropdown(
        options={"— (all)": None, "Masc": "Masc", "Fem": "Fem", "Neut": "Neut"},
        value="— (all)",
        label="Gender (nouns/adjectives)",
    )
    mo.hstack([lemma_input, pos_selector, gender_selector], gap="1rem")
    return gender_selector, lemma_input, pos_selector


@app.cell(hide_code=True)
def _(eee, gender_selector, lemma_input, pos_selector):
    _lemma = lemma_input.value.strip()
    _pos = pos_selector.value
    _gender = gender_selector.value

    _VERB_FORMS = []
    for _tense, _tense_label in [("Pres", "Pres"), ("Aor", "Aor"), ("Fut", "Fut"), ("Perf", "Perf")]:
        for _voice, _voice_label in [("Act", "Act"), ("Mid", "Mid"), ("Pass", "Pass")]:
            for _person, _number in [("1", "Sing"), ("2", "Sing"), ("3", "Sing"),
                                      ("1", "Plur"), ("2", "Plur"), ("3", "Plur")]:
                _VERB_FORMS.append((
                    f"{_tense_label} {_voice_label} {_person}{'sg' if _number == 'Sing' else 'pl'} Ind",
                    {"VerbForm": "Fin", "Tense": _tense, "Voice": _voice,
                     "Mood": "Ind", "Person": _person, "Number": _number},
                ))
    for _tense, _tense_label in [("Pres", "Pres"), ("Aor", "Aor")]:
        for _voice, _voice_label in [("Act", "Act"), ("Mid", "Mid"), ("Pass", "Pass")]:
            _VERB_FORMS.append((
                f"{_tense_label} {_voice_label} Inf",
                {"VerbForm": "Inf", "Tense": _tense, "Voice": _voice},
            ))
            _VERB_FORMS.append((
                f"{_tense_label} {_voice_label} Part NSM",
                {"VerbForm": "Part", "Tense": _tense, "Voice": _voice,
                 "Case": "Nom", "Number": "Sing", "Gender": "Masc"},
            ))

    _NOUN_FORMS = []
    for _number in ("Sing", "Plur"):
        for _case in ("Nom", "Gen", "Dat", "Acc", "Voc"):
            _feats = {"Case": _case, "Number": _number}
            if _gender:
                _feats["Gender"] = _gender
            _NOUN_FORMS.append((f"{_case} {_number}", _feats))

    _ADJ_FORMS = []
    _genders = [_gender] if _gender else ["Masc", "Fem", "Neut"]
    for _g in _genders:
        for _number in ("Sing", "Plur"):
            for _case in ("Nom", "Gen", "Dat", "Acc"):
                _ADJ_FORMS.append((
                    f"Pos {_g} {_case} {_number}",
                    {"Degree": "Pos", "Gender": _g, "Case": _case, "Number": _number},
                ))

    _forms_map = {"verb": _VERB_FORMS, "noun": _NOUN_FORMS, "adjective": _ADJ_FORMS}
    rows = []
    if _lemma:
        for _label, _features in _forms_map.get(_pos, []):
            try:
                _result = eee.inflect(_lemma, _features, _pos, language="grc")
                _forms_str = ", ".join(sorted(_result)) if _result else "—"
            except Exception as _exc:
                _forms_str = f"error: {_exc}"
            rows.append({"Form": _label, "Inflected forms": _forms_str})
    return (rows,)


@app.cell(hide_code=True)
def _(lemma_input, mo, rows):
    if not lemma_input.value.strip():
        _output = mo.md("Enter a lemma above.")
    elif rows:
        _output = mo.ui.table(rows, selection=None)
    else:
        _output = mo.md(f"No forms found for **{lemma_input.value.strip()}**.")
    _output
    return


if __name__ == "__main__":
    app.run()

# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.19.4",
#     "eee @ git+https://codeberg.org/EEE-project/eee.git",
# ]
#
# [tool.uv.sources]
# eee = { git = "https://codeberg.org/EEE-project/eee.git" }
# ///
"""Modern Greek morphology demo using the eee package.

Run standalone (fetches eee from Codeberg):
    uv run marimo run examples/modern_greek_notebook.py

Run from within the repo (uses local package):
    uv run marimo edit examples/modern_greek_notebook.py
"""

import marimo

__generated_with = "0.23.6"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    # Imports
    import marimo as mo
    import eee

    return eee, mo


@app.cell(hide_code=True)
def _(mo):
    # Title
    mo.md(r"""
    # Modern Greek Morphology
    **[eee](https://codeberg.org/EEE-project/eee)** — language-agnostic morphology for the EEE project.

    Enter a Greek lemma and select its part of speech to see the full inflection paradigm.
    Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    # Controls
    lemma_input = mo.ui.text(
        value="λύω",
        placeholder="e.g. λύω, γυναίκα, καλός",
        label="Lemma",
    )
    pos_selector = mo.ui.dropdown(
        options={"Verb": "verb", "Noun": "noun", "Adjective": "adjective"},
        value="Verb",
        label="Part of speech",
    )
    mo.hstack([lemma_input, pos_selector], gap="1rem")
    return lemma_input, pos_selector


@app.cell(hide_code=True)
def _(eee, lemma_input, pos_selector):
    # Compute paradigm rows
    _lemma = lemma_input.value.strip()
    _pos = pos_selector.value

    _VERB_FORMS = [
        ("Pres Act 1sg",  {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act",  "Person": "1", "Number": "Sing"}),
        ("Pres Act 2sg",  {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act",  "Person": "2", "Number": "Sing"}),
        ("Pres Act 3sg",  {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act",  "Person": "3", "Number": "Sing"}),
        ("Pres Act 1pl",  {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act",  "Person": "1", "Number": "Plur"}),
        ("Pres Act 2pl",  {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act",  "Person": "2", "Number": "Plur"}),
        ("Pres Act 3pl",  {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act",  "Person": "3", "Number": "Plur"}),
        ("Impf Act 1sg",  {"Tense": "Past", "Aspect": "Imp",  "Voice": "Act",  "Person": "1", "Number": "Sing"}),
        ("Impf Act 2sg",  {"Tense": "Past", "Aspect": "Imp",  "Voice": "Act",  "Person": "2", "Number": "Sing"}),
        ("Impf Act 3sg",  {"Tense": "Past", "Aspect": "Imp",  "Voice": "Act",  "Person": "3", "Number": "Sing"}),
        ("Impf Act 1pl",  {"Tense": "Past", "Aspect": "Imp",  "Voice": "Act",  "Person": "1", "Number": "Plur"}),
        ("Impf Act 2pl",  {"Tense": "Past", "Aspect": "Imp",  "Voice": "Act",  "Person": "2", "Number": "Plur"}),
        ("Impf Act 3pl",  {"Tense": "Past", "Aspect": "Imp",  "Voice": "Act",  "Person": "3", "Number": "Plur"}),
        ("Aor Act 1sg",   {"Tense": "Past", "Aspect": "Perf", "Voice": "Act",  "Person": "1", "Number": "Sing"}),
        ("Aor Act 2sg",   {"Tense": "Past", "Aspect": "Perf", "Voice": "Act",  "Person": "2", "Number": "Sing"}),
        ("Aor Act 3sg",   {"Tense": "Past", "Aspect": "Perf", "Voice": "Act",  "Person": "3", "Number": "Sing"}),
        ("Aor Act 1pl",   {"Tense": "Past", "Aspect": "Perf", "Voice": "Act",  "Person": "1", "Number": "Plur"}),
        ("Aor Act 2pl",   {"Tense": "Past", "Aspect": "Perf", "Voice": "Act",  "Person": "2", "Number": "Plur"}),
        ("Aor Act 3pl",   {"Tense": "Past", "Aspect": "Perf", "Voice": "Act",  "Person": "3", "Number": "Plur"}),
        ("Pres Pass 1sg", {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Pass", "Person": "1", "Number": "Sing"}),
        ("Pres Pass 2sg", {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Pass", "Person": "2", "Number": "Sing"}),
        ("Pres Pass 3sg", {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Pass", "Person": "3", "Number": "Sing"}),
        ("Pres Pass 1pl", {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Pass", "Person": "1", "Number": "Plur"}),
        ("Pres Pass 2pl", {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Pass", "Person": "2", "Number": "Plur"}),
        ("Pres Pass 3pl", {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Pass", "Person": "3", "Number": "Plur"}),
        ("Aor Pass 1sg",  {"Tense": "Past", "Aspect": "Perf", "Voice": "Pass", "Person": "1", "Number": "Sing"}),
        ("Aor Pass 2sg",  {"Tense": "Past", "Aspect": "Perf", "Voice": "Pass", "Person": "2", "Number": "Sing"}),
        ("Aor Pass 3sg",  {"Tense": "Past", "Aspect": "Perf", "Voice": "Pass", "Person": "3", "Number": "Sing"}),
        ("Aor Pass 1pl",  {"Tense": "Past", "Aspect": "Perf", "Voice": "Pass", "Person": "1", "Number": "Plur"}),
        ("Aor Pass 2pl",  {"Tense": "Past", "Aspect": "Perf", "Voice": "Pass", "Person": "2", "Number": "Plur"}),
        ("Aor Pass 3pl",  {"Tense": "Past", "Aspect": "Perf", "Voice": "Pass", "Person": "3", "Number": "Plur"}),
    ]

    _NOUN_FORMS = [
        ("Nom Sing", {"Number": "Sing", "Case": "Nom"}),
        ("Gen Sing", {"Number": "Sing", "Case": "Gen"}),
        ("Acc Sing", {"Number": "Sing", "Case": "Acc"}),
        ("Voc Sing", {"Number": "Sing", "Case": "Voc"}),
        ("Nom Plur", {"Number": "Plur", "Case": "Nom"}),
        ("Gen Plur", {"Number": "Plur", "Case": "Gen"}),
        ("Acc Plur", {"Number": "Plur", "Case": "Acc"}),
        ("Voc Plur", {"Number": "Plur", "Case": "Voc"}),
    ]

    _ADJ_FORMS = [
        ("Pos Masc Nom Sing",  {"Degree": "Pos", "Gender": "Masc", "Number": "Sing", "Case": "Nom"}),
        ("Pos Masc Gen Sing",  {"Degree": "Pos", "Gender": "Masc", "Number": "Sing", "Case": "Gen"}),
        ("Pos Masc Acc Sing",  {"Degree": "Pos", "Gender": "Masc", "Number": "Sing", "Case": "Acc"}),
        ("Pos Masc Nom Plur",  {"Degree": "Pos", "Gender": "Masc", "Number": "Plur", "Case": "Nom"}),
        ("Pos Masc Gen Plur",  {"Degree": "Pos", "Gender": "Masc", "Number": "Plur", "Case": "Gen"}),
        ("Pos Masc Acc Plur",  {"Degree": "Pos", "Gender": "Masc", "Number": "Plur", "Case": "Acc"}),
        ("Pos Fem Nom Sing",   {"Degree": "Pos", "Gender": "Fem",  "Number": "Sing", "Case": "Nom"}),
        ("Pos Fem Gen Sing",   {"Degree": "Pos", "Gender": "Fem",  "Number": "Sing", "Case": "Gen"}),
        ("Pos Fem Acc Sing",   {"Degree": "Pos", "Gender": "Fem",  "Number": "Sing", "Case": "Acc"}),
        ("Pos Fem Nom Plur",   {"Degree": "Pos", "Gender": "Fem",  "Number": "Plur", "Case": "Nom"}),
        ("Pos Fem Gen Plur",   {"Degree": "Pos", "Gender": "Fem",  "Number": "Plur", "Case": "Gen"}),
        ("Pos Fem Acc Plur",   {"Degree": "Pos", "Gender": "Fem",  "Number": "Plur", "Case": "Acc"}),
        ("Pos Neut Nom Sing",  {"Degree": "Pos", "Gender": "Neut", "Number": "Sing", "Case": "Nom"}),
        ("Pos Neut Gen Sing",  {"Degree": "Pos", "Gender": "Neut", "Number": "Sing", "Case": "Gen"}),
        ("Pos Neut Acc Sing",  {"Degree": "Pos", "Gender": "Neut", "Number": "Sing", "Case": "Acc"}),
        ("Pos Neut Nom Plur",  {"Degree": "Pos", "Gender": "Neut", "Number": "Plur", "Case": "Nom"}),
        ("Pos Neut Gen Plur",  {"Degree": "Pos", "Gender": "Neut", "Number": "Plur", "Case": "Gen"}),
        ("Pos Neut Acc Plur",  {"Degree": "Pos", "Gender": "Neut", "Number": "Plur", "Case": "Acc"}),
        ("Cmp Masc Nom Sing",  {"Degree": "Cmp", "Gender": "Masc", "Number": "Sing", "Case": "Nom"}),
        ("Cmp Fem Nom Sing",   {"Degree": "Cmp", "Gender": "Fem",  "Number": "Sing", "Case": "Nom"}),
        ("Cmp Neut Nom Sing",  {"Degree": "Cmp", "Gender": "Neut", "Number": "Sing", "Case": "Nom"}),
        ("Sup Masc Nom Sing",  {"Degree": "Sup", "Gender": "Masc", "Number": "Sing", "Case": "Nom"}),
        ("Sup Fem Nom Sing",   {"Degree": "Sup", "Gender": "Fem",  "Number": "Sing", "Case": "Nom"}),
        ("Sup Neut Nom Sing",  {"Degree": "Sup", "Gender": "Neut", "Number": "Sing", "Case": "Nom"}),
    ]

    _forms_map = {"verb": _VERB_FORMS, "noun": _NOUN_FORMS, "adjective": _ADJ_FORMS}
    rows = []
    if _lemma:
        for _label, _features in _forms_map.get(_pos, []):
            try:
                _result = eee.inflect(_lemma, _features, _pos, language="el")
                _forms_str = ", ".join(sorted(_result)) if _result else "—"
            except Exception as _exc:
                _forms_str = f"error: {_exc}"
            rows.append({"Form": _label, "Inflected forms": _forms_str})
    return (rows,)


@app.cell(hide_code=True)
def _(lemma_input, mo, rows):
    # Display paradigm table
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

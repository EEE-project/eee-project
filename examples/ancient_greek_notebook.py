# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.13",
#     "eee-project>=1.1.0",
#     "unimorph-backend-eee>=1.0.3",
#     "ancient-greek-backend-eee>=2.0.0",
# ]
# ///
"""Ancient Greek morphology demo using the eee package.

Run standalone (fetches packages from PyPI):
    uv run marimo run examples/ancient_greek_notebook.py

Run from within the repo (uses local packages):
    uv run marimo edit examples/ancient_greek_notebook.py
"""

import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import eee_project as eee
    from ancient_greek_backend_eee import AncientGreekBackend
    from unimorph_backend_eee import UniMorphBackend

    eee.register_backend("grc", AncientGreekBackend())
    eee.register_backend("grc", UniMorphBackend(language="grc"), backend="unimorph")

    # One named backend per bundled period/corpus preset, so this general demo
    # notebook can show off any of them -- not just the tiny Pratt teaching set
    # the bare default above uses. for_period() resolves each preset's lexicon
    # list from a single shared source in ancient-greek-backend-eee (see its
    # own _PERIOD_PRESETS for why e.g. "byzantine" merges onto a Koine/Attic
    # base) -- new presets only need a name added there, not a lexicon list
    # hand-copied into every consumer including this one.
    for _period_name, _period in [
        ("ag-homer", "epic"),
        ("ag-lsj", "attic"),
        ("ag-lxx", "hellenistic_koine"),
        ("ag-morphgnt", "roman_koine"),
        ("ag-byzantine", "byzantine"),
    ]:
        eee.register_backend("grc", AncientGreekBackend.for_period(_period), backend=_period_name)

    return eee, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Ancient Greek Morphology
    **[eee](https://codeberg.org/EEE-project/eee)** — language-agnostic morphology engine for the EEE project.

    Select a part of speech and backend, then pick a word from the corpus table.
    Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    pos_selector = mo.ui.dropdown(
        options={"Noun": "noun", "Verb": "verb", "Adjective": "adjective"},
        value="Noun",
        label="Part of speech",
    )
    gender_selector = mo.ui.dropdown(
        options={"— (all)": None, "Masc": "Masc", "Fem": "Fem", "Neut": "Neut"},
        value="— (all)",
        label="Gender",
    )
    backend_selector = mo.ui.dropdown(
        options={
            "ancient-greek (pratt)": None,
            "Epic Greek (homer)": "ag-homer",
            "Classical Attic (lsj)": "ag-lsj",
            "Hellenistic Koine (lxx)": "ag-lxx",
            "Roman Koine (morphgnt)": "ag-morphgnt",
            "Byzantine Greek (byzantine)": "ag-byzantine",
            "unimorph": "unimorph",
        },
        value="ancient-greek (pratt)",
        label="Backend",
    )
    return backend_selector, gender_selector, pos_selector


@app.cell(hide_code=True)
def _(backend_selector, eee, mo, pos_selector):
    _unimorph_verb = backend_selector.value == "unimorph" and pos_selector.value == "verb"
    if _unimorph_verb:
        corpus_table = None
        _display = mo.callout(
            mo.md("UniMorph has no Ancient Greek verb data — use **ancient-greek** backend"),
            kind="warn",
        )
    else:
        try:
            _available = eee.list_lemmas(pos_selector.value, language="grc", backend=backend_selector.value)
        except Exception:
            _available = []
        if _available:
            corpus_table = mo.ui.table(
                [{"Word": w} for w in _available],
                selection="single",
                label=f"Corpus words — {pos_selector.value} ({len(_available)})",
            )
            _display = corpus_table
        else:
            corpus_table = None
            _display = mo.md("")
    _display
    return (corpus_table,)


@app.cell(hide_code=True)
def _(backend_selector, gender_selector, mo, pos_selector):
    _controls = [backend_selector, pos_selector]
    if pos_selector.value == "adjective":
        _controls.append(gender_selector)
    mo.hstack(_controls, gap="1rem", justify="start")
    return


@app.cell(hide_code=True)
def _(backend_selector, corpus_table, eee, gender_selector, pos_selector):
    _lemma = corpus_table.value[0]["Word"] if (corpus_table is not None and corpus_table.value) else ""
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
                    f"{_g} {_case} {_number}",  # restore "Pos {_g}..." when Cmp/Sup re-enabled
                    {"Degree": "Pos", "Gender": _g, "Case": _case, "Number": _number},
                ))

    _GRC_DEF = {
        ("Masc","Sing","Nom"): "ὁ",    ("Masc","Sing","Gen"): "τοῦ",
        ("Masc","Sing","Dat"): "τῷ",   ("Masc","Sing","Acc"): "τόν",  ("Masc","Sing","Voc"): "",
        ("Masc","Plur","Nom"): "οἱ",   ("Masc","Plur","Gen"): "τῶν",
        ("Masc","Plur","Dat"): "τοῖς", ("Masc","Plur","Acc"): "τούς", ("Masc","Plur","Voc"): "",
        ("Fem", "Sing","Nom"): "ἡ",    ("Fem", "Sing","Gen"): "τῆς",
        ("Fem", "Sing","Dat"): "τῇ",   ("Fem", "Sing","Acc"): "τήν",  ("Fem", "Sing","Voc"): "",
        ("Fem", "Plur","Nom"): "αἱ",   ("Fem", "Plur","Gen"): "τῶν",
        ("Fem", "Plur","Dat"): "ταῖς", ("Fem", "Plur","Acc"): "τάς",  ("Fem", "Plur","Voc"): "",
        ("Neut","Sing","Nom"): "τό",   ("Neut","Sing","Gen"): "τοῦ",
        ("Neut","Sing","Dat"): "τῷ",   ("Neut","Sing","Acc"): "τό",   ("Neut","Sing","Voc"): "",
        ("Neut","Plur","Nom"): "τά",   ("Neut","Plur","Gen"): "τῶν",
        ("Neut","Plur","Dat"): "τοῖς", ("Neut","Plur","Acc"): "τά",   ("Neut","Plur","Voc"): "",
    }
    _forms_map = {"verb": _VERB_FORMS, "noun": _NOUN_FORMS, "adjective": _ADJ_FORMS}
    _fg_noun = _gender
    if _pos == "noun" and _fg_noun is None:
        for _g in ("Masc", "Fem", "Neut"):
            try:
                _r = eee.inflect(_lemma, {"Number": "Sing", "Case": "Nom", "Gender": _g}, _pos, language="grc", backend=backend_selector.value)
                if _lemma in (_r or set()):
                    _fg_noun = _g
                    break
            except Exception:
                pass
    _use_articles = _pos == "noun" and _fg_noun is not None
    rows = []
    if _lemma:
        for _label, _features in _forms_map.get(_pos, []):
            try:
                _result = eee.inflect(_lemma, _features, _pos, language="grc", backend=backend_selector.value)
                if _use_articles:
                    _fn = _features.get("Number", "")
                    _fc = _features.get("Case", "")
                    _art = _GRC_DEF.get((_fg_noun, _fn, _fc), "")
                    rows.append({
                        "Form":     _label,
                        "Definite": ", ".join(f"{_art} {f}".strip() for f in sorted(_result)) if _result else "—",
                    })
                else:
                    rows.append({"Form": _label, "Inflected forms": ", ".join(sorted(_result)) if _result else "—"})
            except Exception as _exc:
                if _use_articles:
                    rows.append({"Form": _label, "Definite": f"error: {_exc}"})
                else:
                    rows.append({"Form": _label, "Inflected forms": f"error: {_exc}"})
    return (rows,)


@app.cell(hide_code=True)
def _(corpus_table, mo, rows):
    _lemma = corpus_table.value[0]["Word"] if (corpus_table is not None and corpus_table.value) else ""
    if rows:
        _output = mo.ui.table(rows, selection=None)
    elif _lemma:
        _output = mo.md(f"No forms found for **{_lemma}**.")
    elif corpus_table is not None:
        _output = mo.md("Select a word from the corpus table above.")
    else:
        _output = mo.md("")
    _output
    return


if __name__ == "__main__":
    app.run()

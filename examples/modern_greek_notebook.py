# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.19.4",
#     "eee @ git+https://codeberg.org/EEE-project/eee.git@unimorph-backend",
# ]
#
# [tool.uv.sources]
# eee = { git = "https://codeberg.org/EEE-project/eee.git", branch = "unimorph-backend" }
# ///
"""Modern Greek morphology demo using the eee package.

Run standalone (fetches eee from Codeberg):
    uv run marimo run examples/modern_greek_notebook.py

Run from within the repo (uses local package):
    uv run marimo edit examples/modern_greek_notebook.py
"""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import eee

    return eee, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Modern Greek Morphology
    **[eee](https://codeberg.org/EEE-project/eee)** — language-agnostic morphology engine for the EEE project.

    Select a part of speech and backend. For the corpus-based backend pick a word from the table; for the algorithm-based backend type a lemma directly.
    Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    lemma_input = mo.ui.text(
        value="γυναίκα",
        placeholder="e.g. λύω, γυναίκα, καλός",
        label="Lemma",
    )
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
        options={"modern-greek": None, "unimorph": "unimorph"},
        value="modern-greek",
        label="Backend",
    )
    return backend_selector, gender_selector, lemma_input, pos_selector


@app.cell(hide_code=True)
def _(backend_selector, eee, gender_selector, lemma_input, mo, pos_selector):
    try:
        _available = eee.list_lemmas(pos_selector.value, language="el", backend=backend_selector.value)
    except Exception:
        _available = []
    _rows = (
        [{"Word": w, "Type": "deponent/pass" if w.endswith("μαι") else "active"} for w in _available]
        if pos_selector.value == "verb" and backend_selector.value != "unimorph"
        else [{"Word": w} for w in _available]
    )
    corpus_table = (
        mo.ui.table(
            _rows,
            selection="single",
            label=f"Corpus words — {pos_selector.value} ({len(_available)})",
        )
        if _available
        else None
    )
    corpus_table if corpus_table is not None else lemma_input
    return (corpus_table,)


@app.cell(hide_code=True)
def _(backend_selector, gender_selector, mo, pos_selector):
    _controls = [backend_selector, pos_selector]
    if pos_selector.value == "adjective":
        _controls.append(gender_selector)
    mo.hstack(_controls, gap="1rem", justify="start")
    return


@app.cell(hide_code=True)
def _(backend_selector, corpus_table, eee, gender_selector, lemma_input, pos_selector):
    _lemma = corpus_table.value[0]["Word"] if (corpus_table is not None and corpus_table.value) else lemma_input.value.strip()
    _pos = pos_selector.value
    _gender = gender_selector.value

    _EL_VERB_FORMS = []
    for _per, _num in [("1","Sing"),("2","Sing"),("3","Sing"),("1","Plur"),("2","Plur"),("3","Plur")]:
        _ns = "sg" if _num == "Sing" else "pl"
        _EL_VERB_FORMS += [
            (f"Pres {_per}{_ns}",       {"Tense":"Pres","Person":_per,"Number":_num},                None),
            (f"Impf {_per}{_ns}",       {"Tense":"Past","Aspect":"Imp","Person":_per,"Number":_num}, None),
            (f"Aor {_per}{_ns}",        {"Tense":"Past","Aspect":"Perf","Person":_per,"Number":_num},None),
            (f"Fut/Subj Ipfv {_per}{_ns}", {"Tense":"Fut","Aspect":"Imp","Person":_per,"Number":_num},  "θα/να"),
            (f"Fut/Subj Pfv {_per}{_ns}",  {"Tense":"Fut","Aspect":"Perf","Person":_per,"Number":_num}, "θα/να"),
            (f"Cond {_per}{_ns}",       {"Tense":"Past","Aspect":"Imp","Person":_per,"Number":_num}, "θα"),
            (f"Perf {_per}{_ns}",       {"Tense":"Perf","Person":_per,"Number":_num},                None),
            (f"Pqp {_per}{_ns}",        {"Tense":"Pqp","Person":_per,"Number":_num},                 None),
        ]
    for _num in ("Sing","Plur"):
        _ns = "sg" if _num == "Sing" else "pl"
        _EL_VERB_FORMS += [
            (f"Imp Cont 2{_ns}", {"Tense":"Pres","Mood":"Imp","Person":"2","Number":_num},  None),
            (f"Imp Aor 2{_ns}",  {"Mood":"Imp","Aspect":"Perf","Person":"2","Number":_num}, None),
        ]

    _NOUN_FORMS = []
    for _number in ("Sing", "Plur"):
        for _case in ("Nom", "Gen", "Acc", "Voc"):
            _feats = {"Number": _number, "Case": _case}
            if _gender:
                _feats["Gender"] = _gender
            _NOUN_FORMS.append((f"{_case} {_number}", _feats))

    _ADJ_GENDERS = [_gender] if _gender else ["Masc", "Fem", "Neut"]
    _ADJ_FORMS = []
    for _g in _ADJ_GENDERS:
        for _number in ("Sing", "Plur"):
            for _case in ("Nom", "Gen", "Acc"):
                _ADJ_FORMS.append((
                    f"{_g} {_case} {_number}",  # restore "Pos {_g}..." when Cmp/Sup re-enabled
                    {"Degree": "Pos", "Gender": _g, "Number": _number, "Case": _case},
                ))
    # Cmp/Sup correctness uncertain — re-enable after verification
    # for _g in _ADJ_GENDERS:
    #     _ADJ_FORMS.append((f"Cmp {_g} Nom Sing", {"Degree": "Cmp", "Gender": _g, "Number": "Sing", "Case": "Nom"}))
    #     _ADJ_FORMS.append((f"Sup {_g} Nom Sing", {"Degree": "Sup", "Gender": _g, "Number": "Sing", "Case": "Nom"}))

    rows = []
    if _lemma:
        if _pos == "verb":
            for _label, _feats, _particle in _EL_VERB_FORMS:
                try:
                    _result = eee.inflect(_lemma, _feats, _pos, language="el", backend=backend_selector.value)
                    if _result:
                        _joined = ", ".join(sorted(_result))
                        _forms_str = f"{_particle} {_joined}" if _particle else _joined
                    else:
                        _forms_str = "—"
                except Exception as _exc:
                    _forms_str = f"error: {_exc}"
                rows.append({"Form": _label, "Inflected forms": _forms_str})
        elif _pos == "noun":
            _EL_DEF = {
                ("Masc","Sing","Nom"): "ο",    ("Masc","Sing","Gen"): "του",
                ("Masc","Sing","Acc"): "τον",  ("Masc","Sing","Voc"): "",
                ("Masc","Plur","Nom"): "οι",   ("Masc","Plur","Gen"): "των",
                ("Masc","Plur","Acc"): "τους", ("Masc","Plur","Voc"): "",
                ("Fem", "Sing","Nom"): "η",    ("Fem", "Sing","Gen"): "της",
                ("Fem", "Sing","Acc"): "τη",   ("Fem", "Sing","Voc"): "",
                ("Fem", "Plur","Nom"): "οι",   ("Fem", "Plur","Gen"): "των",
                ("Fem", "Plur","Acc"): "τις",  ("Fem", "Plur","Voc"): "",
                ("Neut","Sing","Nom"): "το",   ("Neut","Sing","Gen"): "του",
                ("Neut","Sing","Acc"): "το",   ("Neut","Sing","Voc"): "",
                ("Neut","Plur","Nom"): "τα",   ("Neut","Plur","Gen"): "των",
                ("Neut","Plur","Acc"): "τα",   ("Neut","Plur","Voc"): "",
            }
            _EL_INDEF = {
                ("Masc","Sing","Nom"): "ένας", ("Masc","Sing","Gen"): "ενός", ("Masc","Sing","Acc"): "έναν",
                ("Fem", "Sing","Nom"): "μια",  ("Fem", "Sing","Gen"): "μιας", ("Fem", "Sing","Acc"): "μια",
                ("Neut","Sing","Nom"): "ένα",  ("Neut","Sing","Gen"): "ενός", ("Neut","Sing","Acc"): "ένα",
            }
            _fg_noun = _gender
            if _fg_noun is None:
                for _g in ("Masc", "Fem", "Neut"):
                    try:
                        _r = eee.inflect(_lemma, {"Number": "Sing", "Case": "Nom", "Gender": _g}, _pos, language="el", backend=backend_selector.value)
                        if _lemma in (_r or set()):
                            _fg_noun = _g
                            break
                    except Exception:
                        pass
            _use_articles = _fg_noun is not None
            for _label, _features in _NOUN_FORMS:
                _fn = _features["Number"]
                _fc = _features["Case"]
                try:
                    _result = eee.inflect(_lemma, _features, _pos, language="el", backend=backend_selector.value)
                    if _use_articles:
                        _da = _EL_DEF.get((_fg_noun, _fn, _fc), "")
                        _ia = _EL_INDEF.get((_fg_noun, _fn, _fc), "")
                        rows.append({
                            "Form":       _label,
                            "Definite":   ", ".join(f"{_da} {f}".strip() for f in sorted(_result)) if _result else "—",
                            "Indefinite": ", ".join(f"{_ia} {f}".strip() for f in sorted(_result)) if (_result and _ia) else "—",
                        })
                    else:
                        rows.append({"Form": _label, "Inflected forms": ", ".join(sorted(_result)) if _result else "—"})
                except Exception as _exc:
                    if _use_articles:
                        rows.append({"Form": _label, "Definite": f"error: {_exc}", "Indefinite": "—"})
                    else:
                        rows.append({"Form": _label, "Inflected forms": f"error: {_exc}"})
        else:  # adjective
            for _label, _features in _ADJ_FORMS:
                try:
                    _result = eee.inflect(_lemma, _features, _pos, language="el", backend=backend_selector.value)
                    rows.append({"Form": _label, "Inflected forms": ", ".join(sorted(_result)) if _result else "—"})
                except Exception as _exc:
                    rows.append({"Form": _label, "Inflected forms": f"error: {_exc}"})
    return (rows,)


@app.cell(hide_code=True)
def _(corpus_table, lemma_input, mo, rows):
    _lemma = corpus_table.value[0]["Word"] if (corpus_table is not None and corpus_table.value) else lemma_input.value.strip()
    if not _lemma:
        _output = mo.md("Enter a lemma above." if corpus_table is None else "Select a word from the corpus table above.")
    elif rows:
        _output = mo.ui.table(rows, selection=None)
    else:
        _output = mo.md(f"No forms found for **{_lemma}**.")
    _output

    return


if __name__ == "__main__":
    app.run()

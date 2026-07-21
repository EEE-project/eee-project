# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.13",
#     "eee-project @ git+https://codeberg.org/EEE-project/eee.git",
#     "modern-greek-backend-eee @ git+https://codeberg.org/EEE-project/modern-greek-backend-eee.git",
#     "unimorph-backend-eee @ git+https://codeberg.org/EEE-project/unimorph-backend-eee.git",
#     "ancient-greek-backend-eee @ git+https://codeberg.org/EEE-project/ancient-greek-backend-eee.git",
# ]
#
# [tool.uv.sources]
# eee-project = { git = "https://codeberg.org/EEE-project/eee.git" }
# modern-greek-backend-eee = { git = "https://codeberg.org/EEE-project/modern-greek-backend-eee.git" }
# unimorph-backend-eee = { git = "https://codeberg.org/EEE-project/unimorph-backend-eee.git" }
# ancient-greek-backend-eee = { git = "https://codeberg.org/EEE-project/ancient-greek-backend-eee.git" }
# ///
"""Greek morphology demo (Modern and Ancient) using the eee package.

Run standalone (fetches packages from Codeberg):
    uv run marimo run examples/greek_notebook.py

Run from within the repo (uses local packages):
    uv run marimo edit examples/greek_notebook.py
"""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import eee_project as eee
    from ancient_greek_backend_eee import AncientGreekBackend
    from modern_greek_backend_eee import ModernGreekBackend
    from unimorph_backend_eee import UniMorphBackend

    eee.register_backend("el", ModernGreekBackend())
    eee.register_backend("el", UniMorphBackend(language="el"), backend="unimorph")
    eee.register_backend("grc", AncientGreekBackend())
    eee.register_backend("grc", UniMorphBackend(language="grc"), backend="unimorph")

    return eee, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Greek Morphology — Modern / Ancient Greek
    **[eee](https://codeberg.org/EEE-project/eee)** — language-agnostic morphology engine for the EEE project.

    Select a language, enter a lemma and part of speech to see the full inflection paradigm.
    Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    language_selector = mo.ui.dropdown(
        options={"Modern Greek (el)": "el", "Ancient Greek (grc)": "grc"},
        value="Modern Greek (el)",
        label="Language",
    )
    pos_selector = mo.ui.dropdown(
        options={"Noun": "noun", "Verb": "verb", "Adjective": "adjective"},
        value="Noun",
        label="Part of speech",
    )
    return language_selector, pos_selector


@app.cell(hide_code=True)
def _(language_selector, mo):
    _default = "ancient-greek" if language_selector.value == "grc" else "modern-greek"
    backend_selector = mo.ui.dropdown(
        options={_default: None, "unimorph": "unimorph"},
        value=_default,
        label="Backend",
    )
    return (backend_selector,)


@app.cell(hide_code=True)
def _(mo):
    gender_selector = mo.ui.dropdown(
        options={"— (all)": None, "Masc": "Masc", "Fem": "Fem", "Neut": "Neut"},
        value="— (all)",
        label="Gender",
    )
    return (gender_selector,)


@app.cell(hide_code=True)
def _(language_selector, mo, pos_selector):
    _is_verb = pos_selector.value == "verb"
    if _is_verb and language_selector.value == "el":
        _tense_opts = {
            "— (all)": None,
            "Present (Ενεστώτας)": "pres",
            "Past Continuous (Παρατατικός)": "impf",
            "Past Simple (Αόριστος)": "aor",
            "Future Continuous (Εξακ. Μέλλ.)": "fut_cont",
            "Future Simple (Απλ. Μέλλ.)": "fut_simp",
            "Conditional (θα+Παρατ.)": "cond",
            "Imperative (Προστακτική)": "imp",
            "Perfect (Παρακείμενος)": "perf",
            "Pluperfect (Υπερσυντέλικος)": "pqp",
        }
        _voice_opts = {}
    elif _is_verb:  # grc
        _tense_opts = {
            "— (all)": None,
            "Present": "pres",
            "Aorist": "aor",
            "Future": "fut",
            "Perfect": "perf",
            "Pluperfect": "pqp",
            "Imperative": "imp",
            "Infinitive": "inf",
            "Participle": "part",
        }
        _voice_opts = {"— (all)": None, "Active": "act", "Middle": "mid", "Passive": "pass"}
    else:
        _tense_opts = _voice_opts = {"— (all)": None}
    tense_selector = mo.ui.dropdown(options=_tense_opts, value="— (all)", label="Tense")
    voice_selector = mo.ui.dropdown(options=_voice_opts, value="— (all)", label="Voice") if _voice_opts else None
    return tense_selector, voice_selector


@app.cell(hide_code=True)
def _(language_selector, mo, pos_selector):
    _LEMMA_DEFAULTS = {
        ("verb",      "el"):  ("γράφω",    "e.g. γράφω, μιλάω"),
        ("verb",      "grc"): ("λύω",      "e.g. λύω, βάλλω"),
        ("noun",      "el"):  ("πόλη",     "e.g. πόλη, σπίτι"),
        ("noun",      "grc"): ("θεός",     "e.g. θεός, σοφία, δεῖπνον"),
        ("adjective", "el"):  ("καλός",    "e.g. καλός, μεγάλος"),
        ("adjective", "grc"): ("ἀγαθός",   "e.g. ἀγαθός, ταχύς"),
    }
    _default_val, _placeholder = _LEMMA_DEFAULTS.get((pos_selector.value, language_selector.value), ("", ""))
    lemma_input = mo.ui.text(
        value=_default_val,
        placeholder=_placeholder,
        label="Lemma",
    )
    return (lemma_input,)


@app.cell(hide_code=True)
def _(backend_selector, eee, language_selector, lemma_input, mo, pos_selector):
    _unimorph_verb = backend_selector.value == "unimorph" and language_selector.value == "grc" and pos_selector.value == "verb"
    if _unimorph_verb:
        corpus_table = None
        _display = mo.callout(
            mo.md("UniMorph has no Ancient Greek verb data — use **ancient-greek** backend"),
            kind="warn",
        )
    else:
        try:
            _available = eee.list_lemmas(pos_selector.value, language=language_selector.value, backend=backend_selector.value)
        except Exception:
            _available = []
        if _available:
            _rows = (
                [{"Word": w, "Type": "deponent/pass" if w.endswith("μαι") else "active"} for w in _available]
                if language_selector.value == "el" and pos_selector.value == "verb" and backend_selector.value != "unimorph"
                else [{"Word": w} for w in _available]
            )
            corpus_table = mo.ui.table(
                _rows,
                selection="single",
                label=f"Corpus words — {pos_selector.value} ({len(_available)})",
            )
            _display = corpus_table
        else:
            corpus_table = None
            _display = lemma_input
    _display
    return (corpus_table,)


@app.cell(hide_code=True)
def _(
    backend_selector,
    gender_selector,
    language_selector,
    mo,
    pos_selector,
    tense_selector,
    voice_selector,
):
    _controls = [backend_selector, language_selector, pos_selector]
    if pos_selector.value == "adjective":
        _controls.append(gender_selector)
    if pos_selector.value == "verb":
        _controls.append(tense_selector)
        if voice_selector is not None:
            _controls.append(voice_selector)
    mo.hstack(_controls, gap="1rem", justify="start")
    return


@app.cell(hide_code=True)
def _(
    backend_selector,
    corpus_table,
    eee,
    gender_selector,
    language_selector,
    lemma_input,
    pos_selector,
    tense_selector,
    voice_selector,
):
    _lang = language_selector.value
    _pos = pos_selector.value
    if corpus_table is not None:
        _lemma = corpus_table.value[0]["Word"] if corpus_table.value else ""
    elif backend_selector.value == "unimorph" and _lang == "grc" and _pos == "verb":
        _lemma = ""
    else:
        _lemma = lemma_input.value.strip()
    _gender = gender_selector.value
    _tense_filter = tense_selector.value
    _voice_filter = voice_selector.value if voice_selector is not None else None
    _backend = backend_selector.value

    # ── Article tables (nouns / adjectives) ──────────────────────────────────────
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
    def _def_str(result, lang, gender, number, case):
        if not result or gender is None:
            return ", ".join(sorted(result)) if result else "—"
        art = (_EL_DEF if lang == "el" else _GRC_DEF).get((gender, number, case), "")
        return ", ".join(f"{art} {f}".strip() for f in sorted(result))

    def _indef_str(result, lang, gender, number, case):
        if lang != "el" or not result or gender is None:
            return "—"
        art = _EL_INDEF.get((gender, number, case), "")
        if not art:
            return "—"
        return ", ".join(f"{art} {f}".strip() for f in sorted(result))

    _EL_VERB_FORMS = []
    for _per, _num in [("1","Sing"),("2","Sing"),("3","Sing"),("1","Plur"),("2","Plur"),("3","Plur")]:
        _ns = "sg" if _num == "Sing" else "pl"
        _EL_VERB_FORMS += [
            (f"Present (Ενεστ.) {_per}{_ns}",          {"Tense":"Pres","Person":_per,"Number":_num},                None),
            (f"Past Cont (Παρατ.) {_per}{_ns}",        {"Tense":"Past","Aspect":"Imp","Person":_per,"Number":_num}, None),
            (f"Past Simple (Αόρ.) {_per}{_ns}",        {"Tense":"Past","Aspect":"Perf","Person":_per,"Number":_num},None),
            (f"Fut Cont (Εξακ. Μέλλ.) {_per}{_ns}",   {"Tense":"Fut","Aspect":"Imp","Person":_per,"Number":_num},  "θα/να"),
            (f"Fut Simple (Απλ. Μέλλ.) {_per}{_ns}",  {"Tense":"Fut","Aspect":"Perf","Person":_per,"Number":_num}, "θα/να"),
            (f"Conditional (θα+Παρατ.) {_per}{_ns}",  {"Tense":"Past","Aspect":"Imp","Person":_per,"Number":_num}, "θα"),
            (f"Perfect (Παρακ.) {_per}{_ns}",          {"Tense":"Perf","Person":_per,"Number":_num},                None),
            (f"Pluperfect (Υπερσ.) {_per}{_ns}",       {"Tense":"Pqp","Person":_per,"Number":_num},                 None),
        ]
    for _num in ("Sing","Plur"):
        _ns = "sg" if _num == "Sing" else "pl"
        _EL_VERB_FORMS += [
            (f"Imp Cont (Προστ. Ενεστ.) 2{_ns}", {"Tense":"Pres","Mood":"Imp","Person":"2","Number":_num},  None),
            (f"Imp Simple (Προστ. Αόρ.) 2{_ns}",  {"Mood":"Imp","Aspect":"Perf","Person":"2","Number":_num}, None),
        ]

    _EL_TENSE_FILTER = {
        "pres":     lambda f, p: f.get("Tense") == "Pres" and "Mood" not in f,
        "impf":     lambda f, p: f.get("Tense") == "Past" and f.get("Aspect") == "Imp" and p is None,
        "aor":      lambda f, p: f.get("Tense") == "Past" and f.get("Aspect") == "Perf" and "Mood" not in f,
        "fut_cont": lambda f, p: f.get("Tense") == "Fut" and f.get("Aspect") == "Imp",
        "fut_simp": lambda f, p: f.get("Tense") == "Fut" and f.get("Aspect") == "Perf",
        "cond":     lambda f, p: f.get("Tense") == "Past" and p == "θα",
        "imp":      lambda f, p: f.get("Mood") == "Imp",
        "perf":     lambda f, p: f.get("Tense") == "Perf",
        "pqp":      lambda f, p: f.get("Tense") == "Pqp",
    }

    # ── grc verb filter ───────────────────────────────────────────────────────────
    _TENSE_MATCH_GRC = {
        "pres": lambda f: f.get("Tense") == "Pres",
        "aor":  lambda f: f.get("Tense") == "Aor",
        "fut":  lambda f: f.get("Tense") == "Fut",
        "perf": lambda f: f.get("Tense") == "Perf",
        "pqp":  lambda f: f.get("Tense") == "Pqp",
        "imp":  lambda f: f.get("Mood") == "Imp",
        "inf":  lambda f: f.get("VerbForm") == "Inf",
        "part": lambda f: f.get("VerbForm") == "Part",
    }
    _VOICE_MATCH = {
        "act":  lambda f: f.get("Voice") == "Act",
        "mid":  lambda f: f.get("Voice") == "Mid",
        "pass": lambda f: f.get("Voice") == "Pass",
    }

    def _filter_verbs_grc(forms, tense_val, voice_val):
        if tense_val is None and voice_val is None:
            return forms
        result = []
        for label, feats in forms:
            t_ok = tense_val is None or _TENSE_MATCH_GRC.get(tense_val, lambda f: True)(feats)
            v_ok = voice_val is None or _VOICE_MATCH.get(voice_val, lambda f: True)(feats)
            if t_ok and v_ok:
                result.append((label, feats))
        return result

    # ── Form definitions ──────────────────────────────────────────────────────────
    if _lang == "grc":
        _VERB_FORMS = []
        for _tense, _tl in [("Pres", "Pres"), ("Aor", "Aor"), ("Fut", "Fut"), ("Perf", "Perf"), ("Pqp", "Pqp")]:
            for _voice, _vl in [("Act", "Act"), ("Mid", "Mid"), ("Pass", "Pass")]:
                for _person, _number in [("1", "Sing"), ("2", "Sing"), ("3", "Sing"),
                                          ("1", "Plur"), ("2", "Plur"), ("3", "Plur")]:
                    _VERB_FORMS.append((
                        f"{_tl} {_vl} {_person}{'sg' if _number == 'Sing' else 'pl'} Ind",
                        {"VerbForm": "Fin", "Tense": _tense, "Voice": _voice,
                         "Mood": "Ind", "Person": _person, "Number": _number},
                    ))
                _VERB_FORMS.append((f"{_tl} {_vl} Inf", {"VerbForm": "Inf", "Tense": _tense, "Voice": _voice}))
                _VERB_FORMS.append((
                    f"{_tl} {_vl} Part NSM",
                    {"VerbForm": "Part", "Tense": _tense, "Voice": _voice,
                     "Case": "Nom", "Number": "Sing", "Gender": "Masc"},
                ))
        for _tense, _tl in [("Pres", "Pres"), ("Aor", "Aor")]:
            for _voice, _vl in [("Act", "Act"), ("Mid", "Mid"), ("Pass", "Pass")]:
                for _person, _number in [("2", "Sing"), ("2", "Plur"), ("3", "Sing"), ("3", "Plur")]:
                    _VERB_FORMS.append((
                        f"{_tl} {_vl} {_person}{'sg' if _number == 'Sing' else 'pl'} Imp",
                        {"VerbForm": "Fin", "Tense": _tense, "Voice": _voice,
                         "Mood": "Imp", "Person": _person, "Number": _number},
                    ))
        _NOUN_FORMS = []
        for _number in ("Sing", "Plur"):
            for _case in ("Nom", "Gen", "Dat", "Acc", "Voc"):
                _feats = {"Case": _case, "Number": _number}
                if _gender:
                    _feats["Gender"] = _gender
                _NOUN_FORMS.append((f"{_case} {_number}", _feats))
        _genders = [_gender] if _gender else ["Masc", "Fem", "Neut"]
        _ADJ_FORMS = []
        for _g in _genders:
            for _number in ("Sing", "Plur"):
                for _case in ("Nom", "Gen", "Dat", "Acc"):
                    _ADJ_FORMS.append((
                        f"{_g} {_case} {_number}",  # restore "Pos {_g}..." when Cmp/Sup re-enabled
                        {"Degree": "Pos", "Gender": _g, "Case": _case, "Number": _number},
                    ))
    else:  # el
        _NOUN_FORMS = [
            (f"{_case} {_number}", {"Number": _number, "Case": _case})
            for _number in ("Sing", "Plur")
            for _case in ("Nom", "Gen", "Acc", "Voc")
        ]
        _genders = [_gender] if _gender else ["Masc", "Fem", "Neut"]
        _ADJ_FORMS = [
            (f"{_g} {_c} {_n}", {"Degree": "Pos", "Gender": _g, "Number": _n, "Case": _c})  # restore "Pos {_g}..." when Cmp/Sup re-enabled
            for _g in _genders
            for _n in ("Sing", "Plur")
            for _c in ("Nom", "Gen", "Acc")
        ]

    rows = []
    if _lemma:
        if _pos == "verb" and _lang == "el":
            for _label, _feats, _particle in _EL_VERB_FORMS:
                _t_ok = _tense_filter is None or _EL_TENSE_FILTER.get(_tense_filter, lambda f, p: False)(_feats, _particle)
                if not _t_ok:
                    continue
                try:
                    _result = eee.inflect(_lemma, _feats, _pos, language=_lang, backend=_backend)
                    if _result:
                        _joined = ", ".join(sorted(_result))
                        _forms_str = f"{_particle} {_joined}" if _particle else _joined
                    else:
                        _forms_str = "—"
                except Exception as _exc:
                    _forms_str = f"error: {_exc}"
                rows.append({"Form": _label, "Inflected forms": _forms_str})
        elif _pos == "verb":  # grc
            _filtered = _filter_verbs_grc(_VERB_FORMS, _tense_filter, _voice_filter)
            for _label, _features in _filtered:
                try:
                    _result = eee.inflect(_lemma, _features, _pos, language=_lang, backend=_backend)
                    _fs = ", ".join(sorted(_result)) if _result else "—"
                    rows.append({"Form": _label, "Inflected forms": _fs})
                except Exception as _exc:
                    rows.append({"Form": _label, "Inflected forms": f"error: {_exc}"})
        else:  # noun / adjective
            _forms_map = {"noun": _NOUN_FORMS, "adjective": _ADJ_FORMS}
            _fg_noun = _gender
            if _pos == "noun" and _fg_noun is None:
                for _g in ("Masc", "Fem", "Neut"):
                    try:
                        _r = eee.inflect(_lemma, {"Number": "Sing", "Case": "Nom", "Gender": _g}, _pos, language=_lang, backend=_backend)
                        if _lemma in (_r or set()):
                            _fg_noun = _g
                            break
                    except Exception:
                        pass
            _use_articles = _pos == "noun" and _fg_noun is not None
            for _label, _features in _forms_map.get(_pos, []):
                try:
                    _result = eee.inflect(_lemma, _features, _pos, language=_lang, backend=_backend)
                    if _pos == "adjective":
                        rows.append({"Form": _label, "Inflected forms": ", ".join(sorted(_result)) if _result else "—"})
                    elif _use_articles:
                        _fg = _features.get("Gender", _fg_noun)
                        _fn = _features.get("Number", "")
                        _fc = _features.get("Case", "")
                        row = {"Form": _label, "Definite": _def_str(_result, _lang, _fg, _fn, _fc)}
                        if _lang == "el":
                            row["Indefinite"] = _indef_str(_result, _lang, _fg, _fn, _fc)
                        rows.append(row)
                    else:  # noun, gender unknown
                        rows.append({"Form": _label, "Inflected forms": ", ".join(sorted(_result)) if _result else "—"})
                except Exception as _exc:
                    if _pos == "adjective" or not _use_articles:
                        rows.append({"Form": _label, "Inflected forms": f"error: {_exc}"})
                    else:
                        row = {"Form": _label, "Definite": f"error: {_exc}"}
                        if _lang == "el":
                            row["Indefinite"] = "—"
                        rows.append(row)
    return (rows,)


@app.cell(hide_code=True)
def _(backend_selector, corpus_table, language_selector, lemma_input, mo, pos_selector, rows):
    _lang = language_selector.value
    _pos = pos_selector.value
    if corpus_table is not None:
        _lemma = corpus_table.value[0]["Word"] if corpus_table.value else ""
    elif backend_selector.value == "unimorph" and _lang == "grc" and _pos == "verb":
        _lemma = ""
    else:
        _lemma = lemma_input.value.strip()
    if rows:
        _wrap = [k for k in rows[0] if k != "Form"]
        _output = mo.ui.table(rows, selection=None, show_column_summaries=False,
                              show_data_types=False, wrapped_columns=_wrap)
    elif _lemma:
        _output = mo.md(f"No forms found for **{_lemma}** ({_lang}).")
    elif corpus_table is not None:
        _output = mo.md("Select a word from the corpus table above.")
    else:
        _output = mo.md("")
    _output
    return


if __name__ == "__main__":
    app.run()

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
"""Greek morphology demo (Modern and Ancient) using the eee package.

Run standalone (fetches packages from Codeberg):
    uv run marimo run examples/greek_notebook.py

Run from within the repo (uses local packages):
    uv run marimo edit examples/greek_notebook.py
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
    # Greek Morphology — Modern Greek (el) / Ancient Greek (grc)
    **[eee](https://codeberg.org/EEE-project/eee)** — language-agnostic morphology for the EEE project.

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
        options={"Verb": "verb", "Noun": "noun", "Adjective": "adjective"},
        value="Verb",
        label="Part of speech",
    )
    return language_selector, pos_selector


@app.cell(hide_code=True)
def _(mo, pos_selector):
    _is_noun = pos_selector.value == "noun"
    gender_selector = mo.ui.dropdown(
        options={"Masc": "Masc", "Fem": "Fem", "Neut": "Neut"} if _is_noun
            else {"— (all)": None, "Masc": "Masc", "Fem": "Fem", "Neut": "Neut"},
        value="Masc" if _is_noun else "— (all)",
        label="Gender",
    )
    return (gender_selector,)


@app.cell(hide_code=True)
def _(language_selector, mo, pos_selector):
    _is_verb = pos_selector.value == "verb"
    if _is_verb and language_selector.value == "el":
        _tense_opts = {
            "— (all)": None,
            "Present": "pres",
            "Imperfect": "impf",
            "Aorist": "aor",
            "Dependent": "dep",
            "Future": "fut",
            "Subjunctive": "subj",
            "Conditional": "cond",
            "Imperative": "imp",
            "Participle": "part",
        }
        _voice_opts = {"— (all)": None, "Active": "act", "Passive": "pass"}
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
    voice_selector = mo.ui.dropdown(options=_voice_opts, value="— (all)", label="Voice")
    return tense_selector, voice_selector


@app.cell(hide_code=True)
def _(gender_selector, language_selector, mo, pos_selector):
    _LEMMA_DEFAULTS = {
        ("verb",      "el",  None):   ("γράφω",    "e.g. γράφω, μιλάω"),
        ("verb",      "grc", None):   ("λύω",      "e.g. λύω, βάλλω"),
        ("noun",      "el",  None):   ("πόλη",     "e.g. πόλη, σπίτι"),
        ("noun",      "el",  "Masc"): ("δάσκαλος", "e.g. δάσκαλος, πατέρας"),
        ("noun",      "el",  "Fem"):  ("πόλη",     "e.g. πόλη, γυναίκα"),
        ("noun",      "el",  "Neut"): ("σπίτι",    "e.g. σπίτι, παιδί"),
        ("noun",      "grc", None):   ("θεός",     "e.g. θεός, σοφία, δεῖπνον"),
        ("noun",      "grc", "Masc"): ("θεός",     "e.g. θεός, ἀνήρ, βασιλεύς"),
        ("noun",      "grc", "Fem"):  ("σοφία",    "e.g. σοφία, πόλις, νύξ"),
        ("noun",      "grc", "Neut"): ("δεῖπνον",  "e.g. δεῖπνον, ἔτος, ὕδωρ"),
        ("adjective", "el",  None):   ("καλός",    "e.g. καλός, μεγάλος"),
        ("adjective", "grc", None):   ("ἀγαθός",   "e.g. ἀγαθός, ταχύς"),
    }
    _gender = gender_selector.value
    _key = (pos_selector.value, language_selector.value, _gender)
    _default_val, _placeholder = _LEMMA_DEFAULTS.get(
        _key, _LEMMA_DEFAULTS.get((pos_selector.value, language_selector.value, None), ("", ""))
    )
    lemma_input = mo.ui.text(
        value=_default_val,
        placeholder=_placeholder,
        label="Lemma",
    )
    return (lemma_input,)


@app.cell(hide_code=True)
def _(
    gender_selector,
    language_selector,
    lemma_input,
    mo,
    pos_selector,
    tense_selector,
    voice_selector,
):
    _gender_widget = gender_selector if pos_selector.value != "verb" else mo.md("")
    _main_row = mo.hstack([language_selector, lemma_input, pos_selector, _gender_widget], gap="1rem", justify="end")
    if pos_selector.value == "verb":
        _verb_row = mo.hstack([tense_selector, voice_selector], gap="1rem", justify="end")
        _output = mo.vstack([_main_row, _verb_row])
    else:
        _output = _main_row
    _output
    return


@app.cell(hide_code=True)
def _(
    eee,
    gender_selector,
    language_selector,
    lemma_input,
    pos_selector,
    tense_selector,
    voice_selector,
):
    _lang = language_selector.value
    _lemma = lemma_input.value.strip()
    _pos = pos_selector.value
    _gender = gender_selector.value
    _tense_filter = tense_selector.value
    _voice_filter = voice_selector.value

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
    _EL_PRONOUNS = {
        ("pri","sg"): "εγώ",   ("sec","sg"): "εσύ",   ("ter","sg"): "αυτός/αυτή/αυτό",
        ("pri","pl"): "εμείς", ("sec","pl"): "εσείς", ("ter","pl"): "αυτοί/αυτές/αυτά",
    }
    _GRC_PRONOUNS = {
        ("1","Sing"): "ἐγώ",   ("2","Sing"): "σύ",     ("3","Sing"): "αὐτός/αὐτή/αὐτό",
        ("1","Plur"): "ἡμεῖς", ("2","Plur"): "ὑμεῖς", ("3","Plur"): "αὐτοί/αὐταί/αὐτά",
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

    # ── el verb paradigm walker ───────────────────────────────────────────────────
    def _el_verb_rows(paradigm, tense_f, voice_f):
        rows = []

        def _w(tense, voice, mood):
            return paradigm.get(tense, {}).get(voice, {}).get(mood, {})

        def _tense_ok(tk):
            if tense_f is None:
                return True
            if tense_f == "fut":
                return tk in ("fut_cont", "fut_simp")
            if tense_f == "subj":
                return tk in ("subj_pres", "subj_aor")
            return tense_f == tk

        def _voice_ok(voice):
            if voice_f is None:
                return True
            return (voice_f == "act") == (voice == "active")

        def _add(label_prefix, tk, tense, voice, mood, particle=""):
            if not (_tense_ok(tk) and _voice_ok(voice)):
                return
            v_l = "Act" if voice == "active" else "Pass"
            path = _w(tense, voice, mood)
            if mood == "imp":
                for num, num_l in [("sg", "2sg"), ("pl", "2pl")]:
                    forms = path.get(num, {}).get("sec", set())
                    if forms:
                        fs = ", ".join(f"{particle} {f}".strip() for f in sorted(forms))
                        rows.append({"Form": f"{label_prefix} {v_l} {num_l}", "Inflected forms": fs})
            else:
                for num, num_s in [("sg", "sg"), ("pl", "pl")]:
                    nd = path.get(num, {})
                    for per, per_n in [("pri", "1"), ("sec", "2"), ("ter", "3")]:
                        forms = nd.get(per, set())
                        if forms:
                            _pron = _EL_PRONOUNS.get((per, num), "")
                            _pfx = " ".join(x for x in [_pron, particle] if x)
                            fs = ", ".join(f"{_pfx} {f}".strip() for f in sorted(forms))
                            rows.append({"Form": f"{label_prefix} {v_l} {per_n}{num_s}", "Inflected forms": fs})

        for _v in ["active", "passive"]:
            _add("Pres Ind",  "pres",      "present",     _v, "ind")
            _add("Impf",      "impf",      "paratatikos", _v, "ind")
            _add("Aor Ind",   "aor",       "aorist",      _v, "ind")
            _add("Dep",       "dep",       "conjunctive", _v, "ind")
            _add("θα+Pres",   "fut_cont",  "present",     _v, "ind", "θα")
            _add("θα+Dep",    "fut_simp",  "conjunctive", _v, "ind", "θα")
            _add("να+Pres",   "subj_pres", "present",     _v, "ind", "να")
            _add("να+Dep",    "subj_aor",  "conjunctive", _v, "ind", "να")
            _add("θα+Impf",   "cond",      "paratatikos", _v, "ind", "θα")
            _add("Imp Pres",  "imp",       "present",     _v, "imp")
            _add("Imp Aor",   "imp",       "conjunctive", _v, "imp")

        if _tense_ok("part"):
            forms = paradigm.get("act_pres_participle", set())
            if forms and isinstance(forms, set):
                rows.append({"Form": "Act Pres Part", "Inflected forms": ", ".join(sorted(forms))})
            for pk, lbl_pfx in [
                ("pass_pres_participle",      "Pass Pres Part"),
                ("active_aorist_participle",  "Act Aor Part"),
                ("passive_perfect_participle","Pass Perf Part"),
            ]:
                part = paradigm.get(pk, {})
                if part and isinstance(part, dict):
                    for n_k, n_l in [("sg","Sg"), ("pl","Pl")]:
                        for g_k, g_l in [("masc","Masc"), ("fem","Fem"), ("neut","Neut")]:
                            fms = part.get(n_k, {}).get(g_k, {}).get("nom", set())
                            if fms:
                                rows.append({"Form": f"{lbl_pfx} {g_l} Nom {n_l}",
                                             "Inflected forms": ", ".join(sorted(fms))})
        return rows

    # ── grc verb filter (unchanged) ───────────────────────────────────────────────
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
                        f"Pos {_g} {_case} {_number}",
                        {"Degree": "Pos", "Gender": _g, "Case": _case, "Number": _number},
                    ))
    else:  # el
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
            (f"Pos {_g} {_c} {_n}", {"Degree": "Pos", "Gender": _g, "Number": _n, "Case": _c})
            for _g in ("Masc", "Fem", "Neut")
            for _n in ("Sing", "Plur")
            for _c in ("Nom", "Gen", "Acc")
        ]

    # ── Compute rows ──────────────────────────────────────────────────────────────
    rows = []
    if _lemma:
        if _pos == "verb" and _lang == "el":
            from eee.backends import modern_greek as _mg_mod
            try:
                _paradigm = _mg_mod.ModernGreekBackend().paradigm(_lemma, "verb")
                rows = _el_verb_rows(_paradigm, _tense_filter, _voice_filter)
            except Exception as _exc:
                rows = [{"Form": "error", "Inflected forms": str(_exc)}]
        elif _pos == "verb":  # grc
            _filtered = _filter_verbs_grc(_VERB_FORMS, _tense_filter, _voice_filter)
            for _label, _features in _filtered:
                try:
                    _result = eee.inflect(_lemma, _features, _pos, language=_lang)
                    _pron = ""
                    if _features.get("VerbForm") == "Fin" and _features.get("Mood") != "Imp":
                        _pron = _GRC_PRONOUNS.get((_features.get("Person"), _features.get("Number")), "")
                    _fs = ", ".join(f"{_pron} {f}".strip() for f in sorted(_result)) if _result else "—"
                    rows.append({"Form": _label, "Inflected forms": _fs})
                except Exception as _exc:
                    rows.append({"Form": _label, "Inflected forms": f"error: {_exc}"})
        else:  # noun / adjective
            _forms_map = {"noun": _NOUN_FORMS, "adjective": _ADJ_FORMS}
            for _label, _features in _forms_map.get(_pos, []):
                try:
                    _result = eee.inflect(_lemma, _features, _pos, language=_lang)
                    _fg = _features.get("Gender", _gender)
                    _fn = _features.get("Number", "")
                    _fc = _features.get("Case", "")
                    rows.append({
                        "Form":       _label,
                        "Definite":   _def_str(_result, _lang, _fg, _fn, _fc),
                        "Indefinite": _indef_str(_result, _lang, _fg, _fn, _fc),
                    })
                except Exception as _exc:
                    rows.append({"Form": _label, "Definite": f"error: {_exc}", "Indefinite": "—"})
    return (rows,)


@app.cell(hide_code=True)
def _(language_selector, lemma_input, mo, rows):
    if not lemma_input.value.strip():
        _output = mo.md("Enter a lemma above.")
    elif rows:
        _wrap = [k for k in rows[0] if k != "Form"]
        _output = mo.ui.table(rows, selection=None, show_column_summaries=False,
                              show_data_types=False, wrapped_columns=_wrap)
    else:
        _output = mo.md(
            f"No forms found for **{lemma_input.value.strip()}** "
            f"({language_selector.value})."
        )
    _output
    return


if __name__ == "__main__":
    app.run()

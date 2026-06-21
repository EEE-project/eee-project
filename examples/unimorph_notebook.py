# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.8",
#     "eee-project @ git+https://codeberg.org/EEE-project/eee.git",
#     "unimorph-backend-eee @ git+https://codeberg.org/EEE-project/unimorph-backend-eee.git",
# ]
#
# [tool.uv.sources]
# eee-project = { git = "https://codeberg.org/EEE-project/eee.git" }
# unimorph-backend-eee = { git = "https://codeberg.org/EEE-project/unimorph-backend-eee.git" }
# ///
"""Interactive UniMorph inflection browser — all 187 languages.

Bundled languages (ell, grc, lat, rus, spa, tur) work offline.
All others are fetched from GitHub on first selection and cached locally.

Run standalone (fetches from Codeberg):
    uv run marimo run examples/unimorph_notebook.py

Run from within the repo (uses local packages):
    uv run marimo edit examples/unimorph_notebook.py
"""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import eee_project as eee
    from unimorph_backend_eee import UniMorphBackend
    from unimorph_backend_eee.fetch import fetch_language_list, register_language
    from unimorph_backend_eee.backend import _SUPPORTED_POS

    BUNDLED_LANGS = set(_SUPPORTED_POS.keys())
    BUNDLED_LANG_NAMES = {
        "ell": "Modern Greek", "grc": "Ancient Greek", "lat": "Latin",
        "rus": "Russian", "spa": "Spanish", "tur": "Turkish",
    }
    return (
        BUNDLED_LANGS,
        BUNDLED_LANG_NAMES,
        UniMorphBackend,
        eee,
        fetch_language_list,
        mo,
        register_language,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # UniMorph Inflection Browser

    **[unimorph-backend-eee](https://codeberg.org/EEE-project/unimorph-backend-eee)** — TSV-lookup
    backend for all 187 languages in the UniMorph corpus. Bundled languages work offline;
    others are downloaded from GitHub on first use and cached locally.
    Feature keys follow [Universal Dependencies FEATS](https://universaldependencies.org/u/feat/index.html).
    """)
    return


@app.cell(hide_code=True)
def _(BUNDLED_LANGS, BUNDLED_LANG_NAMES, fetch_language_list, mo):
    with mo.status.spinner("Loading language list…"):
        _langs = fetch_language_list()

    if not _langs:
        _langs = [{"code": c, "name": BUNDLED_LANG_NAMES.get(c, "")} for c in sorted(BUNDLED_LANGS)]

    lang_options = {}
    for _l in _langs:
        _c = _l["code"]
        _n = _l["name"]
        _tag = " [bundled]" if _c in BUNDLED_LANGS else ""
        _label = f"{_n} ({_c}){_tag}" if _n else f"{_c}{_tag}"
        lang_options[_label] = _c
    return (lang_options,)


@app.cell(hide_code=True)
def _(lang_options, mo):
    _POS_OPTIONS = {
        "Noun":      "noun",
        "Adjective": "adjective",
        "Verb":      "verb",
    }
    _default_lang = next(
        (k for k, v in lang_options.items() if v == "ell"), next(iter(lang_options))
    )
    lang_selector = mo.ui.dropdown(
        options=lang_options, value=_default_lang, label="Language",
        searchable=True,
    )
    pos_selector = mo.ui.dropdown(options=_POS_OPTIONS, value="Noun", label="Part of speech")
    _TERMS_OPTIONS = {
        "English": "",
        "Greek (ell)": "ell",
        "Ancient Greek (grc)": "grc",
        "Latin (lat)": "lat",
        "Russian (rus)": "rus",
        "Spanish (spa)": "spa",
        "Turkish (tur)": "tur",
    }
    terms_lang = mo.ui.dropdown(options=_TERMS_OPTIONS, value="English", label="Terms")
    return lang_selector, pos_selector, terms_lang


@app.cell(hide_code=True)
def _(lang_selector, mo, pos_selector, terms_lang):
    _show_terms = lang_selector.value in {"ell", "grc", "lat", "rus", "spa", "tur"}
    mo.hstack(
        [lang_selector, pos_selector] + ([terms_lang] if _show_terms else []),
        gap="1rem", justify="start",
    )
    return


@app.cell(hide_code=True)
def _(UniMorphBackend, lang_selector, mo, pos_selector, register_language):
    _lang = lang_selector.value
    _pos  = pos_selector.value

    with mo.status.spinner(f"Loading {_lang}…"):
        try:
            unimorph_index, pos_list = register_language(_lang)
            backend = UniMorphBackend(_lang)
            _load_error = None
        except Exception as _e:
            unimorph_index, pos_list, backend = {}, [], None
            _load_error = str(_e)

    corpus_table = None
    if _load_error:
        _out = mo.callout(mo.md(f"**Failed to load `{_lang}`:** {_load_error}"), kind="danger")
    elif _pos not in pos_list:
        _out = mo.callout(
            mo.md(f"`{_pos}` not available for **{_lang}**. Available: {', '.join(pos_list) or 'none'}"),
            kind="warn",
        )
    else:
        _pos_token = {"noun": "N", "adjective": "ADJ", "verb": "V"}[_pos]
        _lemmas = sorted({lm for (lm, tag) in unimorph_index
                          if tag.startswith(_pos_token + ";") or tag == _pos_token})
        corpus_table = (
            mo.ui.table([{"Word": w} for w in _lemmas], selection="single",
                        label=f"Corpus — {_pos} ({len(_lemmas)})")
            if _lemmas else None
        )
        _out = corpus_table if corpus_table is not None else mo.md("_No corpus entries for this POS._")
    _out
    return backend, corpus_table, pos_list, unimorph_index


@app.cell(hide_code=True)
def _(corpus_table, lang_selector, mo, pos_list, pos_selector):
    _pos = pos_selector.value
    if _pos not in pos_list:
        lemma_input = mo.ui.text(value="", label="Lemma", disabled=True)
    else:
        _DEFAULTS = {
            ("ell", "noun"): "γυναίκα", ("ell", "verb"): "ιατρεύω",
            ("ell", "adjective"): "ανιαρός", ("grc", "noun"): "βοηθός",
            ("grc", "adjective"): "ἄγναπτος", ("lat", "noun"): "puella",
            ("lat", "adjective"): "lūminōsus", ("rus", "noun"): "работа",
            ("rus", "adjective"): "красивый", ("spa", "noun"): "casa",
            ("spa", "adjective"): "grande", ("tur", "noun"): "köpek",
        }
        _default = _DEFAULTS.get((lang_selector.value, _pos), "")
        lemma_input = mo.ui.text(value=_default, placeholder="type a lemma…", label="Lemma")
    if corpus_table is None:
        lemma_input
    return (lemma_input,)


@app.cell(hide_code=True)
def _(
    backend,
    corpus_table,
    eee,
    lang_selector,
    lemma_input,
    pos_list,
    pos_selector,
    terms_lang,
    unimorph_index,
):
    _lang = lang_selector.value
    _pos  = pos_selector.value
    _lemma = (
        corpus_table.value[0]["Word"]
        if corpus_table is not None and corpus_table.value
        else ("" if corpus_table is not None else lemma_input.value.strip())
    )

    _LOCALE_TERMS: dict[str, dict[str, str]] = {
        "ell": {
            "Nom": "Ονομ.", "Gen": "Γεν.", "Acc": "Αιτ.", "Voc": "Κλητ.",
            "Sing": "Εν.", "Plur": "Πλ.",
            "Ma": "Αρσ.", "Fe": "Θηλ.", "Ne": "Ουδ.",
            "prs": "Ενεστ.", "impf": "Παρτ.", "aor": "Αόρ.", "fut": "Μελλ.",
            "1sg": "1 εν.", "2sg": "2 εν.", "3sg": "3 εν.",
            "1pl": "1 πλ.", "2pl": "2 πλ.", "3pl": "3 πλ.",
        },
        "grc": {
            "Nom": "Ὀνομ.", "Gen": "Γεν.", "Dat": "Δοτ.", "Acc": "Αἰτ.", "Voc": "Κλητ.",
            "Sing": "Εν.", "Plur": "Πλ.",
            "Ma": "Ἀρσ.", "Fe": "Θηλ.", "Ne": "Ουδ.",
        },
        "lat": {
            "Nom": "Nom.", "Gen": "Gen.", "Dat": "Dat.", "Acc": "Acc.",
            "Abl": "Abl.", "Voc": "Voc.",
            "Sing": "Sg.", "Plur": "Pl.",
            "Ma": "M.", "Fe": "F.", "Ne": "N.",
        },
        "rus": {
            "Nom": "Им.", "Gen": "Род.", "Dat": "Дат.", "Acc": "Вин.",
            "Ins": "Тв.", "Loc": "Пр.",
            "Sing": "Ед.", "Plur": "Мн.", "Sg": "Ед.", "Pl": "Мн.",
            "Ma": "М.", "Fe": "Ж.", "Ne": "Ср.",
            "Masc": "М.", "Fem": "Ж.", "Neut": "Ср.",
            "anim": "одуш.", "inan": "неодуш.",
        },
        "spa": {
            "Mas": "M.", "Fem": "F.",
            "Sing": "Sg.", "Plur": "Pl.",
        },
        "tur": {
            "Nom": "Yal.", "Gen": "İlgi.", "Dat": "Yön.",
            "Acc": "Bel.", "Abl": "Ayr.", "Loc": "Bul.",
            "Sing": "Tek.", "Plur": "Çoğ.",
        },
    }

    def _loc(label: str) -> str:
        terms = _LOCALE_TERMS.get(terms_lang.value, {})
        if not terms:
            return label
        return " ".join(terms.get(p, p) for p in label.split())

    def _noun_slots(cases):
        return [(f"{c} {n}", {"Case": c, "Number": n})
                for n in ("Sing", "Plur") for c in cases]

    def _adj_slots(cases, genders):
        return [(f"{g[:2]} {c} {n}", {"Case": c, "Number": n, "Gender": g})
                for g in genders for n in ("Sing", "Plur") for c in cases]

    _SLOTS: dict = {
        ("ell", "noun"):      _noun_slots(["Nom", "Gen", "Acc", "Voc"]),
        ("ell", "adjective"): _adj_slots(["Nom", "Gen", "Acc"], ["Masc", "Fem", "Neut"]),
        ("ell", "verb"): [
            (f"{lbl} {p}{'sg' if n=='Sing' else 'pl'}",
             {**feats, "Person": p, "Number": n})
            for lbl, feats in [
                ("prs",  {"Tense": "Pres"}),
                ("impf", {"Tense": "Past", "Aspect": "Imp"}),
                ("aor",  {"Tense": "Past", "Aspect": "Perf"}),
                ("fut",  {"Tense": "Fut"}),
            ]
            for p, n in [("1","Sing"),("2","Sing"),("3","Sing"),("1","Plur"),("2","Plur"),("3","Plur")]
        ],
        ("grc", "noun"):      _noun_slots(["Nom", "Gen", "Dat", "Acc", "Voc"]),
        ("grc", "adjective"): _adj_slots(["Nom", "Gen", "Dat", "Acc"], ["Masc", "Fem", "Neut"]),
        ("lat", "noun"):      _noun_slots(["Nom", "Gen", "Dat", "Acc", "Abl", "Voc"]),
        ("lat", "adjective"): _adj_slots(["Nom", "Gen", "Acc"], ["Masc", "Fem", "Neut"]),
        ("rus", "noun"):      _noun_slots(["Nom", "Gen", "Dat", "Acc", "Ins", "Loc"]),
        ("rus", "adjective"): [
            *_adj_slots(["Nom", "Gen", "Dat", "Ins"], ["Masc", "Fem", "Neut"]),
            ("Masc Acc Sg anim",  {"Case": "Acc", "Number": "Sing", "Gender": "Masc", "Animacy": "Anim"}),
            ("Masc Acc Sg inan",  {"Case": "Acc", "Number": "Sing", "Gender": "Masc", "Animacy": "Inan"}),
            ("Fem  Acc Sg",       {"Case": "Acc", "Number": "Sing", "Gender": "Fem"}),
            ("Neut Acc Sg",       {"Case": "Acc", "Number": "Sing", "Gender": "Neut"}),
            ("Acc Pl anim",       {"Case": "Acc", "Number": "Plur", "Animacy": "Anim"}),
            ("Acc Pl inan",       {"Case": "Acc", "Number": "Plur", "Animacy": "Inan"}),
        ],
        ("spa", "noun"):      [(f"{g[:3]} {n}", {"Gender": g, "Number": n})
                               for g in ("Masc", "Fem") for n in ("Sing", "Plur")],
        ("spa", "adjective"): [(f"{g[:3]} {n}", {"Gender": g, "Number": n})
                               for g in ("Masc", "Fem") for n in ("Sing", "Plur")],
        ("tur", "noun"):      _noun_slots(["Nom", "Gen", "Dat", "Acc", "Abl", "Loc"]),
    }

    def _generic_slots(lang, pos, index):
        pos_token = {"noun": "N", "adjective": "ADJ", "verb": "V"}[pos]
        prefix = pos_token + ";"
        tags = sorted({tag for (_, tag) in index
                       if tag.startswith(prefix) or tag == pos_token})
        return [(tag[len(pos_token)+1:] if ";" in tag else tag, None) for tag in tags]

    # Step 1: bundled UD slots (fast-path — no backend call needed)
    slots = _SLOTS.get((_lang, _pos))
    generic = False
    # Normalise "" (old "English" sentinel) → "en" for backend calls.
    terms_lang_norm = terms_lang.value or "en"

    if slots is None:
        # Steps 2-3: TOML template via backend (requested terms_lang, then "en" fallback).
        # Note: load_slot_template() also has an internal "en" fallback when the requested
        # file is absent, so step 3 is only strictly needed when the file exists but the
        # pos section is missing. The redundant stat in the "file absent" case is harmless.
        if backend is not None and hasattr(backend, "get_slot_templates"):
            slots = backend.get_slot_templates(_lang, _pos, terms_lang_norm)
            if slots is None and terms_lang_norm != "en":
                slots = backend.get_slot_templates(_lang, _pos, "en")

    if slots is None:
        # Step 4: raw tag dump — backwards compatible with non-bundled languages
        generic = True
        slots = _generic_slots(_lang, _pos, unimorph_index)

    rows = []
    if _lemma and _pos in pos_list and backend is not None:
        if generic:
            pos_token = {"noun": "N", "adjective": "ADJ", "verb": "V"}[_pos]
            for tag_suffix, _ in slots:
                full_tag = pos_token + ";" + tag_suffix if tag_suffix else pos_token
                forms = unimorph_index.get((_lemma, full_tag), set())
                if forms:
                    rows.append({"Tag": tag_suffix or pos_token,
                                  "Forms": ", ".join(sorted(forms))})
        elif slots and hasattr(slots[0], "tag_type"):
            # TOML template slots (list[SlotTemplate]); labels already in terms_lang.
            # Rows use "Form" key (not "Tag"), so display cell's `"Tag" in rows[0]` detection
            # is not affected regardless of what label the slot carries.
            for slot in slots:
                try:
                    result = eee.inflect_slot(_lemma, slot, _pos, language=_lang, backend=backend)
                    rows.append({
                        "Form": slot.label,
                        "Inflected forms": ", ".join(sorted(result)) if result else "—",
                    })
                except Exception as exc:
                    rows.append({
                        "Form": slot.label,
                        "Inflected forms": f"[{type(exc).__name__}]",
                    })
        else:
            # Bundled UD slots (list[(label_str, features_dict)])
            for _label, _feats in slots:
                try:
                    _result = backend.inflect(_lemma, _feats, _pos, language=_lang)
                    rows.append({"Form": _loc(_label),
                                 "Inflected forms": ", ".join(sorted(_result)) if _result else "—"})
                except Exception as _exc:
                    rows.append({"Form": _label, "Inflected forms": f"[{type(_exc).__name__}]"})
    return (rows,)


@app.cell(hide_code=True)
def _(corpus_table, lemma_input, mo, pos_list, pos_selector, rows):
    _pos = pos_selector.value
    _lemma = (
        corpus_table.value[0]["Word"]
        if corpus_table is not None and corpus_table.value
        else ("" if corpus_table is not None else lemma_input.value.strip())
    )
    _generic = bool(rows and "Tag" in rows[0])
    (
        mo.md("") if _pos not in pos_list else
        mo.md("_Select a word from the corpus table, or type a lemma above._") if not _lemma else
        mo.md(f"_No inflection data for **{_lemma}** ({_pos})._") if not rows else
        mo.vstack([
            mo.ui.table(rows, selection=None),
            mo.md("Tags follow the [UniMorph schema](https://unimorph.github.io/schema/)."),
        ]) if _generic else
        mo.ui.table(rows, selection=None)
    )
    return


if __name__ == "__main__":
    app.run()

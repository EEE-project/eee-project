# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.3",
#     "eee-project @ git+https://codeberg.org/EEE-project/eee-project.git",
#     "modern-greek-backend-eee @ git+https://codeberg.org/EEE-project/modern-greek-backend-eee.git",
#     "ancient-greek-backend-eee @ git+https://codeberg.org/EEE-project/ancient-greek-backend-eee.git",
# ]
#
# [tool.uv.sources]
# eee-project = { git = "https://codeberg.org/EEE-project/eee-project.git" }
# modern-greek-backend-eee = { git = "https://codeberg.org/EEE-project/modern-greek-backend-eee.git" }
# ancient-greek-backend-eee = { git = "https://codeberg.org/EEE-project/ancient-greek-backend-eee.git" }
# ///
"""GreekUtils demo — verb exercises, custom drill, greek_compare, and vocab quiz.

Combines the exercise API demo with the vocabulary quiz in a single notebook.

Run standalone (fetches packages from Codeberg):
    uv run marimo run examples/greek_exercise_notebook.py

Run from within the repo (uses local packages):
    uv run marimo edit examples/greek_exercise_notebook.py
"""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    from eee_project import eee_topbar
    eee_topbar(
        mo,
        back_url="https://codeberg.org/EEE-project",
        lang="en",
        titles={"en": "Greek Exercise & Quiz Demo", "el": "Άσκηση & Κουίζ"},
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Greek Exercise & Quiz Demo

    Demonstrates **`notebook_utils`** APIs in a single notebook:

    | API | Purpose |
    |---|---|
    | `GreekUtils(backend, mo, pd, eee_module=eee)` | verb / noun quiz widgets |
    | `GreekUtils(..., config=ANCIENT_GREEK)` | switch to 4-case Ancient Greek mode |
    | `gu.make_item_drill_rows(items, fields, ...)` | build multi-field drill input rows |
    | `gu.check_item_drill(items, inputs_2d, fields, ...)` | check custom drill answers |
    | `greek_compare(a, b, diacritics=...)` | student-answer comparison |
    | `gu.load_vocab_tsv(file, nb_dir=...)` | load vocabulary from TSV |
    | `gu.word_quiz_question(word, words, lang, random)` | multiple-choice question widget |
    | `gu.word_write_question(word, lang)` | write-the-word input with diacritics bar |
    | `eee_topbar` / `eee_footer` | navigation chrome |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Modern Greek — Verb Exercise
    """)
    return


@app.cell(hide_code=True)
def _(MODERN_GREEK, mo):
    _clk = lambda v: (v or 0) + 1
    _mg_verb = "γράφω"
    _tense_label = MODERN_GREEK.tense_labels["present"]["greek"]

    mg_form = mo.ui.array(
        [mo.ui.text(label=f"{lbl}:") for lbl in MODERN_GREEK.verb_labels],
    )
    mg_form.verb_word = _mg_verb
    mg_submit = mo.ui.button(label="✓ Check", on_click=_clk)

    mo.vstack([
        mo.md(f"Conjugate **{_mg_verb}** — {_tense_label} (Ενεστώτας)"),
        mg_form,
        mg_submit,
    ])
    return mg_form, mg_submit


@app.cell(hide_code=True)
def _(gu_mg, mg_form, mg_submit, mo):
    if mg_submit.value:
        _ok, _errs = gu_mg.check_verb_test("γράφω", mg_form, "present")
        _feedback = mo.md("**✓ Correct!**" if _ok else f"**Errors:**\n\n{_errs}")
    else:
        _feedback = mo.md("_Fill in all forms and click **✓ Check**._")
    _feedback
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Ancient Greek — Verb Exercise
    """)
    return


@app.cell(hide_code=True)
def _(ANCIENT_GREEK, mo):
    _clk_ag = lambda v: (v or 0) + 1
    _ag_verb = "λύω"
    _tense_label = ANCIENT_GREEK.tense_labels["present"]["greek"]

    ag_form = mo.ui.array(
        [mo.ui.text(label=f"{lbl}:") for lbl in ANCIENT_GREEK.verb_labels],
    )
    ag_form.verb_word = _ag_verb
    ag_submit = mo.ui.button(label="✓ Check", on_click=_clk_ag)

    mo.vstack([
        mo.md(f"Conjugate **{_ag_verb}** — {_tense_label} (active indicative)"),
        mo.md("_Diacritics are optional — `λυω` and `λύω` are both accepted._"),
        ag_form,
        ag_submit,
    ])
    return ag_form, ag_submit


@app.cell(hide_code=True)
def _(ag_form, ag_submit, gu_ag, mo):
    if ag_submit.value:
        _ok, _errs = gu_ag.check_verb_test("λύω", ag_form, "present")
        _feedback = mo.md("**✓ Correct!**" if _ok else f"**Errors:**\n\n{_errs}")
    else:
        _feedback = mo.md("_Fill in all forms and click **✓ Check**._")
    _feedback
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## `greek_compare` — Live Comparison

    Try editing the two fields below. Toggle **Require diacritics** to see how
    the comparison changes between monotonic/polytonic input.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    cmp_a = mo.ui.text(value="λεγε", label="Your answer")
    cmp_b = mo.ui.text(value="λέγε", label="Expected form")
    cmp_strict = mo.ui.switch(label="Require diacritics")
    mo.hstack([cmp_a, cmp_b, cmp_strict], gap="1.5rem", align="end")
    return cmp_a, cmp_b, cmp_strict


@app.cell(hide_code=True)
def _(cmp_a, cmp_b, cmp_strict, greek_compare, mo):
    _result = greek_compare(cmp_a.value, cmp_b.value, diacritics=cmp_strict.value)
    _icon = "✓" if _result else "✗"
    mo.md(
        f"`greek_compare({cmp_a.value!r}, {cmp_b.value!r}, diacritics={cmp_strict.value})` "
        f"→ **{_icon} {_result}**"
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## `make_item_drill_rows` + `check_item_drill` — Custom Drill

    For exercises that don't fit the standard verb/noun paradigm — multiple
    fields per item, custom prompts. Here: given an English meaning, fill in
    the **nominative** and **genitive** singular with article.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    drill_clear = mo.ui.button(label="↺ Clear")
    return (drill_clear,)


@app.cell(hide_code=True)
def _(drill_clear, gu_mg, mo):
    _dep = drill_clear.value
    _clk = lambda v: (v or 0) + 1
    drill_submit = mo.ui.button(label="✓ Check", on_click=_clk)
    drill_nouns = [
        {"meaning": "teacher", "nom": "ο δάσκαλος", "gen": "του δάσκαλου"},
        {"meaning": "woman",   "nom": "η γυναίκα",  "gen": "της γυναίκας"},
        {"meaning": "child",   "nom": "το παιδί",   "gen": "του παιδιού"},
    ]
    drill_inputs, _rows = gu_mg.make_item_drill_rows(
        drill_nouns, ["nom", "gen"],
        meaning_key="meaning",
        placeholders=["nom sg…", "gen sg…"],
    )
    mo.vstack([
        *_rows,
        mo.hstack([drill_clear, drill_submit], justify="end"),
    ])
    return drill_inputs, drill_nouns, drill_submit


@app.cell(hide_code=True)
def _(drill_inputs, drill_nouns, drill_submit, gu_mg, mo):
    _fb = gu_mg.check_item_drill(
        drill_nouns, drill_inputs, ["nom", "gen"],
        strict=False,
    ) if drill_submit.value else []
    mo.vstack(_fb) if _fb else mo.md("_Fill in the forms and click **✓ Check**._")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Vocabulary
    """)
    return


@app.cell(hide_code=True)
def _(WORDS, mo):
    mo.ui.table(
        [{"Word": w["form"], "Translation": w["meaning"]} for w in WORDS],
        selection=None,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Exercise 1 · Multiple Choice

    Pick the correct Ancient Greek word for the given translation.
    """)
    return


@app.cell(hide_code=True)
def _(WORDS, mo, random):
    cv_c, set_cv_c = mo.state(None)
    score_c, set_score_c = mo.state({"correct": 0, "total": 0})
    remaining_c, set_remaining_c = mo.state(None)

    if remaining_c() is None and WORDS:
        _s = random.sample(WORDS, len(WORDS))
        set_cv_c(_s[0])
        set_remaining_c(_s[1:])
    return cv_c, remaining_c, score_c, set_cv_c, set_remaining_c, set_score_c


@app.cell(hide_code=True)
def _(WORDS, cv_c, gu_ag, mo, random):
    if cv_c() is None:
        answer_radio = mo.ui.radio(options=[""])
    else:
        answer_radio, _ = gu_ag.word_quiz_question(cv_c(), WORDS, "en", random)
    return (answer_radio,)


@app.cell(hide_code=True)
def _(
    WORDS,
    answer_radio,
    cv_c,
    mo,
    random,
    remaining_c,
    score_c,
    set_cv_c,
    set_remaining_c,
    set_score_c,
):
    _done_c = cv_c() is None and remaining_c() is not None and not remaining_c()

    def _on_next_c(_):
        if cv_c() is None:
            _shuf = random.sample(WORDS, len(WORDS))
            set_cv_c(_shuf[0])
            set_remaining_c(_shuf[1:])
            set_score_c({"correct": 0, "total": 0})
        else:
            _ok = answer_radio.value == cv_c()["form"]
            set_score_c({"correct": score_c()["correct"] + int(_ok), "total": score_c()["total"] + 1})
            set_cv_c(remaining_c()[0] if remaining_c() else None)
            set_remaining_c(remaining_c()[1:] if remaining_c() else [])

    _s = score_c()
    if _done_c:
        _out = mo.vstack([
            mo.callout(mo.md(f"Done! Correct: **{_s['correct']}** / **{_s['total']}**"), kind="success"),
            mo.ui.button(label="Again", on_click=_on_next_c),
        ])
    else:
        _fb = mo.md("")
        if answer_radio.value is not None:
            _ok = answer_radio.value == cv_c()["form"]
            _color = "#2d9e2d" if _ok else "#d32f2f"
            _mark = "✓" if _ok else "✗"
            _fb = mo.md(f'<span style="color:{_color};font-weight:bold">{_mark} {cv_c()["meaning"]} → {cv_c()["form"]}</span>')
        _out = mo.vstack([
            mo.md(f"**{_s['total'] + 1}** / {len(WORDS)} — correct: {_s['correct']}"),
            answer_radio,
            _fb,
            mo.hstack([mo.ui.button(label="Next", on_click=_on_next_c)], justify="start"),
        ])
    _out
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Exercise 2 · Write the Word

    Type the Ancient Greek word from memory. The polytonic diacritics bar appears
    above the input — click a diacritic then type the vowel.
    """)
    return


@app.cell(hide_code=True)
def _(WORDS, mo, random):
    cv_w, set_cv_w = mo.state(None)
    score_w, set_score_w = mo.state({"correct": 0, "total": 0})
    remaining_w, set_remaining_w = mo.state(None)

    if remaining_w() is None and WORDS:
        _s = random.sample(WORDS, len(WORDS))
        set_cv_w(_s[0])
        set_remaining_w(_s[1:])
    return cv_w, remaining_w, score_w, set_cv_w, set_remaining_w, set_score_w


@app.cell(hide_code=True)
def _(cv_w, gu_ag, mo):
    if cv_w() is None:
        write_input_w = mo.ui.text(placeholder="Greek word…", full_width=True)
    else:
        write_input_w, _ = gu_ag.word_write_question(cv_w(), "en")
    check_btn_w = mo.ui.button(label="Check", on_click=lambda v: (v or 0) + 1)
    return check_btn_w, write_input_w


@app.cell(hide_code=True)
def _(cv_w, mo, remaining_w):
    _done_w = cv_w() is None and remaining_w() is not None and not remaining_w()
    next_btn_w = mo.ui.button(
        label="Again" if _done_w else "Next",
        on_click=lambda v: (v or 0) + 1,
    )
    return (next_btn_w,)


@app.cell(hide_code=True)
def _(
    WORDS,
    cv_w,
    gu_ag,
    next_btn_w,
    random,
    remaining_w,
    score_w,
    set_cv_w,
    set_remaining_w,
    set_score_w,
    write_input_w,
):
    if next_btn_w.value:
        _r = remaining_w()
        if _r is None:
            pass
        elif cv_w() is None:
            _shuf = random.sample(WORDS, len(WORDS))
            set_cv_w(_shuf[0])
            set_remaining_w(_shuf[1:])
            set_score_w({"correct": 0, "total": 0})
        else:
            _ok = gu_ag._ci(write_input_w.value.strip(), {cv_w()["form"]})
            set_score_w({"correct": score_w()["correct"] + int(_ok), "total": score_w()["total"] + 1})
            set_cv_w(_r[0] if _r else None)
            set_remaining_w(_r[1:] if _r else [])
    return


@app.cell(hide_code=True)
def _(
    WORDS,
    check_btn_w,
    cv_w,
    gu_ag,
    mo,
    next_btn_w,
    remaining_w,
    score_w,
    write_input_w,
):
    _done_w = cv_w() is None and remaining_w() is not None and not remaining_w()
    _s = score_w()
    if _done_w:
        _out = mo.vstack([
            mo.callout(mo.md(f"Done! Correct: **{_s['correct']}** / **{_s['total']}**"), kind="success"),
            next_btn_w,
        ])
    else:
        _meaning = cv_w().get("meaning", "") if cv_w() is not None else ""
        _typed = write_input_w.value.strip()
        if check_btn_w.value and _typed and cv_w() is not None:
            _ok = gu_ag._ci(_typed, {cv_w()["form"]})
            _color = "#2d9e2d" if _ok else "#d32f2f"
            _mark = "✓" if _ok else "✗"
            _fb = mo.md(f'<span style="color:{_color};font-weight:bold">{_mark} {_meaning} → {cv_w()["form"]}</span>')
        else:
            _fb = mo.md(f"*{_meaning}*") if _meaning else mo.md("")
        _out = mo.vstack([
            mo.md(f"**{_s['total'] + 1}** / {len(WORDS)} — correct: {_s['correct']}"),
            _fb,
            write_input_w,
            mo.hstack([check_btn_w, next_btn_w], justify="start"),
        ])
    _out
    return


@app.cell(hide_code=True)
def _(mo):
    from eee_project import eee_footer
    eee_footer(mo, lang="en")
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd
    import random
    from pathlib import Path
    import eee_project as eee
    from eee_project import (
        GreekUtils, MODERN_GREEK, ANCIENT_GREEK, greek_compare,
    )
    from modern_greek_backend_eee import ModernGreekBackend
    from ancient_greek_backend_eee import AncientGreekBackend

    _mg_backend = ModernGreekBackend()
    _ag_backend = AncientGreekBackend(lexicons=["pratt", "ltrg"])

    eee.register_backend("el", _mg_backend)
    eee.register_backend("grc", _ag_backend, backend="ancient-greek")
    eee.set_chain("grc", ["ancient-greek"])

    gu_mg = GreekUtils(_mg_backend, mo, pd, eee_module=eee)
    gu_ag = GreekUtils(_ag_backend, mo, pd, eee_module=eee, config=ANCIENT_GREEK)

    NB_DIR = Path(__file__).parent
    WORDS = gu_ag.load_vocab_tsv("vocab.tsv", nb_dir=NB_DIR)
    return (
        ANCIENT_GREEK,
        MODERN_GREEK,
        WORDS,
        greek_compare,
        gu_ag,
        gu_mg,
        mo,
        random,
    )


if __name__ == "__main__":
    app.run()

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
"""GreekUtils exercise notebook — demonstrates notebook_utils APIs.

Shows GreekUtils (Modern + Ancient Greek), eee_topbar/eee_footer, and
greek_compare in a working Marimo notebook.

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
        titles={"en": "Greek Exercise Demo", "el": "Άσκηση Ελληνικών"},
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Greek Exercise Demo

    This notebook demonstrates **`notebook_utils`** APIs:

    | API | Purpose |
    |---|---|
    | `GreekUtils(backend, mo, pd, eee_module=eee)` | verb / noun quiz widgets |
    | `GreekUtils(..., config=ANCIENT_GREEK)` | switch to 4-case Ancient Greek mode |
    | `gu.make_item_drill_rows(items, fields, ...)` | build multi-field drill input rows |
    | `gu.check_item_drill(items, inputs_2d, fields, ...)` | check custom drill answers |
    | `greek_compare(a, b, diacritics=...)` | student-answer comparison |
    | `eee_topbar` / `eee_footer` | navigation chrome |

    Three exercise sections below — Modern Greek verb, Ancient Greek verb, and a
    custom noun drill — backed by a real morphology backend via `eee_project`.
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
    from eee_project import eee_footer
    eee_footer(mo, lang="en")
    return


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd
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
    return ANCIENT_GREEK, MODERN_GREEK, greek_compare, gu_ag, gu_mg, mo


if __name__ == "__main__":
    app.run()

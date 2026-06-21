# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.3",
#     "eee-project @ git+https://codeberg.org/EEE-project/eee-project.git",
#     "ancient-greek-backend-eee @ git+https://codeberg.org/EEE-project/ancient-greek-backend-eee.git",
# ]
#
# [tool.uv.sources]
# eee-project = { git = "https://codeberg.org/EEE-project/eee-project.git" }
# ancient-greek-backend-eee = { git = "https://codeberg.org/EEE-project/ancient-greek-backend-eee.git" }
# ///
"""Vocabulary quiz demo — load_vocab_tsv + word_quiz_question + word_write_question.

Shows both quiz modes (multiple-choice and write-the-word) from a local TSV.

Run locally:
    uv run marimo edit examples/vocab_quiz_notebook.py --no-token

vocab.tsv must be in the same directory (included in this examples/ folder).
For a remote TSV, pass remote_base= to load_vocab_tsv and it downloads on first run.
"""

import marimo

__generated_with = "0.23.8"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Vocabulary Quiz Demo

    Demonstrates `GreekUtils` vocab quiz methods using a local TSV file.

    **Two exercise modes:**
    - **Exercise 1** — multiple choice: pick the correct Greek word for a Russian translation
    - **Exercise 2** — write the word: type the Greek word from memory
    """)
    return


@app.cell(hide_code=True)
def _():
    import random
    from pathlib import Path

    import marimo as mo
    from eee_project import ANCIENT_GREEK, GreekUtils

    gu = GreekUtils(mo_module=mo, config=ANCIENT_GREEK)

    # load_vocab_tsv reads Word/Translation columns from TSV files.
    # Pass remote_base= to auto-download missing files from Codeberg.
    NB_DIR = Path(__file__).parent
    WORDS = gu.load_vocab_tsv("vocab.tsv", nb_dir=NB_DIR)
    return WORDS, gu, mo, random


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
    ## Exercise 1 · Multiple choice
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
def _(WORDS, cv_c, gu, mo, random):
    if cv_c() is None:
        answer_radio = mo.ui.radio(options=[""])
    else:
        answer_radio, _ = gu.word_quiz_question(cv_c(), WORDS, "en", random)
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
    _done_c = cv_c() is None and remaining_c() is not None and len(remaining_c()) == 0

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
    elif cv_c() is None:
        mo.stop(True, mo.md(""))
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
    ## Exercise 2 · Write the word
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
def _(cv_w, gu, mo):
    _ = cv_w()
    if cv_w() is None:
        write_input_w = mo.ui.text(placeholder="Greek word…", full_width=True)
    else:
        write_input_w, _ = gu.word_write_question(cv_w(), "en")
    check_btn_w = mo.ui.button(label="Check", on_click=lambda v: (v or 0) + 1)
    return check_btn_w, write_input_w


@app.cell(hide_code=True)
def _(cv_w, mo, remaining_w):
    _done_w = cv_w() is None and remaining_w() is not None and len(remaining_w()) == 0
    next_btn_w = mo.ui.button(
        label="Again" if _done_w else "Next",
        on_click=lambda v: (v or 0) + 1,
    )
    return (next_btn_w,)


@app.cell(hide_code=True)
def _(
    WORDS,
    cv_w,
    gu,
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
            _ok = gu._ci(write_input_w.value.strip(), {cv_w()["form"]})
            set_score_w({"correct": score_w()["correct"] + int(_ok), "total": score_w()["total"] + 1})
            set_cv_w(_r[0] if _r else None)
            set_remaining_w(_r[1:] if _r else [])
    return


@app.cell(hide_code=True)
def _(
    WORDS,
    check_btn_w,
    cv_w,
    gu,
    mo,
    next_btn_w,
    remaining_w,
    score_w,
    write_input_w,
):
    _done_w = cv_w() is None and remaining_w() is not None and len(remaining_w()) == 0
    _s = score_w()
    if _done_w:
        _out = mo.vstack([
            mo.callout(mo.md(f"Done! Correct: **{_s['correct']}** / **{_s['total']}**"), kind='success'),
            next_btn_w,
        ])
    else:
        _meaning = cv_w().get('meaning', '') if cv_w() is not None else ''
        _typed = write_input_w.value.strip()
        if check_btn_w.value and _typed and cv_w() is not None:
            _ok = gu._ci(_typed, {cv_w()['form']})
            _color = '#2d9e2d' if _ok else '#d32f2f'
            _mark = '✓' if _ok else '✗'
            _fb = mo.md(f'<span style="color:{_color};font-weight:bold">{_mark} {_meaning} → {cv_w()["form"]}</span>')
        else:
            _fb = mo.md(f'*{_meaning}*') if _meaning else mo.md('')
        _out = mo.vstack([
            mo.md(f"**{_s['total'] + 1}** / {len(WORDS)} — correct: {_s['correct']}"),
            _fb,
            write_input_w,
            mo.hstack([check_btn_w, next_btn_w], justify='start'),
        ])
    _out
    return


if __name__ == "__main__":
    app.run()

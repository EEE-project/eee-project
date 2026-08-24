# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.13",
#     "eee-project>=1.1.0",
#     "modern-greek-backend-eee>=1.0.0",
#     "ancient-greek-backend-eee>=2.0.0",
#     "pandas==3.0.5",
# ]
# ///
"""GreekUtils demo — verb exercises, custom drill, greek_compare, and vocab quiz.

Combines the exercise API demo with the vocabulary quiz in a single notebook.

Run standalone (fetches packages from PyPI):
    uv run marimo run examples/greek_exercise_notebook.py

Run from within the repo (uses local packages):
    uv run marimo edit examples/greek_exercise_notebook.py
"""

import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Greek Exercise & Quiz Demo

    Demonstrates **`notebook_utils`** APIs in a single notebook:

    | API | Purpose |
    |:---|:---|
    | `GreekUtils(backend, mo, pd, eee_module=eee)` | verb / noun quiz widgets |
    | `GreekUtils(..., config=ANCIENT_GREEK)` | switch to 4-case Ancient Greek mode |
    | `gu.make_item_drill_rows(items, fields, ...)` | build multi-field drill input rows |
    | `gu.check_item_drill(items, inputs_2d, fields, ...)` | check custom drill answers |
    | `greek_compare(a, b, diacritics=...)` | student-answer comparison |
    | `gu.load_vocab_tsv(file, nb_dir=...)` | load vocabulary from TSV |
    | `gu.adverb_vocab(adjectives)` | derive adverb vocab from adjectives (καλός → καλῶς) |
    | `gu.word_quiz_widgets(...)` / `word_quiz_form(...)` | multiple-choice quiz — state, navigation, and display in one call |
    | `gu.word_drill_widgets(...)` / `word_drill_form(...)` | write-the-word drill — state, navigation, and display in one call |
    | `gu.paradigm_drill_widgets(labels, ...)` | form + Prev/Next/Restart widgets for a full-paradigm drill |
    | `gu.verb_paradigm_drill_form(...)` / `noun_...` / `adjective_...` | full-paradigm drill per POS — Enter-navigation, check, restart, and display in one call |
    | `gu.dirty_check_button(form, cap, cv, attr_name)` | Check button that turns orange when the form has unsaved changes |
    | `gu.noun_drill_meta(word)` | per-word noun metadata (`active_cases`, pluralia tantum) |
    | `gu.verb_slot_labels()` / `noun_slot_labels(cases)` / `adjective_slot_labels(mode)` | slot labels for the paradigm drills |
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Exercise 1 · `greek_compare` — Live Comparison

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
    ## Exercise 2 · `make_item_drill_rows` + `check_item_drill` — Custom Drill

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
def _(drill_clear, eee, gu_mg, mo):
    _dep = drill_clear.value
    drill_submit = mo.ui.button(label="✓ Check", on_click=eee.increment_counter)
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
    ## Exercise 3 · Multiple Choice

    Pick the correct Ancient Greek word for the given translation.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    cv_c, set_cv_c = mo.state(None)
    remaining_c, set_remaining_c = mo.state(None)
    score_c, set_score_c = mo.state({"correct": 0, "total": 0})
    history_c, set_history_c = mo.state([])
    future_c, set_future_c = mo.state([])
    restore_entry_c, set_restore_entry_c = mo.state(None)
    return (
        cv_c,
        future_c,
        history_c,
        remaining_c,
        restore_entry_c,
        score_c,
        set_cv_c,
        set_future_c,
        set_history_c,
        set_remaining_c,
        set_restore_entry_c,
        set_score_c,
    )


@app.cell(hide_code=True)
def _(WORDS, cv_c, gu_ag, history_c, remaining_c, restore_entry_c):
    answer_radio_c, next_btn_c, prev_btn_c = gu_ag.word_quiz_widgets(
        cv=cv_c(),
        remaining=remaining_c(),
        vocab=WORDS,
        restore_entry=restore_entry_c(),
        history_len=len(history_c()),
        lang="en",
    )
    return answer_radio_c, next_btn_c, prev_btn_c


@app.cell(hide_code=True)
def _(
    WORDS,
    answer_radio_c,
    cv_c,
    future_c,
    gu_ag,
    history_c,
    next_btn_c,
    prev_btn_c,
    remaining_c,
    restore_entry_c,
    score_c,
    set_cv_c,
    set_future_c,
    set_history_c,
    set_remaining_c,
    set_restore_entry_c,
    set_score_c,
):
    gu_ag.word_quiz_form(
        cv_c, set_cv_c, remaining_c, set_remaining_c,
        score_c, set_score_c, restore_entry_c, set_restore_entry_c,
        history_c, set_history_c, future_c, set_future_c,
        answer_radio_c, next_btn_c, prev_btn_c,
        vocab=WORDS,
        meaning_key="meaning",
        form_key="form",
        lang="en",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md("""
    ## Exercise 4 · Write the Word

    Type the Ancient Greek word from memory. The polytonic diacritics bar appears
    above the input — click a diacritic then type the vowel. Press **Enter** or
    click **Check** to see feedback.

    The **part-of-speech switcher** below picks which vocabulary you're writing —
    verbs, nouns (type the article too: *ὁ λόγος*), adjectives, or derived
    adverbs. Switching restarts the drill.

    - **Combining marks:** click more than one before typing to stack them — one
      accent (acute/grave/circumflex) + one breathing (smooth/rough) + iota
      subscript can all apply to the same vowel (e.g. rough breathing + circumflex
      + iota subscript → ᾧ). Clicking a second mark in the *same* group (e.g. a
      different accent) replaces the first instead of adding to it; diaeresis
      can't combine with breathing or iota subscript.
    - **Prefer a physical keyboard?** If your OS has a polytonic Greek layout
      installed (e.g. "Greek Polytonic" on Windows/macOS, `gr(polytonic)` on
      Linux), its dead keys work directly in this input as an alternative to the
      button bar.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    def make_pos_switcher():
        return mo.ui.radio(
            options=["verb", "noun", "adjective", "adverb"],
            value="verb",
            label="Part of speech",
            inline=True,
        )

    return (make_pos_switcher,)


@app.cell(hide_code=True)
def _(make_pos_switcher):
    pos_sel_w = make_pos_switcher()
    pos_sel_w
    return (pos_sel_w,)


@app.cell(hide_code=True)
def _(ADJS, ADVERBS, NOUNS, WORDS, mo, pos_sel_w):
    # Re-created whenever the part of speech changes — switching resets the drill.
    vocab_w = {"verb": WORDS, "noun": NOUNS, "adjective": ADJS, "adverb": ADVERBS}[pos_sel_w.value]
    cv_w, set_cv_w = mo.state(None)
    remaining_w, set_remaining_w = mo.state(None)
    score_w, set_score_w = mo.state({"correct": 0, "total": 0})
    history_w, set_history_w = mo.state([])
    future_w, set_future_w = mo.state([])
    restore_entry_w, set_restore_entry_w = mo.state(None)
    return (
        cv_w,
        future_w,
        history_w,
        remaining_w,
        restore_entry_w,
        score_w,
        set_cv_w,
        set_future_w,
        set_history_w,
        set_remaining_w,
        set_restore_entry_w,
        set_score_w,
        vocab_w,
    )


@app.cell(hide_code=True)
def _(cv_w, gu_ag, history_w, remaining_w, restore_entry_w):
    write_input_w, dia_w, check_btn_w, prev_btn_w, next_btn_w = gu_ag.word_drill_widgets(
        cv=cv_w(),
        remaining=remaining_w(),
        restore_entry=restore_entry_w(),
        history_len=len(history_w()),
        lang="en",
    )
    return check_btn_w, dia_w, next_btn_w, prev_btn_w, write_input_w


@app.cell(hide_code=True)
def _(
    check_btn_w,
    cv_w,
    dia_w,
    future_w,
    gu_ag,
    history_w,
    next_btn_w,
    prev_btn_w,
    remaining_w,
    restore_entry_w,
    score_w,
    set_cv_w,
    set_future_w,
    set_history_w,
    set_remaining_w,
    set_restore_entry_w,
    set_score_w,
    vocab_w,
    write_input_w,
):
    gu_ag.word_drill_form(
        cv_w, set_cv_w, remaining_w, set_remaining_w,
        score_w, set_score_w, restore_entry_w, set_restore_entry_w,
        history_w, set_history_w, future_w, set_future_w,
        write_input_w, dia_w, check_btn_w, prev_btn_w, next_btn_w,
        vocab=vocab_w,
        form_key="form",
        lang="en",
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Exercise 5 · Paradigm Drill — Verb / Noun / Adjective / Adverb

    One drill, switchable between parts of speech. The switcher picks the
    vocabulary and the matching form function — the three paradigm siblings
    `gu.verb_paradigm_drill_form` / `noun_...` / `adjective_...` share one cell
    structure (state, widgets, check button, display), so switching costs one
    `if/elif` per cell, not a separate exercise each.

    **Adverbs don't decline**, so that option switches the same cells to the
    single-answer drill instead (`gu.word_drill_widgets` / `word_drill_form`,
    as in Exercise 4) over `gu.adverb_vocab`'s derived forms (καλός → καλῶς).

    Paradigm-drill features, all inside the form function: Enter submits and
    advances focus past a correct field; the Check button turns orange on
    unsaved changes (`gu.dirty_check_button`, kept in its own cell — bundling
    it with the form would rebuild the form on every check); ↺ restarts;
    typed values are saved per word and restored when navigating back.
    Switching part of speech restarts the drill — the state cell
    re-initializes from the new vocabulary.
    """)
    return


@app.cell(hide_code=True)
def _(make_pos_switcher):
    pos_sel = make_pos_switcher()
    pos_sel
    return (pos_sel,)


@app.cell(hide_code=True)
def _(mo):
    # Kept in its own cell, undisplayed here: a cell that both builds this
    # widget and displays it conditionally on pos_sel would rerun (and reset
    # the toggle back to its default) on every part-of-speech switch, since
    # marimo reruns a cell whole when any of its own dependencies change.
    # The next cell displays it conditionally instead, without recreating it.
    article_toggle_ag = mo.ui.switch(label="Require article (noun)", value=True)
    return (article_toggle_ag,)


@app.cell(hide_code=True)
def _(article_toggle_ag, mo, pos_sel):
    article_toggle_ag if pos_sel.value == "noun" else mo.md("")
    return


@app.cell(hide_code=True)
def _(ADJS, NOUNS, WORDS, gu_ag, mo, pos_sel):
    # Re-created whenever the part of speech changes — switching resets the drill.
    _vv = {"verb": WORDS, "noun": NOUNS, "adjective": ADJS}.get(pos_sel.value, [])
    (w4t_p, set_w4t_p, hist_p, set_hist_p, msg_p, set_msg_p, cap_p, set_cap_p,
     entered_p, set_entered_p, sub_cnt_p, set_sub_cnt_p, prev_cnt_p, set_prev_cnt_p,
     nxt_cnt_p, set_nxt_cnt_p, entercnt_p, set_entercnt_p, restart_cnt_p,
     set_restart_cnt_p) = gu_ag.make_paradigm_drill_state(_vv)
    cvw_p, set_cvw_p = mo.state(None)
    remaining_p, set_remaining_p = mo.state(None)
    score_p, set_score_p = mo.state({"correct": 0, "total": 0})
    history_p, set_history_p = mo.state([])
    future_p, set_future_p = mo.state([])
    restore_entry_p, set_restore_entry_p = mo.state(None)
    return (
        cap_p,
        cvw_p,
        entercnt_p,
        entered_p,
        future_p,
        hist_p,
        history_p,
        msg_p,
        nxt_cnt_p,
        prev_cnt_p,
        remaining_p,
        restart_cnt_p,
        restore_entry_p,
        score_p,
        set_cap_p,
        set_cvw_p,
        set_entercnt_p,
        set_entered_p,
        set_future_p,
        set_hist_p,
        set_history_p,
        set_msg_p,
        set_nxt_cnt_p,
        set_prev_cnt_p,
        set_remaining_p,
        set_restart_cnt_p,
        set_restore_entry_p,
        set_score_p,
        set_sub_cnt_p,
        set_w4t_p,
        sub_cnt_p,
        w4t_p,
    )


@app.cell(hide_code=True)
def _(
    cvw_p,
    entered_p,
    gu_ag,
    hist_p,
    history_p,
    pos_sel,
    remaining_p,
    restore_entry_p,
    set_entercnt_p,
    set_nxt_cnt_p,
    set_prev_cnt_p,
    w4t_p,
):
    cur_p = noun_meta_p = drill_form_p = prev_btn_p = nxt_btn_p = restart_btn_p = None
    write_input_p = dia_p = wcheck_btn_p = wprev_btn_p = wnext_btn_p = None
    if pos_sel.value == "adverb":
        write_input_p, dia_p, wcheck_btn_p, wprev_btn_p, wnext_btn_p = gu_ag.word_drill_widgets(
            cv=cvw_p(),
            remaining=remaining_p(),
            restore_entry=restore_entry_p(),
            history_len=len(history_p()),
            placeholder="Greek adverb…",
            lang="en",
        )
    else:
        cur_p = w4t_p()[0] if w4t_p() else None
        if pos_sel.value == "verb":
            _labels = gu_ag.verb_slot_labels()
        elif pos_sel.value == "noun":
            noun_meta_p = gu_ag.noun_drill_meta(cur_p["form"]) if cur_p else None
            _labels = gu_ag.noun_slot_labels(getattr(noun_meta_p, "active_cases", []))
        else:
            _labels = gu_ag.adjective_slot_labels("simple")
        _entered_form_p = entered_p().get(cur_p["form"]) if cur_p else None
        drill_form_p, prev_btn_p, nxt_btn_p, restart_btn_p = gu_ag.paradigm_drill_widgets(
            labels=_labels,
            values=_entered_form_p,
            history_len=len(hist_p()),
            remaining_len=len(w4t_p()),
            lang="en",
        )
        set_prev_cnt_p(0)
        set_nxt_cnt_p(0)
        set_entercnt_p(0)
    return (
        cur_p,
        dia_p,
        drill_form_p,
        noun_meta_p,
        nxt_btn_p,
        prev_btn_p,
        restart_btn_p,
        wcheck_btn_p,
        wnext_btn_p,
        wprev_btn_p,
        write_input_p,
    )


@app.cell(hide_code=True)
def _(cap_p, cur_p, drill_form_p, gu_ag, pos_sel, set_sub_cnt_p):
    check_btn_p = (
        gu_ag.dirty_check_button(
            drill_form_p, cap_p, cur_p,
            {"verb": "verb_word", "noun": "test_word", "adjective": "adj_word"}[pos_sel.value],
            label="✓ Check",
        )
        if pos_sel.value != "adverb"
        else None
    )
    set_sub_cnt_p(0)
    return (check_btn_p,)


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd
    from pathlib import Path
    import eee_project as eee
    from eee_project import GreekUtils, ANCIENT_GREEK, greek_compare
    from modern_greek_backend_eee import ModernGreekBackend
    from ancient_greek_backend_eee import AncientGreekBackend

    _mg_backend = ModernGreekBackend()
    _ag_backend = AncientGreekBackend(lexicons=["pratt", "ltrg"])

    eee.register_backend("el", _mg_backend)
    eee.setup_ancient_greek(_ag_backend)

    gu_mg = GreekUtils(_mg_backend, mo, pd, eee_module=eee)
    gu_ag = GreekUtils(_ag_backend, mo, pd, eee_module=eee, config=ANCIENT_GREEK)

    # remote_base lets load_vocab_tsv fall back to fetching these from
    # Codeberg when the local file isn't found -- needed for the WASM
    # export, whose browser sandbox doesn't have this directory's siblings.
    # Must be the Gitea API raw endpoint, not the plain git-web raw URL --
    # codeberg.org/.../raw/branch/... sends no CORS headers, so a browser
    # fetch from inside the WASM sandbox is silently blocked; api/v1/repos/
    # .../raw/... serves identical bytes with access-control-allow-origin: *.
    NB_DIR = Path(__file__).parent
    _REMOTE_BASE = "https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/examples"
    WORDS = gu_ag.load_vocab_tsv("vocab.tsv", nb_dir=NB_DIR, remote_base=_REMOTE_BASE)
    NOUNS = gu_ag.load_vocab_tsv("nouns.tsv", nb_dir=NB_DIR, remote_base=_REMOTE_BASE)
    ADJS = gu_ag.load_vocab_tsv("adjectives.tsv", nb_dir=NB_DIR, remote_base=_REMOTE_BASE)
    _ADV_ADJS = gu_ag.load_vocab_tsv("adverb_adjectives.tsv", nb_dir=NB_DIR, remote_base=_REMOTE_BASE)
    ADVERBS = gu_ag.adverb_vocab(_ADV_ADJS)
    return ADJS, ADVERBS, NOUNS, WORDS, eee, greek_compare, gu_ag, gu_mg, mo


@app.cell(hide_code=True)
def _(
    ADJS,
    ADVERBS,
    NOUNS,
    WORDS,
    article_toggle_ag,
    cap_p,
    check_btn_p,
    cur_p,
    cvw_p,
    dia_p,
    drill_form_p,
    entercnt_p,
    entered_p,
    future_p,
    gu_ag,
    hist_p,
    history_p,
    msg_p,
    noun_meta_p,
    nxt_btn_p,
    nxt_cnt_p,
    pos_sel,
    prev_btn_p,
    prev_cnt_p,
    remaining_p,
    restart_btn_p,
    restart_cnt_p,
    restore_entry_p,
    score_p,
    set_cap_p,
    set_cvw_p,
    set_entercnt_p,
    set_entered_p,
    set_future_p,
    set_hist_p,
    set_history_p,
    set_msg_p,
    set_nxt_cnt_p,
    set_prev_cnt_p,
    set_remaining_p,
    set_restart_cnt_p,
    set_restore_entry_p,
    set_score_p,
    set_sub_cnt_p,
    set_w4t_p,
    sub_cnt_p,
    w4t_p,
    wcheck_btn_p,
    wnext_btn_p,
    wprev_btn_p,
    write_input_p,
):
    if pos_sel.value == "verb":
        _out = gu_ag.verb_paradigm_drill_form(
            w4t_p, set_w4t_p, hist_p, set_hist_p, msg_p, set_msg_p,
            cap_p, set_cap_p, entered_p, set_entered_p,
            sub_cnt_p, set_sub_cnt_p, prev_cnt_p, set_prev_cnt_p,
            nxt_cnt_p, set_nxt_cnt_p, entercnt_p, set_entercnt_p,
            restart_cnt_p, set_restart_cnt_p,
            cur_p, drill_form_p, check_btn_p, prev_btn_p, nxt_btn_p, restart_btn_p,
            vocab=WORDS,
            tense="present",
            done_message="Done — every verb drilled!",
        )
    elif pos_sel.value == "noun":
        _out = gu_ag.noun_paradigm_drill_form(
            w4t_p, set_w4t_p, hist_p, set_hist_p, msg_p, set_msg_p,
            cap_p, set_cap_p, entered_p, set_entered_p,
            sub_cnt_p, set_sub_cnt_p, prev_cnt_p, set_prev_cnt_p,
            nxt_cnt_p, set_nxt_cnt_p, entercnt_p, set_entercnt_p,
            restart_cnt_p, set_restart_cnt_p,
            cur_p, drill_form_p, check_btn_p, prev_btn_p, nxt_btn_p, restart_btn_p,
            vocab=NOUNS,
            noun_meta=noun_meta_p,
            article=article_toggle_ag.value,
            done_message="Done — every noun drilled!",
        )
    elif pos_sel.value == "adjective":
        _out = gu_ag.adjective_paradigm_drill_form(
            w4t_p, set_w4t_p, hist_p, set_hist_p, msg_p, set_msg_p,
            cap_p, set_cap_p, entered_p, set_entered_p,
            sub_cnt_p, set_sub_cnt_p, prev_cnt_p, set_prev_cnt_p,
            nxt_cnt_p, set_nxt_cnt_p, entercnt_p, set_entercnt_p,
            restart_cnt_p, set_restart_cnt_p,
            cur_p, drill_form_p, check_btn_p, prev_btn_p, nxt_btn_p, restart_btn_p,
            vocab=ADJS,
            mode="simple",
            done_message="Done — every adjective drilled!",
        )
    else:
        _out = gu_ag.word_drill_form(
            cvw_p, set_cvw_p, remaining_p, set_remaining_p,
            score_p, set_score_p, restore_entry_p, set_restore_entry_p,
            history_p, set_history_p, future_p, set_future_p,
            write_input_p, dia_p, wcheck_btn_p, wprev_btn_p, wnext_btn_p,
            vocab=ADVERBS,
            form_key="form",
            lang="en",
        )
    _out
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Exercise 6 · Modern Greek Paradigm Drill

    Same `paradigm_drill_widgets` / `*_paradigm_drill_form` mechanism as
    Exercise 5, but wired to `gu_mg` (`config=MODERN_GREEK`) instead of
    `gu_ag` -- the diacritics bar switches to the monotonic mark set (acute
    accent + diaeresis only), matching `GreekConfig.polytonic`. Switch part
    of speech below, same as Exercise 5 -- verb / noun / adjective only, no
    adverb here, since that path uses the separate `word_drill_widgets`
    mechanism, not `paradigm_drill_widgets`.

    For nouns specifically: `article` switches between a bare-noun answer and
    one requiring the definite article; `indefinite` additionally appends an
    indefinite-article slot for each singular case (indefinite articles
    don't inflect for plural) -- `config.indef_articles` is `None` for
    Ancient Greek, so this toggle only does something here.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    pos_sel_mg = mo.ui.radio(
        options=["verb", "noun", "adjective"],
        value="noun",
        label="Part of speech",
        inline=True,
    )
    pos_sel_mg
    return (pos_sel_mg,)


@app.cell(hide_code=True)
def _(mo):
    # Toggles kept in their own cell, undisplayed here -- same reason as
    # article_toggle_ag above: a cell depending on pos_sel_mg to decide
    # whether to display them would rerun (and reset them) on every
    # part-of-speech switch. The next cell displays them conditionally.
    MG_WORDS = [{"form": "γράφω", "meaning": "I write"}, {"form": "διαβάζω", "meaning": "I read"}]
    MG_NOUNS = [{"form": "το μήνυμα", "meaning": "message"}, {"form": "ο φίλος", "meaning": "friend"}]
    MG_ADJS = [{"form": "καλός", "meaning": "good"}, {"form": "μεγάλος", "meaning": "big"}]
    article_toggle_mg = mo.ui.switch(label="Require article (noun)", value=True)
    indefinite_toggle_mg = mo.ui.switch(label="Also test indefinite article (noun)", value=False)
    return MG_ADJS, MG_NOUNS, MG_WORDS, article_toggle_mg, indefinite_toggle_mg


@app.cell(hide_code=True)
def _(article_toggle_mg, indefinite_toggle_mg, mo, pos_sel_mg):
    mo.hstack([article_toggle_mg, indefinite_toggle_mg]) if pos_sel_mg.value == "noun" else mo.md("")
    return


@app.cell(hide_code=True)
def _(MG_ADJS, MG_NOUNS, MG_WORDS, gu_mg, pos_sel_mg):
    _vv = {"verb": MG_WORDS, "noun": MG_NOUNS, "adjective": MG_ADJS}.get(pos_sel_mg.value, [])
    (w4t_mg, set_w4t_mg, hist_mg, set_hist_mg, msg_mg, set_msg_mg, cap_mg, set_cap_mg,
     entered_mg, set_entered_mg, sub_cnt_mg, set_sub_cnt_mg, prev_cnt_mg, set_prev_cnt_mg,
     nxt_cnt_mg, set_nxt_cnt_mg, entercnt_mg, set_entercnt_mg, restart_cnt_mg,
     set_restart_cnt_mg) = gu_mg.make_paradigm_drill_state(_vv)
    return (
        cap_mg,
        entercnt_mg,
        entered_mg,
        hist_mg,
        msg_mg,
        nxt_cnt_mg,
        prev_cnt_mg,
        restart_cnt_mg,
        set_cap_mg,
        set_entercnt_mg,
        set_entered_mg,
        set_hist_mg,
        set_msg_mg,
        set_nxt_cnt_mg,
        set_prev_cnt_mg,
        set_restart_cnt_mg,
        set_sub_cnt_mg,
        set_w4t_mg,
        sub_cnt_mg,
        w4t_mg,
    )


@app.cell(hide_code=True)
def _(
    entered_mg,
    gu_mg,
    hist_mg,
    indefinite_toggle_mg,
    pos_sel_mg,
    set_entercnt_mg,
    set_nxt_cnt_mg,
    set_prev_cnt_mg,
    w4t_mg,
):
    cur_mg = w4t_mg()[0] if w4t_mg() else None
    noun_meta_mg = None
    if pos_sel_mg.value == "verb":
        _labels = gu_mg.verb_slot_labels()
    elif pos_sel_mg.value == "noun":
        noun_meta_mg = gu_mg.noun_drill_meta(cur_mg["form"]) if cur_mg else None
        _ac = getattr(noun_meta_mg, "active_cases", [])
        _labels = gu_mg.noun_slot_labels(_ac)
        if indefinite_toggle_mg.value:
            _labels = _labels + [f"Ind. {l}" for l in gu_mg.noun_slot_labels(gu_mg.noun_indef_cells(_ac))]
    else:
        _labels = gu_mg.adjective_slot_labels("simple")
    drill_form_mg, prev_btn_mg, nxt_btn_mg, restart_btn_mg = gu_mg.paradigm_drill_widgets(
        labels=_labels,
        values=entered_mg().get(cur_mg["form"]) if cur_mg else None,
        history_len=len(hist_mg()),
        remaining_len=len(w4t_mg()),
        lang="en",
    )
    set_prev_cnt_mg(0)
    set_nxt_cnt_mg(0)
    set_entercnt_mg(0)
    return (
        cur_mg,
        drill_form_mg,
        noun_meta_mg,
        nxt_btn_mg,
        prev_btn_mg,
        restart_btn_mg,
    )


@app.cell(hide_code=True)
def _(cap_mg, cur_mg, drill_form_mg, gu_mg, pos_sel_mg):
    check_btn_mg = gu_mg.dirty_check_button(
        drill_form_mg, cap_mg, cur_mg,
        {"verb": "verb_word", "noun": "test_word", "adjective": "adj_word"}[pos_sel_mg.value],
        label="Check",
    )
    return (check_btn_mg,)


@app.cell(hide_code=True)
def _(
    MG_ADJS,
    MG_NOUNS,
    MG_WORDS,
    article_toggle_mg,
    cap_mg,
    check_btn_mg,
    cur_mg,
    drill_form_mg,
    entercnt_mg,
    entered_mg,
    gu_mg,
    hist_mg,
    indefinite_toggle_mg,
    msg_mg,
    noun_meta_mg,
    nxt_btn_mg,
    nxt_cnt_mg,
    pos_sel_mg,
    prev_btn_mg,
    prev_cnt_mg,
    restart_btn_mg,
    restart_cnt_mg,
    set_cap_mg,
    set_entercnt_mg,
    set_entered_mg,
    set_hist_mg,
    set_msg_mg,
    set_nxt_cnt_mg,
    set_prev_cnt_mg,
    set_restart_cnt_mg,
    set_sub_cnt_mg,
    set_w4t_mg,
    sub_cnt_mg,
    w4t_mg,
):
    if pos_sel_mg.value == "verb":
        _out_mg = gu_mg.verb_paradigm_drill_form(
            w4t_mg, set_w4t_mg, hist_mg, set_hist_mg, msg_mg, set_msg_mg,
            cap_mg, set_cap_mg, entered_mg, set_entered_mg,
            sub_cnt_mg, set_sub_cnt_mg, prev_cnt_mg, set_prev_cnt_mg,
            nxt_cnt_mg, set_nxt_cnt_mg, entercnt_mg, set_entercnt_mg,
            restart_cnt_mg, set_restart_cnt_mg,
            cur_mg, drill_form_mg, check_btn_mg, prev_btn_mg, nxt_btn_mg, restart_btn_mg,
            vocab=MG_WORDS,
            tense="present",
            done_message="Done -- every verb drilled!",
        )
    elif pos_sel_mg.value == "noun":
        _out_mg = gu_mg.noun_paradigm_drill_form(
            w4t_mg, set_w4t_mg, hist_mg, set_hist_mg, msg_mg, set_msg_mg,
            cap_mg, set_cap_mg, entered_mg, set_entered_mg,
            sub_cnt_mg, set_sub_cnt_mg, prev_cnt_mg, set_prev_cnt_mg,
            nxt_cnt_mg, set_nxt_cnt_mg, entercnt_mg, set_entercnt_mg,
            restart_cnt_mg, set_restart_cnt_mg,
            cur_mg, drill_form_mg, check_btn_mg, prev_btn_mg, nxt_btn_mg, restart_btn_mg,
            vocab=MG_NOUNS,
            noun_meta=noun_meta_mg,
            article=article_toggle_mg.value,
            indefinite=indefinite_toggle_mg.value,
            done_message="Done -- both nouns drilled!",
        )
    else:
        _out_mg = gu_mg.adjective_paradigm_drill_form(
            w4t_mg, set_w4t_mg, hist_mg, set_hist_mg, msg_mg, set_msg_mg,
            cap_mg, set_cap_mg, entered_mg, set_entered_mg,
            sub_cnt_mg, set_sub_cnt_mg, prev_cnt_mg, set_prev_cnt_mg,
            nxt_cnt_mg, set_nxt_cnt_mg, entercnt_mg, set_entercnt_mg,
            restart_cnt_mg, set_restart_cnt_mg,
            cur_mg, drill_form_mg, check_btn_mg, prev_btn_mg, nxt_btn_mg, restart_btn_mg,
            vocab=MG_ADJS,
            mode="simple",
            done_message="Done -- both adjectives drilled!",
        )
    _out_mg
    return


if __name__ == "__main__":
    app.run()

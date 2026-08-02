# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.23.13",
#     "eee-project>=1.0.1",
#     "modern-greek-backend-eee>=1.0.0",
#     "pandas==3.0.5",
# ]
# ///
"""Modern Greek paradigm drill — verb / noun / adjective, with personal vocab upload.

Run standalone (fetches packages from PyPI):
    uv run marimo run examples/modern_greek_drill_notebook.py

Run from within the repo (uses local packages):
    uv run marimo edit examples/modern_greek_drill_notebook.py
"""

import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _():
    import marimo as mo
    import pandas as pd
    import eee_project as eee
    from eee_project import GreekUtils
    from modern_greek_backend_eee import ModernGreekBackend

    mg_backend = ModernGreekBackend()
    eee.register_backend("el", mg_backend)
    gu = GreekUtils(mg_backend, mo, pd, eee_module=eee)
    t_ui = gu.ui_label
    return gu, mo, pd, t_ui


@app.cell(hide_code=True)
def _(mo):
    # Kept in its own cell, undisplayed here: a cell that both builds this
    # widget and displays it conditionally elsewhere would rerun (and reset
    # the selection back to its default) on every dependent re-render.
    language_selector = mo.ui.dropdown(
        options={"English": "en", "Русский": "ru", "Ελληνικά": "el"},
        value="English",
        label="🌐",
    )
    return (language_selector,)


@app.cell(hide_code=True)
def _(language_selector, mo):
    mo.Html(f"""
    <div style="position: fixed; top: 60px; right: 10px; z-index: 1000; background: white; padding: 8px 12px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
        {language_selector}
    </div>
    """)
    return


@app.cell(hide_code=True)
def _(language_selector, mo, t_ui):
    _lang = language_selector.value
    mo.md(f"""
    # {t_ui("drill_title", _lang)}

    {t_ui("drill_description", _lang)}
    """)
    return


@app.cell(hide_code=True)
def _(language_selector, mo, t_ui):
    pos_selector = mo.ui.radio(
        options=["verb", "noun", "adjective"],
        value="noun",
        label=t_ui("pos_label", language_selector.value),
        inline=True,
    )
    pos_selector
    return (pos_selector,)


@app.cell(hide_code=True)
def _(language_selector, mo, t_ui):
    file_upload = mo.ui.file(label=t_ui("load_tsv_label", language_selector.value))
    file_upload
    return (file_upload,)


@app.cell(hide_code=True)
def _(language_selector, mo, t_ui, vocab_df, w4t):
    _lang = language_selector.value
    _remaining_forms = {w["form"] for w in w4t()}
    vocab_table_df = vocab_df[vocab_df["Word"].isin(_remaining_forms)].reset_index(drop=True)
    vocab_table_df = vocab_table_df.rename(columns={
        "Word": t_ui("word_label", _lang),
        "Translation": t_ui("translation_label", _lang).removesuffix(":"),
    })
    vocab_table = mo.ui.table(vocab_table_df, selection=None)
    vocab_table
    return


@app.cell(hide_code=True)
def _():
    DEFAULT_VOCAB = {
        "verb": [
            {"form": "γράφω", "meaning": "I write"},
            {"form": "διαβάζω", "meaning": "I read"},
            {"form": "μιλάω", "meaning": "I speak"},
        ],
        "noun": [
            {"form": "το μήνυμα", "meaning": "message"},
            {"form": "ο φίλος", "meaning": "friend"},
            {"form": "η γυναίκα", "meaning": "woman"},
        ],
        "adjective": [
            {"form": "καλός", "meaning": "good"},
            {"form": "μεγάλος", "meaning": "big"},
            {"form": "όμορφος", "meaning": "beautiful"},
        ],
    }
    return (DEFAULT_VOCAB,)


@app.cell(hide_code=True)
def _(DEFAULT_VOCAB, file_upload, gu, pd, pos_selector):
    # An uploaded TSV always has Word/Translation columns regardless of the
    # currently-selected part of speech — the same uploaded list is reused
    # across all 3 POS tabs, matching modern-greek-eee's old behavior.
    uploaded_df = gu.load_data(file_upload, None)
    if uploaded_df is not None and not uploaded_df.empty:
        vocab = [
            {"form": str(row["Word"]).strip(), "meaning": str(row["Translation"]).strip()}
            for _, row in uploaded_df.iterrows()
            if str(row.get("Word", "")).strip()
        ]
    else:
        vocab = DEFAULT_VOCAB[pos_selector.value]
    vocab_df = pd.DataFrame([{"Word": w["form"], "Translation": w["meaning"]} for w in vocab])
    return vocab, vocab_df


@app.cell(hide_code=True)
def _(gu, vocab):
    # Re-created whenever the part of speech (or vocab) changes — switching resets the drill.
    (w4t, set_w4t, hist, set_hist, msg, set_msg, cap, set_cap,
     entered, set_entered, sub_cnt, set_sub_cnt, prev_cnt, set_prev_cnt,
     nxt_cnt, set_nxt_cnt, entercnt, set_entercnt, restart_cnt,
     set_restart_cnt) = gu.make_paradigm_drill_state(vocab)
    return (
        cap,
        entercnt,
        entered,
        hist,
        msg,
        nxt_cnt,
        prev_cnt,
        restart_cnt,
        set_cap,
        set_entercnt,
        set_entered,
        set_hist,
        set_msg,
        set_nxt_cnt,
        set_prev_cnt,
        set_restart_cnt,
        set_sub_cnt,
        set_w4t,
        sub_cnt,
        w4t,
    )


@app.cell(hide_code=True)
def _(gu, language_selector, mo, t_ui):
    # Widgets kept in their own cell, undisplayed here: a cell that both
    # builds a widget and displays it conditionally on pos_selector would
    # rerun (and reset the widget to its default) on every part-of-speech
    # switch, since marimo reruns a cell whole when any dependency changes.
    # The next cell displays each conditionally instead, without recreating it.
    _lang = language_selector.value
    tense_options = gu.tense_dropdown_options(_lang)
    default_tense_label = next(
        (k for k, v in tense_options.items() if v == "present"),
        next(iter(tense_options)),
    )
    tense_selector = mo.ui.dropdown(options=tense_options, value=default_tense_label, label=t_ui("tense_label", _lang))
    article_toggle = mo.ui.switch(label=t_ui("require_article_label", _lang), value=True)
    indefinite_toggle = mo.ui.switch(label=t_ui("indefinite_label", _lang), value=False)
    full_mode_toggle = mo.ui.switch(label=t_ui("full_paradigm_label", _lang), value=False)
    return article_toggle, full_mode_toggle, indefinite_toggle, tense_selector


@app.cell(hide_code=True)
def _(
    article_toggle,
    full_mode_toggle,
    indefinite_toggle,
    mo,
    pos_selector,
    tense_selector,
):
    if pos_selector.value == "verb":
        _controls = tense_selector
    elif pos_selector.value == "noun":
        _controls = mo.hstack([article_toggle, indefinite_toggle], gap="1.5rem")
    else:
        _controls = full_mode_toggle
    _controls
    return


@app.cell(hide_code=True)
def _(
    entered,
    full_mode_toggle,
    gu,
    hist,
    language_selector,
    pos_selector,
    set_entercnt,
    set_nxt_cnt,
    set_prev_cnt,
    w4t,
):
    cur = w4t()[0] if w4t() else None
    noun_meta = None
    adj_mode = "full" if full_mode_toggle.value else "simple"
    if pos_selector.value == "verb":
        labels = gu.verb_slot_labels()
    elif pos_selector.value == "noun":
        noun_meta = gu.noun_drill_meta(cur["form"]) if cur else None
        labels = gu.noun_slot_labels(getattr(noun_meta, "active_cases", []))
    else:
        labels = gu.adjective_slot_labels(adj_mode)
    drill_form, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
        labels=labels,
        values=entered().get(cur["form"]) if cur else None,
        history_len=len(hist()),
        remaining_len=len(w4t()),
        lang=language_selector.value,
    )
    set_prev_cnt(0)
    set_nxt_cnt(0)
    set_entercnt(0)
    return adj_mode, cur, drill_form, noun_meta, nxt_btn, prev_btn, restart_btn


@app.cell(hide_code=True)
def _(cap, cur, drill_form, gu, language_selector, pos_selector, t_ui):
    check_btn = gu.dirty_check_button(
        drill_form, cap, cur,
        {"verb": "verb_word", "noun": "test_word", "adjective": "adj_word"}[pos_selector.value],
        label=t_ui("check_label", language_selector.value),
    )
    return (check_btn,)


@app.cell(hide_code=True)
def _(
    adj_mode,
    article_toggle,
    cap,
    check_btn,
    cur,
    drill_form,
    entercnt,
    entered,
    gu,
    hist,
    indefinite_toggle,
    language_selector,
    msg,
    noun_meta,
    nxt_btn,
    nxt_cnt,
    pos_selector,
    prev_btn,
    prev_cnt,
    restart_btn,
    restart_cnt,
    set_cap,
    set_entercnt,
    set_entered,
    set_hist,
    set_msg,
    set_nxt_cnt,
    set_prev_cnt,
    set_restart_cnt,
    set_sub_cnt,
    set_w4t,
    sub_cnt,
    t_ui,
    tense_selector,
    vocab,
    w4t,
):
    _lang = language_selector.value
    # translation_label already carries a trailing colon (e.g. "Translation:")
    # for use as standalone text elsewhere; meaning_label's own "{label}: "
    # formatting expects a colon-less string, so strip it here once.
    _meaning_label = t_ui("translation_label", _lang).removesuffix(":")
    if pos_selector.value == "verb":
        out = gu.verb_paradigm_drill_form(
            w4t, set_w4t, hist, set_hist, msg, set_msg,
            cap, set_cap, entered, set_entered,
            sub_cnt, set_sub_cnt, prev_cnt, set_prev_cnt,
            nxt_cnt, set_nxt_cnt, entercnt, set_entercnt,
            restart_cnt, set_restart_cnt,
            cur, drill_form, check_btn, prev_btn, nxt_btn, restart_btn,
            vocab=vocab,
            tense=tense_selector.value,
            meaning_label=_meaning_label,
            done_message=t_ui("verb_done", _lang),
        )
    elif pos_selector.value == "noun":
        out = gu.noun_paradigm_drill_form(
            w4t, set_w4t, hist, set_hist, msg, set_msg,
            cap, set_cap, entered, set_entered,
            sub_cnt, set_sub_cnt, prev_cnt, set_prev_cnt,
            nxt_cnt, set_nxt_cnt, entercnt, set_entercnt,
            restart_cnt, set_restart_cnt,
            cur, drill_form, check_btn, prev_btn, nxt_btn, restart_btn,
            vocab=vocab,
            noun_meta=noun_meta,
            article=article_toggle.value,
            indefinite=indefinite_toggle.value,
            meaning_label=_meaning_label,
            done_message=t_ui("noun_done", _lang),
        )
    else:
        out = gu.adjective_paradigm_drill_form(
            w4t, set_w4t, hist, set_hist, msg, set_msg,
            cap, set_cap, entered, set_entered,
            sub_cnt, set_sub_cnt, prev_cnt, set_prev_cnt,
            nxt_cnt, set_nxt_cnt, entercnt, set_entercnt,
            restart_cnt, set_restart_cnt,
            cur, drill_form, check_btn, prev_btn, nxt_btn, restart_btn,
            vocab=vocab,
            mode=adj_mode,
            meaning_label=_meaning_label,
            done_message=t_ui("adj_done", _lang),
        )
    out
    return


if __name__ == "__main__":
    app.run()

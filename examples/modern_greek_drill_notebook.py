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

__generated_with = "0.23.16"
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

    # Anywidget bridge for cross-page language persistence (localStorage).
    # Kept in its own cell, undisplayed here: a cell that both builds this
    # and displays/uses it elsewhere would rerun (and reset the bridge) on
    # every dependent re-render.
    bridge = eee.language_bridge(mo)
    return bridge, eee, gu, mo, pd, t_ui


@app.cell(hide_code=True)
def _(bridge, eee, mo):
    # Kept undisplayed here, in its own cell (not folded into the bridge
    # cell above): must take *bridge* as a parameter, not just reference it
    # via closure, so marimo reruns this cell -- rebuilding the dropdown
    # with the real persisted language -- once the browser's (async)
    # localStorage read completes.
    language_selector = eee.language_selector(mo, bridge)
    return (language_selector,)


@app.cell(hide_code=True)
def _(bridge, eee, language_selector, mo):
    eee.save_language_selection(bridge, language_selector)
    mo.Html(f"""
    <div style="position: fixed; top: 60px; right: 10px; z-index: 1000; background: white; padding: 8px 12px; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15);">
        {language_selector}
    </div>
    {bridge}
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
    file_upload = mo.ui.file(label=t_ui("load_tsv_label", language_selector.value))
    file_upload
    return (file_upload,)


@app.cell(hide_code=True)
def _(language_selector, mo, t_ui):
    _lang = language_selector.value
    pos_selector = mo.ui.radio(
        options={
            t_ui("verb_test_topic", _lang): "verb",
            t_ui("noun_test_topic", _lang): "noun",
            t_ui("adj_test_topic", _lang): "adjective",
        },
        value=t_ui("noun_test_topic", _lang),
        label=t_ui("pos_label", _lang),
        inline=True,
    )
    pos_selector
    return (pos_selector,)


@app.cell(hide_code=True)
def _(file_upload, gu, mo, pd, pos_selector):
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

    tbl_sel, set_tbl_sel = mo.state(None)

    # An uploaded TSV always has Word/Translation columns regardless of the
    # currently-selected part of speech — the same uploaded list is reused
    # across all 3 POS tabs, matching modern-greek-eee's old behavior.
    uploaded_df = gu.load_data(file_upload, None)
    if uploaded_df is not None and not uploaded_df.empty:
        _rows = [
            {"Word": str(row["Word"]).strip(), "Translation": str(row["Translation"]).strip()}
            for _, row in uploaded_df.iterrows()
            if str(row.get("Word", "")).strip()
        ]
    else:
        _rows = [{"Word": w["form"], "Translation": w["meaning"]} for w in DEFAULT_VOCAB[pos_selector.value]]
    vocab_df = pd.DataFrame(_rows)
    return tbl_sel, vocab_df


@app.cell(hide_code=True)
def _(mo):
    confirmed_vocab, set_confirmed_vocab = mo.state([])
    return confirmed_vocab, set_confirmed_vocab


@app.cell(hide_code=True)
def _(gu, language_selector, mo, t_ui):
    # Kept in their own cell, undisplayed here: a cell that both builds a
    # widget and displays/uses it conditionally elsewhere would rerun (and
    # reset the widget to its default) on every dependent re-render -- these
    # 4 widgets must depend on *only* language_selector, not on vocab_table
    # or anything downstream of it, otherwise every checkbox click in the
    # vocab table (or every POS switch) would silently discard whatever the
    # user had picked here. Confirmed via a live regression test after an
    # earlier merge folded these into the same cell as vocab_table-derived
    # state, which silently broke it (indefinite_toggle reset to False on
    # any table-selection change).
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
def _(mo, tbl_sel, vocab_df):
    # Column headers are always "Word"/"Translation" (not translated) -- this
    # table's own cell must not depend on language_selector. Making it do so
    # once caused a confirmed live regression: since this table's *value*
    # is the source vocab is derived from, and the drill state resets
    # whenever vocab's upstream cell reruns, a plain language switch would
    # silently wipe drill progress (hist/w4t) with no word-content change
    # at all.
    _selected_words = tbl_sel() or set()
    _sel_indices = [i for i, w in enumerate(vocab_df["Word"]) if w in _selected_words]
    if not _sel_indices:
        # No selection yet, or a stale selection from a different part-of-
        # speech/upload with no matching words: default to "all selected".
        _sel_indices = list(range(len(vocab_df)))
    vocab_table = mo.ui.table(vocab_df, selection="multi", initial_selection=_sel_indices)
    vocab_table
    return (vocab_table,)


@app.cell(hide_code=True)
def _(confirmed_vocab, set_confirmed_vocab, vocab_table):
    # Only commits a new vocab list when its *content* actually changed --
    # vocab_table rebuilds as a new object on every language switch (pos_selector
    # and file_upload both have translated labels, so they rebuild too, and jCtf
    # depends on both), but that's a cosmetic rebuild, not a real selection
    # change. Without this guard, crmA would re-derive vocab from the rebuilt
    # vocab_table and call gu.make_paradigm_drill_state() again on every language
    # switch, silently wiping hist/w4t/etc with no word-content change at all --
    # confirmed via a live regression test (hist wiped by a plain language
    # switch, no completion involved).
    if vocab_table.value is not None and not vocab_table.value.empty:
        _cols = list(vocab_table.value.columns)
        _new_vocab = [
            {"form": str(r[_cols[0]]).strip(), "meaning": str(r[_cols[1]]).strip()}
            for _, r in vocab_table.value.iterrows()
        ]
    else:
        _new_vocab = []

    if _new_vocab != confirmed_vocab():
        set_confirmed_vocab(_new_vocab)
    return


@app.cell(hide_code=True)
def _(confirmed_vocab, gu):
    vocab = confirmed_vocab()
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
        vocab,
        w4t,
    )


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
    indefinite_toggle,
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
    _lang = language_selector.value
    if pos_selector.value == "verb":
        labels = gu.verb_slot_labels()
    elif pos_selector.value == "noun":
        noun_meta = gu.noun_drill_meta(cur["form"]) if cur else None
        active_cases = getattr(noun_meta, "active_cases", [])
        labels = gu.noun_slot_labels(active_cases, lang=_lang)
        if indefinite_toggle.value:
            labels = labels + [f"Ind. {l}" for l in gu.noun_slot_labels(gu.noun_indef_cells(active_cases), lang=_lang)]
    else:
        labels = gu.adjective_slot_labels(adj_mode, lang=_lang)
    drill_form, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
        labels=labels,
        values=entered().get(cur["form"]) if cur else None,
        history_len=len(hist()),
        remaining_len=len(w4t()),
        lang=_lang,
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

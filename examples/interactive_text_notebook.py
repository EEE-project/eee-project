# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.25.1",
#     "eee-project>=1.26.0",
# ]
# ///
"""interactive_text and mixed_language_notes demo — a poem with clickable words and highlight sets,
then the same poem beside a translation with comments tied to its words.

Shows `interactive_text` with `word_classes={css_class: forms}` (any number of highlight
sets) and `css=` (the rules that style them), plus the click-reactive panel pattern; then
`wrap=True`, `translation=` and `notes=` with `GreekUtils.render_gloss_sheet`, set up as an Odyssey
lesson sets them up (a stanza dropdown, a translation dropdown with a blank entry, an interface
language): a stanza that fits a phone, its translation as one card, and margin notes shown in the
word panel; then the two translation exercises on the same stanzas (`stanza_match_form` and
`translation_presence_form`) with a choice of translators (`translator_multiselect`);
then `mixed_language_notes`: one card per comment, choosing a card
highlights the words it is about.

Run locally:
    uv run marimo edit examples/interactive_text_notebook.py --no-token
"""

import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # `interactive_text` — clickable words and highlight sets

    `interactive_text` draws poem lines in which chosen words are clickable.
    `word_classes={css_class: forms}` puts any number of **named highlight sets** on those words
    (a word in several sets gets every class), and `css=` carries the rules that style them — a
    `<style>` emitted by another cell cannot reach the widget, because marimo mounts it in a shadow root.

    ```python
    text_widget = eee.interactive_text(
        mo, lines=LINES, clickable=CLICKABLE,
        word_classes={"verb": VERBS, "noun": NOUNS},
        css=".eee-itext .gk-word.verb{background:#e3f0e3;color:#1d1d1b}",
    )
    # a panel cell takes the *widget* and reads text_widget.widget.selected_word
    ```

    Odyssey I.1–2 (Murray 1919). The sets here are parts of speech plus one computed set; in a lesson
    they usually come from `grc_coverage_words(...)` (see `docs/api-patterns.md`).
    """)
    return


@app.cell
def _(mo):
    use_css = mo.ui.switch(value=True, label="pass `css=` (colour the sets)")
    use_css
    return (use_css,)


@app.cell
def _(CSS, LINES, SETS, TOKENS, eee, mo, use_css):
    text_widget = eee.interactive_text(
        mo,
        lines=LINES,
        clickable=set(TOKENS),
        word_classes=SETS,
        css=CSS if use_css.value else None,
    )
    text_widget
    return (text_widget,)


@app.cell
def _(eee, mo, text_widget):
    _word = text_widget.widget.selected_word
    _in = [name for name, forms in text_widget.widget.word_classes.items() if eee.norm_grc_surface(_word) in forms]
    mo.md(f"**{_word}** — in: {', '.join(f'`{s}`' for s in _in) or 'no set'}" if _word else "_Click a word._")
    return


@app.cell(hide_code=True)
def _(SAMPLE, STYLES, mo):
    _rows = "\n".join(
        f'| `{name}` | `{decl}` | <span style="{decl}">{SAMPLE[name]}</span> |' for name, decl in STYLES.items()
    )
    mo.md(
        "| set | `css=` declaration | looks like |\n|:--|:--|:--|\n" + _rows + "\n\n"
        "`long` is computed (7 letters or more), so it overlaps the others — the classes compose. "
        "Switch `css=` off and the classes are still on the spans; the widget itself only styles "
        "`.homer`, the dotted underline and the clicked word (`.active`, always painted last)."
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # `wrap`, `translation` and `notes` — a stanza that fits a phone

    This section is a lesson in miniature: a stanza dropdown (two stanzas of Odyssey I), a translation dropdown, an
    interface language, the poem with its translation, and the word panel.

    By default each line of the poem stays on one row, so on a screen 390 px wide the poem is wider than the
    screen and pushes a translation out of sight. `wrap=True` lets every line wrap, with a hanging indent so that
    a wrapped row is not taken for the next line. `translation=` draws the translation of the stanza in the same
    widget, as one card for the whole stanza (a translator's lines need not match the Greek lines one to one: the
    second stanza has 3 Greek lines and a 2-line translation): beside the poem when the widget is 600 px wide or
    more, under it when narrower, so narrow the browser window to see it move. `notes=` are the translator's margin
    notes: the text marks a word that has one with a star, the card does not draw the star, and the word is a link
    (underlined, in a link's colour) whose tap shows the note where a tap on a Greek word shows its forms. The blank entry of the translation dropdown passes
    `translation=None`, and the three dropdowns sit in a row that wraps on a narrow screen.

    ```python
    stanza = {s["ref"]: s for s in STANZAS}[stanza_choice.value]
    tr = trans_choice.value        # None: the blank entry
    stanza_widget = eee.interactive_text(
        mo, lines=stanza["lines"], clickable=CLICKABLE, wrap=True,
        translation=None if tr is None else stanza["translations"][tr].split("\n"),   # ["Tell me, Muse, of the man* of many turns*, ...", ...]
        notes=stanza.get("margin_glosses", {}).get(tr, {}),   # {0: [("man", "ἀνήρ — ..."), ("turns", "τρόποι — ...")]}: the k-th star of line i = the k-th note of line i
    )
    mo.vstack([mo.hstack([stanza_choice, trans_choice, lang_choice], justify="start", wrap=True, gap=1.5), stanza_widget])
    # the word panel, in two cells:
    #   period_tables, period_selector, gloss_panel = gu.render_gloss_selector(WORDS[lang], stanza_widget.widget.selected_word, build_period_tables, lang=lang)
    #   gu.render_gloss_sheet(gloss_panel, period_tables, period_selector, lang=lang, selected_word=..., click_seq=..., note=stanza_widget.widget.selected_note)
    ```

    `render_gloss_sheet` shows the panel and its table as one sheet: a block under the text on a wide page, a sheet
    fixed to the bottom of the screen on a narrow one once you tap a word, with a close button. Tap an underlined
    word: `ἔπερσεν` and `ἴδεν` have two periods, so a dropdown, the others have one; or tap a linked word of the
    translation. The 🌐 dropdown sets the interface language of the sheet (`lang=`); the meanings come per language,
    as the vocabulary files of a lesson do.
    """)
    return


@app.cell
def _(LESSON_STANZAS, eee, mo):
    stanza_choice = mo.ui.dropdown(options=[s["ref"] for s in LESSON_STANZAS], value=LESSON_STANZAS[0]["ref"], label="stanza")
    trans_choice = mo.ui.dropdown(
        options=list(LESSON_STANZAS[0]["translations"]),
        value="with margin notes",
        allow_select_none=True,  # the blank entry: value None, no translation
        label="translation",
    )
    lang_choice = eee.language_selector(mo, None)  # en, ru or el; a lesson passes its persisted language bridge here
    return lang_choice, stanza_choice, trans_choice


@app.cell
def _(GLOSSED_FORMS, LESSON_STANZAS, eee, lang_choice, mo, stanza_choice, trans_choice):
    _stanza = {s["ref"]: s for s in LESSON_STANZAS}[stanza_choice.value]
    _tr = trans_choice.value
    stanza_widget = eee.interactive_text(
        mo,
        lines=_stanza["lines"],
        clickable=GLOSSED_FORMS,
        wrap=True,
        translation=None if _tr is None else _stanza["translations"][_tr].split("\n"),
        notes=_stanza.get("margin_glosses", {}).get(_tr, {}),
    )
    mo.vstack([
        mo.hstack([stanza_choice, trans_choice, lang_choice], justify="start", wrap=True, gap=1.5),
        stanza_widget,
    ])
    return (stanza_widget,)


@app.cell
def _(GLOSS_WORDS, build_period_tables, gu, lang_choice, stanza_widget):
    # builds the panel and its period dropdown; shows nothing (the next cell shows the sheet)
    period_tables, period_selector, gloss_panel = gu.render_gloss_selector(
        GLOSS_WORDS[lang_choice.value], stanza_widget.widget.selected_word, build_period_tables, lang=lang_choice.value,
    )
    return gloss_panel, period_selector, period_tables


@app.cell
def _(gloss_panel, gu, lang_choice, period_selector, period_tables, stanza_widget):
    # takes period_selector as a parameter, so a pick in the dropdown reruns only this cell
    gu.render_gloss_sheet(
        gloss_panel, period_tables, period_selector, lang=lang_choice.value,
        selected_word=stanza_widget.widget.selected_word,
        click_seq=stanza_widget.widget.click_seq,
        note=stanza_widget.widget.selected_note,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # The two translation exercises — a choice of translators

    `stanza_match_form` (match a stanza with its translation, or the reverse) and `translation_presence_form` (is a word of
    the stanza reflected in a passage of a translation) take the stanzas of the lesson. An exercise quotes a translator's text
    without the stars of the margin notes: the notes (`margin_glosses`, the data `notes=` takes above) belong to the text widget
    of the section above and are not shown in the exercises.

    ```python
    translators = gu.translator_multiselect(["literal", "with margin notes"], lang)   # all chosen at the start; .value = the keys
    gu.stanza_match_form(..., stanzas=STANZAS, direction=direction.value, lang=lang,
                         valid_translators=translators.value, translator_choice=True)   # fewer than 2 translators: a warning
    gu.translation_presence_form(..., items=items, lang=lang, valid_translators=translators.value)   # no translator: a warning
    ```

    Choose one translator, or none, and a message takes the place of the exercise. The 🌐 dropdown of the section above sets the language.
    """)
    return


@app.cell
def _(LESSON_STANZAS, gu, lang_choice, mo):
    ex_translators = gu.translator_multiselect(list(LESSON_STANZAS[0]["translations"]), lang_choice.value)
    _grc_to_tr = gu.ui_label("stanza_match_toggle_grc_to_tr", lang_choice.value)
    ex_direction = mo.ui.radio(
        options={_grc_to_tr: "grc_to_tr", gu.ui_label("stanza_match_toggle_tr_to_grc", lang_choice.value): "tr_to_grc"},
        value=_grc_to_tr,
        label=gu.ui_label("stanza_match_direction_label", lang_choice.value),
        inline=True,
    )
    mo.hstack([ex_translators, ex_direction], justify="start", wrap=True, gap=1.5)
    return ex_direction, ex_translators


@app.cell
def _(mo):
    sm_cv, sm_set_cv = mo.state(None)
    sm_score, sm_set_score = mo.state({"correct": 0, "total": 0})
    sm_remaining, sm_set_remaining = mo.state(None)
    sm_history, sm_set_history = mo.state([])
    sm_future, sm_set_future = mo.state([])
    sm_restore_entry, sm_set_restore_entry = mo.state(None)
    return (
        sm_cv,
        sm_future,
        sm_history,
        sm_remaining,
        sm_restore_entry,
        sm_score,
        sm_set_cv,
        sm_set_future,
        sm_set_history,
        sm_set_remaining,
        sm_set_restore_entry,
        sm_set_score,
    )


@app.cell
def _(ex_direction, ex_translators, sm_set_cv, sm_set_remaining):
    _ = ex_direction.value, ex_translators.value  # a new choice starts a new session
    sm_set_cv(None)
    sm_set_remaining(None)
    return


@app.cell
def _(LESSON_STANZAS, ex_direction, ex_translators, gu, lang_choice, sm_cv, sm_history, sm_remaining, sm_restore_entry):
    _ = sm_cv()
    sm_choice_radio, sm_next_btn, sm_prev_btn = gu.stanza_match_widgets(
        cv=sm_cv(),
        remaining=sm_remaining(),
        stanzas=LESSON_STANZAS,
        direction=ex_direction.value,
        restore_entry=sm_restore_entry(),
        history_len=len(sm_history()),
        lang=lang_choice.value,
        valid_translators=ex_translators.value,
    )
    return sm_choice_radio, sm_next_btn, sm_prev_btn


@app.cell
def _(
    LESSON_STANZAS,
    ex_direction,
    ex_translators,
    gu,
    lang_choice,
    sm_choice_radio,
    sm_cv,
    sm_future,
    sm_history,
    sm_next_btn,
    sm_prev_btn,
    sm_remaining,
    sm_restore_entry,
    sm_score,
    sm_set_cv,
    sm_set_future,
    sm_set_history,
    sm_set_remaining,
    sm_set_restore_entry,
    sm_set_score,
):
    gu.stanza_match_form(
        sm_cv, sm_set_cv, sm_remaining, sm_set_remaining,
        sm_score, sm_set_score, sm_restore_entry, sm_set_restore_entry,
        sm_history, sm_set_history, sm_future, sm_set_future,
        sm_choice_radio, sm_next_btn, sm_prev_btn,
        stanzas=LESSON_STANZAS,
        direction=ex_direction.value,
        lang=lang_choice.value,
        valid_translators=ex_translators.value,
        translator_choice=True,
    )
    return


@app.cell
def _(mo):
    tp_cv, tp_set_cv = mo.state(None)
    tp_score, tp_set_score = mo.state({"correct": 0, "total": 0})
    tp_remaining, tp_set_remaining = mo.state(None)
    tp_history, tp_set_history = mo.state([])
    tp_future, tp_set_future = mo.state([])
    tp_restore_entry, tp_set_restore_entry = mo.state(None)
    return (
        tp_cv,
        tp_future,
        tp_history,
        tp_remaining,
        tp_restore_entry,
        tp_score,
        tp_set_cv,
        tp_set_future,
        tp_set_history,
        tp_set_remaining,
        tp_set_restore_entry,
        tp_set_score,
    )


@app.cell
def _(GLOSS_WORDS, LESSON_STANZAS, PRESENCE_ROWS, ex_translators, gu, tp_set_cv, tp_set_remaining):
    tp_items = gu.build_translation_presence_items(
        PRESENCE_ROWS, GLOSS_WORDS["en"], LESSON_STANZAS, valid_translators=ex_translators.value,
    )
    tp_set_cv(None)  # a new choice starts a new session
    tp_set_remaining(None)
    return (tp_items,)


@app.cell
def _(gu, lang_choice, tp_cv, tp_history, tp_items, tp_remaining, tp_restore_entry):
    _ = tp_cv()
    tp_choice_radio, tp_next_btn, tp_prev_btn, tp_source_switch = gu.translation_presence_widgets(
        cv=tp_cv(),
        remaining=tp_remaining(),
        items=tp_items,
        restore_entry=tp_restore_entry(),
        history_len=len(tp_history()),
        lang=lang_choice.value,
    )
    return tp_choice_radio, tp_next_btn, tp_prev_btn, tp_source_switch


@app.cell
def _(
    ex_translators,
    gu,
    lang_choice,
    tp_choice_radio,
    tp_cv,
    tp_future,
    tp_history,
    tp_items,
    tp_next_btn,
    tp_prev_btn,
    tp_remaining,
    tp_restore_entry,
    tp_score,
    tp_set_cv,
    tp_set_future,
    tp_set_history,
    tp_set_remaining,
    tp_set_restore_entry,
    tp_set_score,
    tp_source_switch,
):
    gu.translation_presence_form(
        tp_cv, tp_set_cv, tp_remaining, tp_set_remaining,
        tp_score, tp_set_score, tp_restore_entry, tp_set_restore_entry,
        tp_history, tp_set_history, tp_future, tp_set_future,
        tp_choice_radio, tp_next_btn, tp_prev_btn, tp_source_switch,
        items=tp_items,
        lang=lang_choice.value,
        valid_translators=ex_translators.value,
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # `mixed_language_notes` — comments tied to words of the poem

    `mixed_language_notes` shows the poem next to one translation and, under them, a card per comment.
    Each comment names the poem's own words it is about (`fragments`, several separated by ` | `) and
    carries its text per UI language. Choose a card and its words are highlighted in the Greek text;
    every card stays visible. It is plain HTML/CSS — no widget, no round trip — so the highlight is
    instant and the choice survives switching the translation or the language (try it).

    ```python
    NOTES = gu.load_language_notes(nb_dir=notebook_dir)  # language_notes.tsv: fragments, ru, el, en
    eee.mixed_language_notes(
        mo, stanzas=STANZAS, translator=translator.value, notes=NOTES, lang=ui_lang.value,
    )
    ```

    `STANZAS` is the list a lesson already holds: `[{"lines": [...], "translations": {translator: "line\nline"}}]`.
    The notes and the two renderings below are the demo's own. The heading and the hint are the generic
    `language_notes_*` rows of `ui-{lang}.tsv`; pass `heading=` and `hint=` for a lesson's own wording, and a
    different `block_id=` to each block when a page holds more than one. `eee.language_notes_problems(lines, notes)`
    lists the fragments that would show as nothing (a typo, an overlap); the setup cell asserts there are none.
    """)
    return


@app.cell
def _(STANZAS, eee, mo):
    translator = mo.ui.dropdown(options=list(STANZAS[0]["translations"]), value="literal", label="translation")
    ui_lang = eee.language_selector(mo, None)
    return translator, ui_lang


@app.cell
def _(NOTES, STANZAS, eee, mo, translator, ui_lang):
    mo.vstack([
        mo.hstack([translator, ui_lang], justify="start"),
        eee.mixed_language_notes(mo, stanzas=STANZAS, translator=translator.value, notes=NOTES, lang=ui_lang.value),
    ])
    return


@app.cell
def _():
    import marimo as mo
    import eee_project as eee

    norm = eee.norm_grc_surface
    LINES = [
        "Ἄνδρα μοι ἔννεπε, μοῦσα, πολύτροπον, ὃς μάλα πολλὰ",
        "πλάγχθη, ἐπεὶ Τροίης ἱερὸν πτολίεθρον ἔπερσεν·",
    ]
    TOKENS = [norm(w) for line in LINES for w in line.split()]
    SETS = {
        "verb": {norm(w) for w in ("ἔννεπε", "πλάγχθη", "ἔπερσεν")},
        "noun": {norm(w) for w in ("Ἄνδρα", "μοῦσα", "Τροίης", "πτολίεθρον")},
        "adjective": {norm(w) for w in ("πολύτροπον", "ἱερὸν")},
    }
    SETS["long"] = {t for t in TOKENS if len(t) >= 7}
    assert all(forms <= set(TOKENS) for forms in SETS.values()), "set forms must be normalized and occur in the text"

    STYLES = {
        "verb": "background:#e3f0e3;color:#1d1d1b",
        "noun": "background:#fff3c4;color:#1d1d1b",
        "adjective": "background:#fce4ec;color:#1d1d1b",
        "long": "border-bottom:2px solid #c0392b",
    }
    SAMPLE = {"verb": "ἔννεπε", "noun": "Τροίης", "adjective": "ἱερὸν", "long": "πτολίεθρον"}
    CSS = "\n".join(f".eee-itext .gk-word.{name}{{{decl}}}" for name, decl in STYLES.items())

    STANZAS = [
        {
            "ref": "1.1-2",
            "lines": LINES,
            "translations": {
                "literal": "Tell me, Muse, of the man of many turns, who very much\nwandered, after he sacked the holy citadel of Troy;",
                "freer": "Sing to me, Muse, of the resourceful man who roamed far and wide\nonce he had destroyed the sacred city of Troy.",
            },
        }
    ]
    gu = eee.GreekUtils(mo_module=mo)

    # A lesson's stanzas: Greek lines, each translator's text ("\n" between lines), margin notes {line: [(word, meaning), ...]} (k-th star = k-th note).
    LESSON_STANZAS = [
        {
            "ref": "1.1-2",
            "lines": LINES,
            "translations": {
                "literal": "Tell me, Muse, of the man of many turns, who very much\nwandered, after he sacked the holy citadel of Troy;",
                "with margin notes": "Tell me, Muse, of the man* of many turns*, who very much\nwandered*, after he sacked the holy citadel of Troy;",
            },
            "margin_glosses": {
                "with margin notes": {
                    0: [("man", "ἀνήρ — the poem's first noun; Odysseus is not named in these lines"),
                        ("turns", "τρόποι — ways; also the turns of a mind")],
                    1: [("wandered", "πλάγχθη — was driven off course (πλάζω)")],
                },
            },
        },
        {
            "ref": "1.3-5",
            "lines": [
                "πολλῶν δ᾽ ἀνθρώπων ἴδεν ἄστεα καὶ νόον ἔγνω,",
                "πολλὰ δ᾽ ὅ γ᾽ ἐν πόντῳ πάθεν ἄλγεα ὃν κατὰ θυμόν,",
                "ἀρνύμενος ἣν τε ψυχὴν καὶ νόστον ἑταίρων.",
            ],
            "translations": {
                "literal": "He saw the cities of many men and came to know their minds,\n"
                           "and many pains he suffered at sea in his own heart,\n"
                           "striving for his own life and the homecoming of his comrades.",
                "with margin notes": "He saw the cities* of many men and learned their minds, and at sea he\n"
                                     "suffered many pains*, striving for his own life and his comrades' homecoming*.",
            },
            "margin_glosses": {
                "with margin notes": {
                    0: [("cities", "ἄστεα — towns (the plural of ἄστυ)")],
                    1: [("pains", "ἄλγεα — pains, griefs (cf. «analgesic»)"),
                        ("homecoming", "νόστον — the return home (cf. «nostalgia»)")],
                },
            },
        },
    ]

    # A lesson's vocabulary per interface language, and build_period_tables(word) -> [(period, html table), ...]: two periods make a dropdown.
    GLOSS_WORDS = {
        "en": [
            {"form": "ἔπερσεν", "lemma": "πέρθω", "context": "verb", "meaning": "sacked, destroyed", "grammar_label": "aorist, 3rd person singular"},
            {"form": "πλάγχθη", "lemma": "πλάζω", "context": "verb", "meaning": "was driven off course", "grammar_label": "aorist passive, 3rd person singular"},
            {"form": "ἴδεν", "lemma": "ὁράω", "context": "verb", "meaning": "saw", "grammar_label": "aorist, 3rd person singular"},
            {"form": "ἔγνω", "lemma": "γιγνώσκω", "context": "verb", "meaning": "came to know, learned", "grammar_label": "aorist, 3rd person singular"},
            {"form": "πάθεν", "lemma": "πάσχω", "context": "verb", "meaning": "suffered", "grammar_label": "aorist, 3rd person singular"},
            {"form": "νόστον", "lemma": "νόστος", "context": "noun", "meaning": "homecoming, return", "grammar_label": "accusative singular"},
        ],
        "ru": [
            {"form": "ἔπερσεν", "lemma": "πέρθω", "context": "глагол", "meaning": "разрушил, взял (город)", "grammar_label": "аорист, 3 л. ед. ч."},
            {"form": "πλάγχθη", "lemma": "πλάζω", "context": "глагол", "meaning": "был унесён с пути, скитался", "grammar_label": "аорист страдательного залога, 3 л. ед. ч."},
            {"form": "ἴδεν", "lemma": "ὁράω", "context": "глагол", "meaning": "увидел", "grammar_label": "аорист, 3 л. ед. ч."},
            {"form": "ἔγνω", "lemma": "γιγνώσκω", "context": "глагол", "meaning": "узнал, познал", "grammar_label": "аорист, 3 л. ед. ч."},
            {"form": "πάθεν", "lemma": "πάσχω", "context": "глагол", "meaning": "испытал, претерпел", "grammar_label": "аорист, 3 л. ед. ч."},
            {"form": "νόστον", "lemma": "νόστος", "context": "существительное", "meaning": "возвращение домой", "grammar_label": "винительный падеж, ед. ч."},
        ],
        "el": [
            {"form": "ἔπερσεν", "lemma": "πέρθω", "context": "ρήμα", "meaning": "κατέστρεψε, κατέκτησε", "grammar_label": "αόριστος, 3ο ενικό πρόσωπο"},
            {"form": "πλάγχθη", "lemma": "πλάζω", "context": "ρήμα", "meaning": "περιπλανήθηκε", "grammar_label": "παθητικός αόριστος, 3ο ενικό πρόσωπο"},
            {"form": "ἴδεν", "lemma": "ὁράω", "context": "ρήμα", "meaning": "είδε", "grammar_label": "αόριστος, 3ο ενικό πρόσωπο"},
            {"form": "ἔγνω", "lemma": "γιγνώσκω", "context": "ρήμα", "meaning": "έμαθε, γνώρισε", "grammar_label": "αόριστος, 3ο ενικό πρόσωπο"},
            {"form": "πάθεν", "lemma": "πάσχω", "context": "ρήμα", "meaning": "έπαθε, υπέφερε", "grammar_label": "αόριστος, 3ο ενικό πρόσωπο"},
            {"form": "νόστον", "lemma": "νόστος", "context": "ουσιαστικό", "meaning": "επιστροφή στην πατρίδα", "grammar_label": "αιτιατική ενικού"},
        ],
    }
    # The answer key of "is the word reflected in the translation": one row per word, stanza it occurs in and translator (a lesson keeps it in translation_presence.tsv).
    PRESENCE_ROWS = [
        {"lemma": "πέρθω", "form": "ἔπερσεν", "stanza_ref": "1.1-2", "translator": "literal", "reflected": "yes"},
        {"lemma": "πλάζω", "form": "πλάγχθη", "stanza_ref": "1.1-2", "translator": "with margin notes", "reflected": "yes"},
        {"lemma": "γιγνώσκω", "form": "ἔγνω", "stanza_ref": "1.3-5", "translator": "literal", "reflected": "yes"},
        {"lemma": "ὁράω", "form": "ἴδεν", "stanza_ref": "1.3-5", "translator": "with margin notes", "reflected": "yes"},
    ]
    GLOSSED_FORMS = {norm(w["form"]) for w in GLOSS_WORDS["en"]}  # what a lesson passes as `clickable`: the words it can gloss
    assert all(GLOSSED_FORMS == {norm(w["form"]) for w in words} for words in GLOSS_WORDS.values()), "every language glosses the same words"
    _TABLES = {
        "πέρθω": [
            ("homer", "<table><tr><th></th><th>aorist</th></tr><tr><td>3 sg.</td><td><b>ἔπερσεν</b></td></tr></table>"),
            ("lsj", "<table><tr><th></th><th>aorist</th></tr><tr><td>3 sg.</td><td><b>ἔπερσε(ν)</b></td></tr></table>"),
        ],
        "πλάζω": [
            ("homer", "<table><tr><th></th><th>aorist passive</th></tr><tr><td>3 sg.</td><td><b>πλάγχθη</b></td></tr></table>"),
        ],
        "ὁράω": [
            ("homer", "<table><tr><th></th><th>aorist</th></tr><tr><td>3 sg.</td><td><b>ἴδεν</b></td></tr></table>"),
            ("lsj", "<table><tr><th></th><th>aorist</th></tr><tr><td>3 sg.</td><td><b>εἶδεν</b></td></tr></table>"),
        ],
        "γιγνώσκω": [
            ("homer", "<table><tr><th></th><th>aorist</th></tr><tr><td>3 sg.</td><td><b>ἔγνω</b></td></tr></table>"),
        ],
        "πάσχω": [
            ("homer", "<table><tr><th></th><th>aorist</th></tr><tr><td>3 sg.</td><td><b>πάθεν</b></td></tr></table>"),
        ],
        "νόστος": [
            ("homer", "<table><tr><th></th><th>singular</th></tr><tr><td>acc.</td><td><b>νόστον</b></td></tr></table>"),
        ],
    }

    def build_period_tables(word):
        return _TABLES.get(word["lemma"])

    NOTES = [
        {
            "fragments": "ἔννεπε μοῦσα",
            "en": "The invocation: the poet asks the Muse to tell the story.",
            "ru": "Призыв: поэт просит Музу рассказать эту историю.",
            "el": "Η επίκληση: ο ποιητής ζητά από τη Μούσα να διηγηθεί την ιστορία.",
        },
        {
            "fragments": "πολύτροπον",
            "en": "Odysseus' first epithet, literally «of many turns»: it can mean resourceful or much-travelled, and the story needs both.",
            "ru": "Первый эпитет Одиссея. Слово может значить и «изобретательный», и «много странствовавший»: для этой истории нужны оба смысла.",
            "el": "Το πρώτο επίθετο του Οδυσσέα: μπορεί να σημαίνει «πολυμήχανος» ή «πολυταξιδεμένος»· η ιστορία χρειάζεται και τα δύο.",
        },
        {
            "fragments": "πλάγχθη | ἔπερσεν",
            "en": "The two aorists that carry the first sentence: «was driven off course» (passive of πλάζω) and «sacked» (πέρθω).",
            "ru": "Два аориста, на которых держится первая фраза: «был унесён в скитания» (страдательный залог от πλάζω) и «разрушил» (πέρθω).",
            "el": "Οι δύο αόριστοι που στηρίζουν την πρώτη φράση: «περιπλανήθηκε» (παθητική φωνή του πλάζω) και «κατέστρεψε» (πέρθω).",
        },
    ]
    assert not eee.language_notes_problems(LINES, NOTES), "every fragment must occur in the text and none may overlap another"
    return CSS, GLOSSED_FORMS, GLOSS_WORDS, LESSON_STANZAS, LINES, NOTES, PRESENCE_ROWS, SAMPLE, SETS, STANZAS, STYLES, TOKENS, build_period_tables, eee, gu, mo


if __name__ == "__main__":
    app.run()

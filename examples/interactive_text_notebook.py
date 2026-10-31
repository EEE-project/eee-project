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
`wrap=True`, `translation=` and `notes=` with `GreekUtils.render_gloss_sheet`: a stanza that fits a
phone, its translation as one card, and margin notes shown in the word panel; then
`mixed_language_notes`: one card per comment, choosing a card highlights the words it is about.

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
        css=".eee-itext .gk-word.verb{background:#e3f0e3}",
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

    By default each line of the poem stays on one row, so on a screen 390 px wide the poem is wider than the
    screen and pushes a translation out of sight. `wrap=True` lets every line wrap, with a hanging indent so that
    a wrapped row is not taken for the next line. `translation=` draws the translation of the stanza in the same
    widget, as one card for the whole stanza (a translator's lines need not match the Greek lines one to one):
    beside the poem when the widget is 600 px wide or more, under it when narrower, so narrow the browser window
    to see it move. `notes=` are the translator's margin notes: a star in a translation line points to one, the word
    before the star is clickable, and a tap shows the note where a tap on a Greek word shows its forms. The blank
    entry of the dropdown below passes `translation=None`.

    ```python
    stanza_widget = eee.interactive_text(
        mo, lines=LINES, clickable=CLICKABLE, wrap=True,
        translation=lines_or_None,   # ["Tell me, Muse, of the man* of many turns*, ...", ...]
        notes={0: [("man", "ἀνήρ — ..."), ("turns", "τρόποι — ...")]},   # the k-th star of line i = the k-th note of line i
    )
    # the word panel, in two cells:
    #   period_tables, period_selector, gloss_panel = gu.render_gloss_selector(WORDS, stanza_widget.widget.selected_word, build_period_tables)
    #   gu.render_gloss_sheet(gloss_panel, period_tables, period_selector, selected_word=..., click_seq=..., note=stanza_widget.widget.selected_note)
    ```

    `render_gloss_sheet` shows the panel and its table as one sheet: a block under the text on a wide page, a sheet
    fixed to the bottom of the screen on a narrow one once you tap a word, with a close button. Tap `ἔπερσεν` (two
    periods, so a dropdown) or `πλάγχθη` (one), or a starred word of the translation.
    """)
    return


@app.cell
def _(mo):
    trans_choice = mo.ui.dropdown(
        options={"literal": "literal", "with margin notes": "with margin notes"},
        value="with margin notes",
        allow_select_none=True,  # the blank entry: value None, no translation
        label="translation",
    )
    return (trans_choice,)


@app.cell
def _(LINES, NOTE_TRANSLATIONS, TOKENS, eee, mo, trans_choice):
    _choice = trans_choice.value
    stanza_widget = eee.interactive_text(
        mo,
        lines=LINES,
        clickable=set(TOKENS),
        wrap=True,
        translation=None if _choice is None else NOTE_TRANSLATIONS[_choice]["lines"],
        notes=None if _choice is None else NOTE_TRANSLATIONS[_choice]["notes"],
    )
    mo.vstack([trans_choice, stanza_widget])
    return (stanza_widget,)


@app.cell
def _(GLOSS_WORDS, build_period_tables, gu, stanza_widget):
    # builds the panel and its period dropdown; shows nothing (the next cell shows the sheet)
    period_tables, period_selector, gloss_panel = gu.render_gloss_selector(
        GLOSS_WORDS, stanza_widget.widget.selected_word, build_period_tables, lang="en",
    )
    return gloss_panel, period_selector, period_tables


@app.cell
def _(gloss_panel, gu, period_selector, period_tables, stanza_widget):
    # takes period_selector as a parameter, so a pick in the dropdown reruns only this cell
    gu.render_gloss_sheet(
        gloss_panel, period_tables, period_selector, lang="en",
        selected_word=stanza_widget.widget.selected_word,
        click_seq=stanza_widget.widget.click_seq,
        note=stanza_widget.widget.selected_note,
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
        "verb": "background:#e3f0e3",
        "noun": "background:#fff3c4",
        "adjective": "background:#fce4ec",
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

    # The same two lines with margin notes (the demo's own glosses): the k-th star of a line is the k-th note of it.
    NOTE_TRANSLATIONS = {
        "literal": {"lines": STANZAS[0]["translations"]["literal"].split("\n"), "notes": {}},
        "with margin notes": {
            "lines": [
                "Tell me, Muse, of the man* of many turns*, who very much",
                "wandered*, after he sacked the holy citadel of Troy;",
            ],
            "notes": {
                0: [("man", "ἀνήρ — the poem's first noun; Odysseus is not named in these lines"),
                    ("turns", "τρόποι — ways; also the turns of a mind")],
                1: [("wandered", "πλάγχθη — was driven off course (πλάζω)")],
            },
        },
    }

    # What a lesson takes from its vocabulary and its lexicons, in miniature: a word list for the gloss panel, and
    # build_period_tables(word) -> [(period, html table), ...]. Two periods make a dropdown, one period does not.
    GLOSS_WORDS = [
        {"form": "ἔπερσεν", "lemma": "πέρθω", "context": "verb", "meaning": "sacked, destroyed", "grammar_label": "aorist, 3rd person singular"},
        {"form": "πλάγχθη", "lemma": "πλάζω", "context": "verb", "meaning": "was driven off course", "grammar_label": "aorist passive, 3rd person singular"},
    ]
    _TABLES = {
        "πέρθω": [
            ("homer", "<table><tr><th></th><th>aorist</th></tr><tr><td>3 sg.</td><td><b>ἔπερσεν</b></td></tr></table>"),
            ("lsj", "<table><tr><th></th><th>aorist</th></tr><tr><td>3 sg.</td><td><b>ἔπερσε(ν)</b></td></tr></table>"),
        ],
        "πλάζω": [
            ("homer", "<table><tr><th></th><th>aorist passive</th></tr><tr><td>3 sg.</td><td><b>πλάγχθη</b></td></tr></table>"),
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
    return CSS, GLOSS_WORDS, LINES, NOTES, NOTE_TRANSLATIONS, SAMPLE, SETS, STANZAS, STYLES, TOKENS, build_period_tables, eee, gu, mo


if __name__ == "__main__":
    app.run()

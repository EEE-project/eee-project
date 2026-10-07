# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.25.1",
#     "eee-project>=1.22.0",
# ]
# ///
"""interactive_text and mixed_language_notes demo — a poem with clickable words and highlight sets,
then the same poem beside a translation with comments tied to its words.

Shows `interactive_text` with `word_classes={css_class: forms}` (any number of highlight
sets) and `css=` (the rules that style them), plus the click-reactive panel pattern; then
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
    return CSS, LINES, NOTES, SAMPLE, SETS, STANZAS, STYLES, TOKENS, eee, mo


if __name__ == "__main__":
    app.run()

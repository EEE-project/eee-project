# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo>=0.25.1",
#     "eee-project>=1.21.0",
# ]
# ///
"""interactive_text demo — clickable poem words, named highlight sets, and their styling.

Shows `interactive_text` with `word_classes={css_class: forms}` (any number of highlight
sets) and `css=` (the rules that style them), plus the click-reactive panel pattern.

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
    return CSS, LINES, SAMPLE, SETS, STYLES, TOKENS, eee, mo


if __name__ == "__main__":
    app.run()

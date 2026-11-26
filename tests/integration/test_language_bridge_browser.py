"""A real-browser check of the language bridge: how often does a page run its cells while it loads?

`language_bridge` reads the language kept in the browser (localStorage, key `eee_lang`) and tells the kernel. A value change
that comes from the browser makes marimo run again every cell that reads the language, so a page whose stored language is
the one it already shows ran all its cells a second time, and a choice made in the first seconds (a translator, say) was
reset. The page of this test counts the runs of a cell that reads the language. It comes in the two shapes of the lessons
of `created_with_eee`: the Odyssey lessons show the bridge in the cell that saves the language (so a new language draws the
bridge again), the other courses show it in its own cell. A third shape lets `language_picker` save the language and show
the dropdown and the bridge.

Run:
    uv run pytest tests/integration/test_language_bridge_browser.py -m integration -v

Needs `playwright` and a Chromium, as the other tests of this folder (see conftest.py).
"""
import contextlib
import re
import time

import pytest

pytestmark = pytest.mark.integration

sync_api = pytest.importorskip("playwright.sync_api")

NOTEBOOK = '''import marimo

app = marimo.App()


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    from eee_project import language_bridge
    bridge = language_bridge(mo)
    BRIDGE_SHOWN
    return (bridge,)


@app.cell
def _(bridge, mo):
    from eee_project import language_selector
    lang_sel = language_selector(mo, bridge)
    SELECTOR_SHOWN
    return (lang_sel,)


@app.cell
def _(bridge, lang_sel, mo):
    from eee_project import language_picker, save_language_selection
    SAVE_CALL
    SAVE_SHOWS
    return


@app.cell
def _():
    runs = []
    return (runs,)


@app.cell
def _(lang_sel, mo, runs):
    runs.append(lang_sel.value)
    mo.md(f"RUNS={len(runs)} LANG={lang_sel.value}")
    return


if __name__ == "__main__":
    app.run()
'''
SHAPES = {
    # the Odyssey lessons: the cell that saves the language also shows the dropdown and the bridge
    "bridge_in_the_save_cell": {"BRIDGE_SHOWN": "None", "SELECTOR_SHOWN": "None",
                                "SAVE_CALL": "save_language_selection(bridge, lang_sel)",
                                "SAVE_SHOWS": 'mo.Html(f"<div class=\'eee-lang-picker\'>{lang_sel}{bridge}</div>")'},
    # the other courses: the bridge and the dropdown are shown by the cells that make them
    "bridge_in_its_own_cell": {"BRIDGE_SHOWN": "bridge", "SELECTOR_SHOWN": "lang_sel",
                               "SAVE_CALL": "save_language_selection(bridge, lang_sel)", "SAVE_SHOWS": "None"},
    # language_picker: one call saves the language and returns the row with the dropdown and the bridge
    "the_picker_helper": {"BRIDGE_SHOWN": "None", "SELECTOR_SHOWN": "None", "SAVE_CALL": "None",
                          "SAVE_SHOWS": "language_picker(mo, lang_sel, bridge)"},
}
COUNT = re.compile(r"RUNS=(\d+) LANG=(\w+)")


@pytest.fixture(scope="module", params=list(SHAPES))
def base_url(request, serve_demo, tmp_path_factory):
    text = NOTEBOOK
    for slot, code in SHAPES[request.param].items():
        text = text.replace(slot, code)
    path = tmp_path_factory.mktemp(request.param) / "bridge_notebook.py"
    path.write_text(text, encoding="utf-8")
    return serve_demo(path)


def _settled(page, quiet=3.0, limit=40.0):
    """(runs, language) once the counter has not changed for `quiet` seconds."""
    page.wait_for_selector("text=/RUNS=\\d+/", timeout=60000)
    last, since, end = None, time.monotonic(), time.monotonic() + limit
    while time.monotonic() < end:
        now = COUNT.search(page.inner_text("body"))
        now = (int(now[1]), now[2]) if now else None
        if now != last:
            last, since = now, time.monotonic()
        elif time.monotonic() - since >= quiet:
            return last
        page.wait_for_timeout(250)
    return last


@contextlib.contextmanager
def _visit(browser, base_url, stored=None):
    ctx = browser.new_context()
    try:
        if stored:
            ctx.add_init_script(f"try {{ localStorage.setItem('eee_lang', '{stored}'); }} catch (e) {{}}")
        page = ctx.new_page()
        page.goto(base_url, wait_until="load")
        yield page
    finally:
        ctx.close()


def test_a_first_visit_runs_the_cells_that_read_the_language_once(browser, base_url):
    with _visit(browser, base_url) as page:
        assert _settled(page) == (1, "en")


def test_a_stored_language_equal_to_the_one_on_show_runs_them_once(browser, base_url):
    with _visit(browser, base_url, stored="en") as page:
        assert _settled(page) == (1, "en")
        assert page.evaluate("localStorage.getItem('eee_lang')") == "en"


def test_another_stored_language_is_shown_and_not_overwritten(browser, base_url):
    # the one case that needs the second run: the page starts in its default and switches to the stored language
    with _visit(browser, base_url, stored="ru") as page:
        assert _settled(page) == (2, "ru")
        assert page.evaluate("localStorage.getItem('eee_lang')") == "ru"


def test_after_a_first_visit_a_new_choice_is_stored_and_runs_the_cells_once(browser, base_url):
    # the kernel must know that the browser read is done (stored is not None), or the choice is not kept for the next page
    with _visit(browser, base_url) as page:
        assert _settled(page) == (1, "en")
        page.locator("select").first.select_option(label="Русский")
        assert _settled(page) == (2, "ru")
        assert page.evaluate("localStorage.getItem('eee_lang')") == "ru"


def test_a_chosen_language_is_kept_on_the_next_visit(browser, base_url):
    # a new tab is a new session with the same browser storage
    with _visit(browser, base_url) as page:
        assert _settled(page) == (1, "en")
        page.locator("select").first.select_option(label="Русский")
        assert _settled(page) == (2, "ru")
        again = page.context.new_page()
        again.goto(base_url, wait_until="load")
        assert _settled(again) == (2, "ru")

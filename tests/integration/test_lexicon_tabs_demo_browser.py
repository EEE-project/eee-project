"""A real-browser check of the period tabs (`build_grc_lexicon_tabs`) in the Ancient Greek demo.

pytest cannot see how the cells of a notebook react to each other, nor what the browser keeps of the tab picker when
the tables are drawn again. This runs the demo (`examples/ancient_greek_notebook.py`) with `marimo run` and opens it
in Chromium.

Run:
    uv run pytest tests/integration/test_lexicon_tabs_demo_browser.py -m integration -v

Needs the same Playwright and Chromium as `test_paradigm_form_browser.py`.
"""
import contextlib
from pathlib import Path

import pytest

from eee_project.content import _ui_label

from .test_interactive_text_browser import _chosen, _contrast, _dropdown_with, _page_background, _paint, _require_theme

pytestmark = pytest.mark.integration

sync_api = pytest.importorskip("playwright.sync_api")

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "ancient_greek_notebook.py"
FOUR_PERIODS, EPIC_ONLY = "μένει (μένω)", "ἔην (εἰμί)"


@pytest.fixture(scope="module")
def base_url(serve_demo):
    return serve_demo(EXAMPLE)


@pytest.fixture(scope="module")
def dark_url(serve_demo):
    return serve_demo(EXAMPLE, "dark")


@contextlib.contextmanager
def _page(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1100, "height": 900})
    page = ctx.new_page()
    try:
        page.goto(base_url, wait_until="load")
        sync_api.expect(_dropdown_with(page, FOUR_PERIODS)).to_be_visible(timeout=90000)
        yield page
    finally:
        ctx.close()


def _choose(page, option):
    _dropdown_with(page, option).select_option(label=option)


def _period(name, lang):
    return _ui_label(f"grc_period_{name}", lang)


def _expect_visible(locator):
    sync_api.expect(locator).to_be_visible(timeout=60000)  # the first word reads the lexicons


def _faint(page, elements):
    """The elements, by name, whose text is under the 4.5:1 contrast that small text needs on the page."""
    background = _page_background(page)
    ratios = {name: _contrast(_paint(element)["color"], background) for name, element in elements.items()}
    return {name: round(ratio, 2) for name, ratio in ratios.items() if ratio < 4.5}


def test_a_new_language_renames_the_tabs_and_keeps_the_word(browser, base_url):
    with _page(browser, base_url) as page:
        _choose(page, FOUR_PERIODS)
        summary = page.locator("details[class^='ddw-'] > summary")
        _expect_visible(summary.get_by_text(_period("homer", "en")))
        _choose(page, "Русский")
        _expect_visible(summary.get_by_text(_period("homer", "ru")))
        _expect_visible(page.locator("[id^='lp-'][id$='-homer'] th", has_text="Наст.").first)  # the table, too
        assert _chosen(_dropdown_with(page, FOUR_PERIODS)) == FOUR_PERIODS


def test_a_one_period_word_shows_after_the_last_tab_of_another(browser, base_url):
    with _page(browser, base_url) as page:
        _choose(page, FOUR_PERIODS)
        summary = page.locator("details[class^='ddw-'] > summary")
        _expect_visible(summary)
        summary.click()
        page.locator("details[class^='ddw-'] label", has_text=_period("morphgnt", "en")).click()
        _expect_visible(page.locator("[id^='lp-'][id$='-morphgnt'] table"))
        sync_api.expect(page.locator("[id^='lp-'][id$='-homer']")).to_be_hidden()
        _choose(page, EPIC_ONLY)
        sync_api.expect(summary).to_have_count(0, timeout=60000)  # one period: a header, no picker
        _expect_visible(page.get_by_text(_period("homer", "en"), exact=True))
        _expect_visible(page.locator("td", has_text="ἔην").first)


def test_the_period_name_of_a_one_period_word_can_be_read_in_the_dark_theme(browser, dark_url):
    with _page(browser, dark_url) as page:
        _require_theme(page, dark=True)
        _choose(page, EPIC_ONLY)
        name = page.get_by_text(_period("homer", "en"), exact=True)
        _expect_visible(name)
        assert not _faint(page, {"period name": name})


@pytest.mark.parametrize("theme", ["light", "dark"])
def test_the_grey_labels_of_the_period_tables_can_be_read(browser, request, theme):
    with _page(browser, request.getfixturevalue("dark_url" if theme == "dark" else "base_url")) as page:
        _require_theme(page, dark=theme == "dark")
        _choose(page, FOUR_PERIODS)
        table = page.locator("[id^='lp-'][id$='-homer']")
        _expect_visible(table.locator("table"))
        faint = _faint(page, {"column header": table.locator("th").nth(1), "row label": table.locator("td").first,
                              "description under the picker": page.locator("[id^='ld-'][id$='-homer']")})
        _choose(page, EPIC_ONLY)
        sync_api.expect(page.locator("details[class^='ddw-'] > summary")).to_have_count(0, timeout=60000)
        description = page.get_by_text(_ui_label("grc_lex_descr_homer", "en"), exact=True)
        _expect_visible(description)
        faint |= _faint(page, {"description of one period": description})
        assert not faint

"""A real-browser check of the drill demo: what starts a new round, and what a change of the language keeps.

pytest cannot see how the cells of a notebook react to each other. This runs the demo
(`examples/modern_greek_drill_notebook.py`) with `marimo run` and opens it in Chromium.

Run:
    uv run pytest tests/integration/test_drill_demo_browser.py -m integration -v

Needs the same Playwright and Chromium as `test_paradigm_form_browser.py`.
"""
import ast
import contextlib
import re
from pathlib import Path

import pytest

from .test_interactive_text_browser import _dropdown_with

pytestmark = pytest.mark.integration

sync_api = pytest.importorskip("playwright.sync_api")

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "modern_greek_drill_notebook.py"
FIELD = "input.eee-para-inp"


@pytest.fixture(scope="module")
def base_url(serve_demo):
    return serve_demo(EXAMPLE)


@pytest.fixture
def upload(tmp_path):
    """A word list of 2 adjectives of the demo, with translations that the demo does not have."""
    tree = ast.parse(EXAMPLE.read_text(encoding="utf-8"))
    vocab = next(
        ast.literal_eval(node.value) for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and ast.unparse(node.targets[0]) == "DEFAULT_VOCAB"
    )
    first, second = (word["form"] for word in vocab["adjective"][:2])
    path = tmp_path / "words.tsv"
    path.write_text(f"Word\tTranslation\n{first}\tuploaded one\n{second}\tuploaded two\n", encoding="utf-8")
    return path


@contextlib.contextmanager
def _page(browser, base_url):
    ctx = browser.new_context(viewport={"width": 1100, "height": 900})
    page = ctx.new_page()
    try:
        page.goto(base_url, wait_until="load")
        page.wait_for_selector(FIELD, timeout=90000)
        page.wait_for_timeout(1500)
        yield page
    finally:
        ctx.close()


def _choose(page, start):
    """Choose the option whose label starts with *start* (a tense label ends with its Greek name)."""
    menu = _dropdown_with(page, start)
    menu.select_option(label=menu.locator("option", has_text=start).first.text_content())


def _radio(page, name):
    return page.get_by_role("radio", name=name, exact=True)  # exact: "Nouns" is also a part of "Pronouns"


def _switch(page, name):
    return page.get_by_role("switch", name=name, exact=True)


def _tick(page, row):
    return page.get_by_role("checkbox").nth(row)  # 0 is the box of the whole table


def _expect_progress(page, text):
    sync_api.expect(page.get_by_text(text, exact=True)).to_be_visible(timeout=15000)


def _skip_a_word(page, words=3):
    _expect_progress(page, f"1 / {words}")
    page.get_by_role("button", name="Next ▶").click()
    _expect_progress(page, f"2 / {words}")


def _to_russian(page):
    _choose(page, "Русский")
    sync_api.expect(_radio(page, "Глаголы")).to_be_visible(timeout=15000)
    page.wait_for_timeout(3000)  # a lost choice or round shows only after the cells have run again


def test_a_new_tense_starts_a_new_round(browser, base_url):
    with _page(browser, base_url) as page:
        _radio(page, "Verbs").click()
        _skip_a_word(page)
        _choose(page, "Aorist")
        _expect_progress(page, "1 / 3")


def test_a_new_language_keeps_the_part_of_speech_the_tense_and_the_round(browser, base_url):
    with _page(browser, base_url) as page:
        _radio(page, "Verbs").click()
        _expect_progress(page, "1 / 3")
        _choose(page, "Aorist")
        page.wait_for_timeout(2000)
        _skip_a_word(page)
        _to_russian(page)
        sync_api.expect(_radio(page, "Глаголы")).to_be_checked()
        sync_api.expect(_dropdown_with(page, "Аорист").locator("option:checked")).to_have_text(re.compile("^Аорист"))
        _expect_progress(page, "2 / 3")


def test_a_new_language_keeps_the_switches_and_the_ticked_words(browser, base_url):
    with _page(browser, base_url) as page:
        _switch(page, "Also test indefinite article").click()
        page.wait_for_timeout(1000)
        _switch(page, "Require article (noun)").click()  # off: the switch for the indefinite article hides
        page.wait_for_timeout(1000)
        _tick(page, 1).click()  # leaves the first word out
        _skip_a_word(page, words=2)
        _to_russian(page)
        article = _switch(page, "Требовать артикль (существительное)")
        sync_api.expect(article).not_to_be_checked()
        sync_api.expect(_tick(page, 1)).not_to_be_checked()
        sync_api.expect(_tick(page, 2)).to_be_checked()
        _expect_progress(page, "2 / 2")
        article.click()
        sync_api.expect(_switch(page, "Также с неопределённым артиклем")).to_be_checked()


def test_a_new_language_keeps_an_empty_selection(browser, base_url):
    with _page(browser, base_url) as page:
        page.get_by_role("button", name="Clear selection").click()
        sync_api.expect(page.get_by_text("The list is empty.", exact=True)).to_be_visible(timeout=15000)
        _to_russian(page)
        sync_api.expect(page.get_by_text("Список пуст.", exact=True)).to_be_visible()


def test_a_new_language_keeps_an_uploaded_list(browser, base_url, upload):
    with _page(browser, base_url) as page:
        page.locator("input[type=file]").set_input_files(str(upload))
        sync_api.expect(page.get_by_text("uploaded two", exact=True).first).to_be_visible(timeout=15000)
        _radio(page, "Adjectives").click()
        page.wait_for_timeout(1000)
        _switch(page, "Full paradigm (all cases, not just nominative)").click()
        page.wait_for_timeout(1000)
        _skip_a_word(page, words=2)
        _to_russian(page)
        sync_api.expect(_radio(page, "Прилагательные")).to_be_checked()
        sync_api.expect(_switch(page, "Полная парадигма (все падежи, не только именительный)")).to_be_checked()
        sync_api.expect(page.get_by_text("uploaded two", exact=True).first).to_be_visible()
        _expect_progress(page, "2 / 2")
        page.get_by_text("Click to clear files.").click()  # the file field still holds the file
        sync_api.expect(page.get_by_text("uploaded two", exact=True)).to_have_count(0, timeout=15000)
        _expect_progress(page, "1 / 3")


def _leave_the_field_for_the_menu(page, option):
    """As a user does it: the focus goes to the menu first, so the field sends its text."""
    _dropdown_with(page, option).click()


def _only_the_first_word(page):
    page.get_by_role("button", name="Clear selection").click()
    sync_api.expect(page.get_by_text("The list is empty.", exact=True)).to_be_visible(timeout=15000)
    _tick(page, 1).click()
    _expect_progress(page, "1 / 1")


@pytest.mark.parametrize("part", [None, "Verbs"], ids=["nouns", "verbs"])
def test_a_new_language_keeps_the_typed_text(browser, base_url, part):
    with _page(browser, base_url) as page:
        if part:
            _radio(page, part).click()
            page.wait_for_timeout(2000)
        page.locator(FIELD).first.fill("αβγ")
        _leave_the_field_for_the_menu(page, "Русский")
        _to_russian(page)
        sync_api.expect(page.locator(FIELD).first).to_have_value("αβγ")
        _leave_the_field_for_the_menu(page, "English")
        _choose(page, "English")
        sync_api.expect(_radio(page, "Verbs")).to_be_visible(timeout=15000)
        page.wait_for_timeout(3000)
        sync_api.expect(page.locator(FIELD).first).to_have_value("αβγ")


def test_a_new_tense_does_not_keep_the_typed_text(browser, base_url):
    with _page(browser, base_url) as page:
        _radio(page, "Verbs").click()
        page.wait_for_timeout(1000)
        _only_the_first_word(page)  # the same word comes back in the new tense
        page.locator(FIELD).first.fill("αβγ")
        _leave_the_field_for_the_menu(page, "Aorist")
        _choose(page, "Aorist")
        page.wait_for_timeout(3000)
        _expect_progress(page, "1 / 1")
        sync_api.expect(page.locator(FIELD).first).to_have_value("")


def test_again_does_not_keep_the_typed_text(browser, base_url):
    with _page(browser, base_url) as page:
        _only_the_first_word(page)
        page.locator(FIELD).first.fill("αβγ")
        page.get_by_role("button", name="Next ▶").click()
        page.get_by_role("button", name="↺ Again").click()
        _expect_progress(page, "1 / 1")
        sync_api.expect(page.locator(FIELD).first).to_have_value("")


def test_a_cleared_upload_brings_the_demo_words_back(browser, base_url, upload):
    with _page(browser, base_url) as page:
        page.locator("input[type=file]").set_input_files(str(upload))
        sync_api.expect(page.get_by_text("uploaded two", exact=True).first).to_be_visible(timeout=15000)
        page.get_by_text("Click to clear files.").click()
        sync_api.expect(page.get_by_text("uploaded two", exact=True)).to_have_count(0, timeout=15000)
        _expect_progress(page, "1 / 3")

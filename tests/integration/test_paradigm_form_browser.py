"""A real-browser check of the paradigm drill form on a phone.

pytest cannot run the JavaScript inside the widget's `_esm` string. This test runs the drill demo
(`examples/modern_greek_drill_notebook.py`) with `marimo run` and opens it in Chromium at a phone size
(390 x 844, touch). The message of a wrong answer sits under all the rows and the buttons, below the screen
of a phone; the form draws the lines of the checked field under that field instead.

Run:
    uv run pytest tests/integration/test_paradigm_form_browser.py -m integration -v

Needs `playwright` (`pip install playwright`; its browsers need not be installed) and a Chromium: point
`EEE_CHROMIUM` at the binary, or have `chromium` on the PATH, or one under `/opt/pw-browsers`. Without
them the tests are skipped.
"""
import contextlib
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

sync_api = pytest.importorskip("playwright.sync_api")

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "modern_greek_drill_notebook.py"
PHONE_W, PHONE_H = 390, 844
FIELD = "input.eee-para-inp"
NOTE = ".eee-para-note"
# the first field (Nom. Sg.) of each word of the demo's default noun list, by its English meaning
NOM_SG = {"message": "το μήνυμα", "friend": "ο φίλος", "woman": "η γυναίκα"}


@pytest.fixture(scope="module")
def base_url(serve_demo):
    return serve_demo(EXAMPLE)


@contextlib.contextmanager
def _page(browser, base_url):
    ctx = browser.new_context(viewport={"width": PHONE_W, "height": PHONE_H}, device_scale_factor=2,
                              is_mobile=True, has_touch=True)
    page = ctx.new_page()
    try:
        page.goto(base_url, wait_until="load")
        page.wait_for_selector(FIELD, timeout=90000)
        page.wait_for_timeout(1500)
        yield page
    finally:
        ctx.close()


def _enter_in_first_field(page, text):
    first = page.locator(FIELD).first
    first.click()
    first.fill(text)
    page.wait_for_timeout(600)  # the widget sends its values 300 ms after the last key
    page.keyboard.press("Enter")


def test_wrong_enter_draws_the_note_under_the_field_on_the_screen(browser, base_url):
    with _page(browser, base_url) as page:
        _enter_in_first_field(page, "λάθος")
        note = page.locator(NOTE).first
        note.wait_for(state="visible", timeout=30000)
        field_box, note_box = page.locator(FIELD).first.bounding_box(), note.bounding_box()
        assert note_box["y"] >= 0 and note_box["y"] + note_box["height"] <= PHONE_H  # on the screen, no scrolling needed
        assert 0 <= note_box["y"] - (field_box["y"] + field_box["height"]) < 40  # right under the field
        assert "❌" in note.inner_text()


def test_typing_in_the_field_removes_its_note(browser, base_url):
    with _page(browser, base_url) as page:
        _enter_in_first_field(page, "λάθος")
        note = page.locator(NOTE).first
        note.wait_for(state="visible", timeout=30000)
        page.locator(FIELD).first.click()
        page.keyboard.type("x")
        sync_api.expect(note).to_be_hidden()


def test_correct_enter_shows_no_note_and_moves_to_the_next_field(browser, base_url):
    with _page(browser, base_url) as page:
        meaning = page.get_by_text("Translation:").first.inner_text().split(":")[-1].strip()
        _enter_in_first_field(page, NOM_SG[meaning])
        sync_api.expect(page.locator(FIELD).nth(1)).to_be_focused(timeout=30000)
        assert page.locator(NOTE).count() == 0

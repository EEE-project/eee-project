"""A real-browser check of the `interactive_text` widget and `render_gloss_sheet`.

pytest cannot run the JavaScript inside the widget's `_esm` string, and the CSS that places the translation
card and the word sheet only means something in a browser. This test runs the demo notebook
(`examples/interactive_text_notebook.py`) with `marimo run`, opens it in Chromium at a phone width and at a
wide width, and taps the words.

Run:
    uv run pytest tests/integration/test_interactive_text_browser.py -m integration -v

Needs `playwright` (`pip install playwright`; its browsers need not be installed) and a Chromium: point
`EEE_CHROMIUM` at the binary, or have `chromium` on the PATH, or one under `/opt/pw-browsers`. Without
them the tests are skipped.
"""
import contextlib
import glob
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

sync_api = pytest.importorskip("playwright.sync_api")

EXAMPLE = Path(__file__).resolve().parents[2] / "examples" / "interactive_text_notebook.py"
PHONE, WIDE = 390, 1000
# in the demo: the widget with the translation card, and its translation dropdown (the only one with a blank entry)
STANZA = ".eee-stanza-wrap"
TRANSLATION = "select"


def _chromium():
    for candidate in (
        os.environ.get("EEE_CHROMIUM"),
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        *glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome"),
    ):
        if candidate and Path(candidate).exists():
            return candidate
    return None


@pytest.fixture(scope="module")
def base_url():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "-m", "marimo", "run", str(EXAMPLE), "--headless", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    url = f"http://127.0.0.1:{port}/"
    try:
        for _ in range(180):
            try:
                if urllib.request.urlopen(url, timeout=1).status == 200:
                    break
            except OSError:
                time.sleep(0.5)
        else:
            pytest.skip("marimo run did not start")
        yield url
    finally:
        proc.terminate()
        proc.wait(timeout=20)


@pytest.fixture(scope="module")
def browser():
    exe = _chromium()
    if exe is None:
        pytest.skip("no Chromium found (set EEE_CHROMIUM)")
    with sync_api.sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
        yield b
        b.close()


@contextlib.contextmanager
def _page(browser, base_url, width):
    ctx = browser.new_context(viewport={"width": width, "height": 844})
    page = ctx.new_page()
    try:
        page.goto(base_url, wait_until="load")
        page.wait_for_selector(f"{STANZA} .gk-word", timeout=60000)
        page.wait_for_timeout(500)
        yield page
    finally:
        ctx.close()


def _box(page, selector):
    return page.locator(selector).first.bounding_box()


def _settle(page):
    page.wait_for_timeout(1500)  # a tap goes to the kernel and back


def _sheet(page):
    return page.evaluate(
        """() => {
            const el = document.querySelector('.eee-sheet');
            const cs = getComputedStyle(el);
            return {cls: el.className, position: cs.position, display: cs.display, text: el.innerText};
        }"""
    )


def test_wrap_mode_wraps_each_line_with_a_hanging_indent_and_fits_a_phone(browser, base_url):
    with _page(browser, base_url, PHONE) as page:
        lines = page.locator(f"{STANZA} .eee-line")
        assert lines.count() == 2
        assert lines.first.evaluate("el => parseFloat(getComputedStyle(el).textIndent)") < 0
        assert _box(page, f"{STANZA} .eee-stanza")["width"] <= PHONE


def test_the_card_stands_under_the_poem_on_a_phone_and_beside_it_on_a_wide_page(browser, base_url):
    with _page(browser, base_url, PHONE) as page:
        greek, card = _box(page, f"{STANZA} .eee-itext"), _box(page, f"{STANZA} .eee-tr")
        assert card["y"] >= greek["y"] + greek["height"] - 1
    with _page(browser, base_url, WIDE) as page:
        greek, card = _box(page, f"{STANZA} .eee-itext"), _box(page, f"{STANZA} .eee-tr")
        assert card["x"] >= greek["x"] + greek["width"] - 1
        assert abs(card["y"] - greek["y"]) < 5


def test_a_tap_on_a_starred_word_shows_its_note_and_a_tap_on_a_greek_word_replaces_it(browser, base_url):
    with _page(browser, base_url, WIDE) as page:
        notes = page.locator(f"{STANZA} .gk-note")
        assert notes.count() == 3  # man*, turns*, wandered*
        notes.first.click()
        _settle(page)
        assert page.locator(f"{STANZA} .gk-note.active").count() == 1
        assert page.locator(f"{STANZA} .gk-word.active").count() == 0
        sheet = _sheet(page)
        assert "Margin note" in sheet["text"] and "the poem's first noun" in sheet["text"]
        assert "table" not in sheet["text"].lower()

        page.locator(f"{STANZA} .gk-word", has_text="ἔπερσεν").first.click()
        _settle(page)
        assert page.locator(f"{STANZA} .gk-note.active").count() == 0
        assert page.locator(f"{STANZA} .gk-word.active").count() == 1
        assert "Margin note" not in _sheet(page)["text"]
        assert page.locator(".eee-sheet table").count() == 1


def test_a_note_opens_from_the_keyboard(browser, base_url):
    with _page(browser, base_url, WIDE) as page:
        page.locator(f"{STANZA} .gk-note").nth(2).focus()
        page.keyboard.press("Enter")
        _settle(page)
        assert "was driven off course" in _sheet(page)["text"]


def test_the_sheet_is_fixed_to_the_screen_on_a_phone_and_in_the_page_on_a_wide_page(browser, base_url):
    for width, position in ((PHONE, "fixed"), (WIDE, "static")):
        with _page(browser, base_url, width) as page:
            page.locator(f"{STANZA} .gk-word", has_text="ἔπερσεν").first.click()
            _settle(page)
            sheet = _sheet(page)
            assert sheet["position"] == position and " on" in f" {sheet['cls']}"


def test_a_closed_sheet_opens_again_for_the_next_word(browser, base_url):
    with _page(browser, base_url, PHONE) as page:
        notes = page.locator(f"{STANZA} .gk-note")
        notes.first.click()
        _settle(page)
        page.locator(".eee-sheet-close").click()
        assert _sheet(page)["display"] == "none"
        notes.nth(1).click()
        _settle(page)
        sheet = _sheet(page)
        assert sheet["display"] != "none" and "τρόποι" in sheet["text"]


def test_a_pick_in_the_period_dropdown_keeps_the_sheet(browser, base_url):
    with _page(browser, base_url, WIDE) as page:
        page.locator(f"{STANZA} .gk-word", has_text="ἔπερσεν").first.click()
        _settle(page)
        period = page.locator(".eee-sheet select")
        options = period.evaluate("s => [...s.options].map(o => o.value)")
        assert len(options) == 2
        period.select_option(options[1])
        _settle(page)
        assert page.locator(".eee-sheet select").evaluate("s => s.value") == options[1]
        assert _sheet(page)["cls"].split()[-1] == "on"


def test_the_blank_translation_entry_removes_the_card(browser, base_url):
    with _page(browser, base_url, WIDE) as page:
        picker = page.locator(TRANSLATION, has=page.locator("option", has_text="with margin notes"))
        assert page.locator(f"{STANZA} .eee-tr").count() == 1
        picker.select_option("--")
        _settle(page)
        assert page.locator(f"{STANZA} .eee-tr").count() == 0
        assert page.locator(".eee-itext.wrap .eee-line").count() == 2  # the poem stays, without the grid around it

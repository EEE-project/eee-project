"""A real-browser check of the landing hub page (`examples/deploy/hub_index.html`), a static page: where its language box stands and what its cards say.

The page has no kernel, so the test opens the file itself in Chromium at a phone width and at a wide width.

Run:
    uv run pytest tests/integration/test_hub_page_browser.py -m integration -v

Needs `playwright` and a Chromium, like the other browser tests of this folder (see conftest.py). Without them the tests are skipped.
"""
import contextlib
from pathlib import Path

import pytest

from eee_project.content import _UI_LABELS

pytestmark = pytest.mark.integration

pytest.importorskip("playwright.sync_api")

HUB = Path(__file__).resolve().parents[2] / "examples" / "deploy" / "hub_index.html"
PHONE, WIDE, TOPBAR = 390, 1000, 48


@contextlib.contextmanager
def _hub(browser, width, lang):
    ctx = browser.new_context(viewport={"width": width, "height": 844})
    page = ctx.new_page()
    try:
        page.goto(HUB.as_uri(), wait_until="load")
        page.select_option("#langSelect", lang)
        yield page
    finally:
        ctx.close()


@pytest.mark.parametrize("lang", ["en", "ru", "el"])
def test_on_a_phone_the_language_box_stands_between_the_top_bar_and_the_title(browser, lang):
    with _hub(browser, PHONE, lang) as page:
        box, title = page.locator("#langWrap").bounding_box(), page.locator(".eee-title").bounding_box()
        assert box["y"] + box["height"] <= title["y"], (box, title)  # a box fixed at the top right covered the end of the first title line
        assert box["y"] >= TOPBAR and box["x"] + box["width"] <= PHONE


def test_on_a_wide_page_the_language_box_stays_fixed_at_the_top_right(browser):
    with _hub(browser, WIDE, "en") as page:
        assert page.locator("#langWrap").evaluate("el => getComputedStyle(el).position") == "fixed"


@pytest.mark.parametrize("lang", ["en", "ru", "el"])
def test_the_open_label_of_every_card_follows_the_language(browser, lang):
    with _hub(browser, WIDE, lang) as page:
        labels = page.locator(".eee-card-arrow").all_inner_texts()
        assert len(labels) == 7 and set(labels) == {f"{_UI_LABELS['card_list_open'][lang]} →"}, labels  # the words of eee_card_list

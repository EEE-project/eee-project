"""A real-browser check of the Enter key in the two text widgets.

An input method (IME) uses Enter to confirm what is composed, and the browser still sends a keydown for it. Such an Enter
must not check the answer. This test sends the two shapes of that keydown to the one-field drill (`diacritics_text`) and
to the paradigm form (`make_paradigm_form`), then a plain Enter, which still must check.

Run:
    uv run pytest tests/integration/test_enter_key_browser.py -m integration -v

Needs `playwright` and a Chromium: see `test_paradigm_form_browser.py`.
"""
import re

import pytest

pytestmark = pytest.mark.integration

sync_api = pytest.importorskip("playwright.sync_api")

NOTEBOOK = '''import marimo

app = marimo.App()


@app.cell
def _():
    import marimo as mo
    from eee_project.notebook_utils import diacritics_text, make_paradigm_form
    return diacritics_text, make_paradigm_form, mo


@app.cell
def _(diacritics_text, make_paradigm_form, mo):
    one = diacritics_text(mo, placeholder="one field")
    one_ui = one._ui  # the element that makes marimo run the next cell again
    form = make_paradigm_form(mo, ["Nom.", "Gen."])
    mo.vstack([one, form])
    return form, one_ui


@app.cell
def _(form, mo, one_ui):
    mo.md(f"ONE={one_ui.value['enter_pressed']} FORM={form.value['submit_request'].get('request_id', 0)}")
    return


if __name__ == "__main__":
    app.run()
'''
FIELDS = {"ONE": "input[placeholder='one field']", "FORM": "input.eee-para-inp"}
SEND = "(e, marks) => e.dispatchEvent(new KeyboardEvent('keydown', {key: 'Enter', bubbles: true, cancelable: true, ...marks}))"


@pytest.fixture(scope="module")
def base_url(serve_demo, tmp_path_factory):
    path = tmp_path_factory.mktemp("enter") / "enter_notebook.py"
    path.write_text(NOTEBOOK, encoding="utf-8")
    return serve_demo(path)


# keyCode 229: Safari sends the confirming Enter after the composition has ended, with isComposing false
@pytest.mark.parametrize("marks", [{"isComposing": True}, {"keyCode": 229}], ids=["isComposing", "keyCode 229"])
@pytest.mark.parametrize("field", list(FIELDS))
def test_an_enter_of_an_input_method_checks_nothing(browser, base_url, field, marks):
    ctx = browser.new_context()
    try:
        page = ctx.new_page()
        page.goto(base_url, wait_until="load")
        box = page.locator(FIELDS[field]).first
        box.wait_for(timeout=90000)
        counter = page.get_by_text(re.compile(r"ONE=\d+ FORM=\d+"))
        sync_api.expect(counter).to_contain_text(f"{field}=0", timeout=30000)
        box.click()
        box.fill("ab")
        assert box.evaluate(SEND, marks), "the key is cancelled"  # it stays with the browser and the input method
        page.wait_for_timeout(1500)  # time for a wrong check to reach Python and come back
        sync_api.expect(counter).to_contain_text(f"{field}=0")
        page.keyboard.press("Enter")  # a plain Enter still checks, once
        sync_api.expect(counter).to_contain_text(f"{field}=1", timeout=15000)
    finally:
        ctx.close()

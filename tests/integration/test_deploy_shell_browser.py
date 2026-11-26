"""A real-browser check of the demo wrapper page (`examples/deploy/shell_template.html`): a notebook that needs longer
than the error timer is still shown, and the error message goes away.

The test cuts the 90 s timer, serves the page beside a notebook page that writes its text late, and opens it in Chromium.

Run:
    uv run pytest tests/integration/test_deploy_shell_browser.py -m integration -v

Needs `playwright` and a Chromium, like the other browser tests of this folder (see conftest.py). Without them the tests are skipped.
"""
import functools
import http.server
import re
import threading
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

sync_api = pytest.importorskip("playwright.sync_api")

TEMPLATE = Path(__file__).resolve().parents[2] / "examples" / "deploy" / "shell_template.html"
# writes its text 3.5 s after it loads: later than the timer below, as a slow notebook boot is later than 90 s
LATE_NOTEBOOK = "<!doctype html><body><script>setTimeout(()=>{document.body.textContent='lesson text '.repeat(20)},3500)</script>"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


@pytest.fixture(scope="module")
def wrapper_url(tmp_path_factory):
    folder = tmp_path_factory.mktemp("shell")
    page = TEMPLATE.read_text(encoding="utf-8")
    assert page.count("setTimeout(showError, 90000)") == 2
    (folder / "index.html").write_text(page.replace("setTimeout(showError, 90000)", "setTimeout(showError, 1500)"), encoding="utf-8")
    (folder / "notebook.html").write_text(LATE_NOTEBOOK, encoding="utf-8")
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(_QuietHandler, directory=str(folder)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}/index.html"
    server.shutdown()


def test_a_notebook_slower_than_the_timer_is_shown_and_the_message_goes(browser, wrapper_url):
    ctx = browser.new_context()
    ctx.route(re.compile(r"^https://"), lambda route: route.abort())  # fonts and analytics of the wrapper
    try:
        page = ctx.new_page()
        page.goto(wrapper_url, wait_until="load")
        error = page.locator("#error-state")
        sync_api.expect(error).to_be_visible(timeout=3000)  # the timer fired first
        sync_api.expect(page.locator("#notebook-frame")).to_have_class(re.compile(r"\bvisible\b"), timeout=10000)
        sync_api.expect(error).to_be_hidden()
    finally:
        ctx.close()

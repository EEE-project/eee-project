"""What the real-browser tests of this folder share: a Chromium for Playwright and `marimo run` on a demo.

A fixture starts only for a test that asks for it, so the other tests of this folder need neither Playwright nor a Chromium.
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


@contextlib.contextmanager
def _marimo(example, config_dir, theme):
    """`marimo run` on a demo, with a marimo config of its own so the developer's settings cannot leak in."""
    (config_dir / "marimo").mkdir()
    (config_dir / "marimo" / "marimo.toml").write_text(f'[display]\ntheme = "{theme}"\n')
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "-m", "marimo", "run", str(example), "--headless", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        env={**os.environ, "XDG_CONFIG_HOME": str(config_dir)},
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
def serve_demo(tmp_path_factory):
    """`serve_demo(example, theme="light")` starts `marimo run` on a demo and gives its URL; the servers stop when the test module is done."""
    with contextlib.ExitStack() as stack:
        def serve(example, theme="light"):
            return stack.enter_context(_marimo(example, tmp_path_factory.mktemp(f"marimo_{theme}"), theme))
        yield serve


@pytest.fixture(scope="module")
def browser():
    exe = _chromium()
    if exe is None:
        pytest.skip("no Chromium found (set EEE_CHROMIUM)")
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe, args=["--no-sandbox"])
        yield b
        b.close()

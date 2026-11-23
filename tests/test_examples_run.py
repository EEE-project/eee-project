"""Each example in examples/ must run from its first line to its last.

No other test starts an example, so a library change that breaks one shows only when someone runs it or its live
page is rebuilt. A marimo notebook ends with `app.run()` and a plain script runs at once: running the file runs it
all, and an error makes the process exit non-zero.
"""
import importlib.util
import os
import subprocess
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parent.parent / "examples"
SCRIPTS = sorted(EXAMPLES.glob("*.py"))
assert SCRIPTS, "no examples/*.py found"
TIMEOUT = 120


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    """Every example once, 4 at a time: the runs are independent and take 1-6 s each."""
    homes = {s: tmp_path_factory.mktemp(s.stem) for s in SCRIPTS}

    def run(script):
        # -I: examples/ and PYTHON* stay off the import path; an empty HOME: the real ~/.cache is neither read nor written
        try:
            return subprocess.run(
                [sys.executable, "-I", script],
                cwd=EXAMPLES.parent, env={**os.environ, "HOME": str(homes[script])},
                capture_output=True, encoding="utf-8", errors="replace", timeout=TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            return subprocess.CompletedProcess(script, -1, "", f"still running after {TIMEOUT} s")

    with ThreadPoolExecutor(max_workers=4) as pool:
        return dict(zip(SCRIPTS, pool.map(run, SCRIPTS)))


class TestExamples:
    @pytest.mark.parametrize("script", SCRIPTS, ids=lambda s: s.stem)
    def test_runs_to_the_end(self, runs, script):
        assert runs[script].returncode == 0, runs[script].stderr[-2000:]


def test_the_presence_session_of_the_interactive_text_demo_is_balanced(tmp_path, monkeypatch):
    # The demo draws "the word in the translation" with balance_presence_items(by_translator=True): half "no", and the
    # same number of items from each chosen translator (Pope and Murray at the start).
    monkeypatch.setenv("HOME", str(tmp_path))
    spec = importlib.util.spec_from_file_location("interactive_text_demo", EXAMPLES / "interactive_text_notebook.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _, defs = module.app.run()
    items = defs["tp_items"]
    by_translator = Counter(it["translator"] for it in items)
    assert len(items) == 10 and set(by_translator) == {"Pope", "Murray"}
    assert abs(by_translator["Pope"] - by_translator["Murray"]) <= 1
    assert Counter(it["reflected"] for it in items) == {"no": 5, "yes": 5}


def test_a_new_session_of_the_interactive_text_demo_resets_all_six_quiz_states():
    # Structural check: the cell that draws the session resets every quiz state, so a stale score or history never shows.
    import ast
    tree = ast.parse((EXAMPLES / "interactive_text_notebook.py").read_text(encoding="utf-8"))
    cells = [f for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)
             and any(isinstance(n, ast.Assign) and any(getattr(t, "id", None) == "tp_items" for t in n.targets)
                     for n in ast.walk(f))]
    assert len(cells) == 1
    setters = {n.func.id for n in ast.walk(cells[0]) if isinstance(n, ast.Call)
               and isinstance(n.func, ast.Name) and n.func.id.startswith("tp_set_")}
    assert setters == {"tp_set_cv", "tp_set_remaining", "tp_set_score", "tp_set_history", "tp_set_future", "tp_set_restore_entry"}

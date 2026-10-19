"""Each example in examples/ must run from its first line to its last.

No other test starts an example, so a library change that breaks one shows only when someone runs it or its live
page is rebuilt. A marimo notebook ends with `app.run()` and a plain script runs at once: running the file runs it
all, and an error makes the process exit non-zero.
"""
import os
import subprocess
import sys
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

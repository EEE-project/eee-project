"""Tests for examples/deploy/build_shell.py -- the WASM deploy-shell builder.

Not part of the eee_project package (examples/ is excluded from the wheel --
see pyproject.toml's [tool.hatch.build.targets.wheel] packages list), so the
module is loaded directly from its file path rather than imported normally.
"""
import importlib.util
import sys
from pathlib import Path

import pytest

_MODULE_PATH = Path(__file__).parent.parent / "examples" / "deploy" / "build_shell.py"
_spec = importlib.util.spec_from_file_location("build_shell", _MODULE_PATH)
build_shell_module = importlib.util.module_from_spec(_spec)
sys.modules["build_shell"] = build_shell_module
_spec.loader.exec_module(build_shell_module)
build_shell = build_shell_module.build_shell


@pytest.fixture
def dist_dir(tmp_path):
    d = tmp_path / "dist" / "some-demo"
    d.mkdir(parents=True)
    (d / "index.html").write_text("<html>raw marimo export</html>", encoding="utf-8")
    return d


class TestBuildShell:
    def test_renames_export_to_notebook_html(self, dist_dir):
        build_shell(dist_dir, "My Demo")
        assert (dist_dir / "notebook.html").read_text(encoding="utf-8") == "<html>raw marimo export</html>"
        # The rename is a move, not a copy -- nothing else wrote index.html's
        # raw export content back to disk under that name.
        assert "raw marimo export" not in (dist_dir / "index.html").read_text(encoding="utf-8")

    def test_writes_new_index_html_from_template(self, dist_dir):
        build_shell(dist_dir, "My Demo")
        shell = (dist_dir / "index.html").read_text(encoding="utf-8")
        assert "<!DOCTYPE html>" in shell
        assert "notebook-frame" in shell

    def test_title_substituted_at_all_four_spots(self, dist_dir):
        build_shell(dist_dir, "My Demo")
        shell = (dist_dir / "index.html").read_text(encoding="utf-8")
        assert shell.count("My Demo") == 4
        assert "{{TITLE}}" not in shell

    def test_title_with_ampersand_not_html_escaped(self, dist_dir):
        # Real case: "Exercise & Quiz Demo" -- str.replace() is a literal
        # substitution, so this only stays true as long as nothing switches
        # to an auto-escaping template engine without updating this test.
        build_shell(dist_dir, "Exercise & Quiz Demo")
        shell = (dist_dir / "index.html").read_text(encoding="utf-8")
        assert shell.count("Exercise & Quiz Demo") == 4
        assert "&amp;" not in shell

    def test_missing_export_raises(self, tmp_path):
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="index.html"):
            build_shell(empty_dir, "My Demo")
        # Nothing should have been created in the failure case.
        assert not (empty_dir / "notebook.html").exists()

"""The live-demo set must read the same in examples/Makefile, the hub page and the README.

A demo added to one of them and forgotten in another breaks nothing else in the suite, so
this parses the three files and compares them.
"""
import html
import re
from pathlib import Path

EXAMPLES = Path(__file__).parent.parent / "examples"
MAKEFILE = (EXAMPLES / "Makefile").read_text(encoding="utf-8")
HUB = (EXAMPLES / "deploy" / "hub_index.html").read_text(encoding="utf-8")
README = (EXAMPLES / "README.md").read_text(encoding="utf-8")


def _demos():
    """{name: (notebook, exported-to dir, shell-wrapped dir, shell title)} for each target in export-all."""
    demos = {}
    for target in re.search(r"^export-all:(.*)$", MAKEFILE, re.M).group(1).split():
        body = re.search(rf"^{re.escape(target)}:\n((?:\t.*\n)+)", MAKEFILE, re.M).group(1)
        notebook, out = re.search(r"html-wasm examples/(\S+) -o examples/dist/(\S+) ", body).groups()
        shell_out, title = re.search(r'build_shell\.py examples/dist/(\S+) "([^"]*)"', body).groups()
        demos[target.removeprefix("export-")] = (notebook, out, shell_out, title)
    return demos


def _hub_cards():
    """{dir: (card title, i18n key of its description)} for each card on the hub page."""
    cards = {}
    for href, inner in re.findall(r'<a class="card" href="([^"]+)/">(.*?)</a>', HUB, re.S):
        title = re.search(r'<div class="card-title">(.*?)</div>', inner).group(1)
        cards[href] = (html.unescape(title), re.search(r'data-i18n="([^"]+)"', inner).group(1))
    return cards


def _translation_keys(lang):
    block = re.search(rf"\n      {lang}: \{{\n(.*?)\n      \}},", HUB, re.S).group(1)
    return re.findall(r'^\s+(\w+): "', block, re.M)


def _readme_demos():
    """{dir: (title, notebook)} from the README's live-demo bullets."""
    bullets = re.findall(r"^- \*\*(.+?)\*\* \(`(\S+\.py)`\) — .*?codeberg\.page/eee-project/([a-z-]+)/\)", README, re.M)
    return {name: (title, notebook) for title, notebook, name in bullets}


class TestLiveDemoSet:
    def test_hub_links_exactly_the_exported_demos(self):
        assert set(_hub_cards()) == set(_demos())

    def test_each_export_target_exports_and_wraps_its_own_directory(self):
        for name, (_, out, shell_out, _) in _demos().items():
            assert out == name == shell_out

    def test_exported_notebooks_exist(self):
        for notebook, *_ in _demos().values():
            assert (EXAMPLES / notebook).is_file(), notebook

    def test_hub_card_title_is_the_shell_title(self):
        cards = _hub_cards()
        for name, (*_, title) in _demos().items():
            assert cards[name][0] == title

    def test_every_card_description_exists_in_every_language(self):
        for lang in ("en", "ru", "el"):
            keys = _translation_keys(lang)
            for name, (_, key) in _hub_cards().items():
                assert key in keys, f"{name}: no {key} in the {lang} block"

    def test_readme_lists_the_same_demos(self):
        expected = {name: (title, notebook) for name, (notebook, _, _, title) in _demos().items()}
        assert _readme_demos() == expected

    def test_counts_agree(self):
        n = len(_demos())
        assert f"export all {n} live demos" in MAKEFILE
        assert f"All {n} demos exported" in MAKEFILE
        assert f"all {n} interactive notebooks" in README
        assert f"all {n} live demos, served as" in README

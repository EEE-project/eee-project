"""Tests for eee_project.lesson_languages and its commands split_lesson / join_lesson: one notebook per language, and the way back."""
import re
import shutil
import subprocess
import sys
import types

import pytest

from eee_project import join_lesson, lesson_languages as ll, split_lesson
from eee_project.content import _LANGUAGE_OPTIONS
from eee_project.notebook_utils import language_selector

# A marimo notebook with the shapes of a real lesson: a cell that marimo saves with a blank line above `return`, a name (x) that only the ru text uses,
# dicts keyed by language (one line, and multi-line texts), and an if-chain on the language inside a cell.
NOTEBOOK = '''import marimo

__generated_with = "0.23.14"
app = marimo.App(width="medium", app_title="Fixture lesson")


@app.cell(hide_code=True)
def _():
    import os as _os
    return


@app.cell
def _():
    x = "shared"
    return (x,)


@app.cell
def _(alpha_name_one, alpha_name_two, alpha_name_three, alpha_name_four, alpha_name_five, alpha_name_six):
    total = alpha_name_one + alpha_name_two + alpha_name_three + alpha_name_four + alpha_name_five + alpha_name_six
    return (total,)


@app.cell(hide_code=True)
def _(bridge, language_selector, mo):
    lang_sel = language_selector(mo, bridge)
    return (lang_sel,)


@app.cell(hide_code=True)
def _(lang_sel, mo, x):
    _TITLES = {"ru": "ru ж title", "el": "el α title", "en": "en title"}
    _TXT = {
        "ru": f"""
    RU text with {x}
      second line
    """,
        "el": r"""
    EL text
      second line
    """,
        "en": """
    EN text
    """,
    }
    mo.md(_TXT.get(lang_sel.value, _TXT["ru"]) + _TITLES[lang_sel.value])
    return


@app.cell(hide_code=True)
def _(lang_sel):
    _lang = lang_sel.value
    if _lang == "ru":
        note = "ru branch"
    elif _lang == "el":
        note = "el branch"
    else:
        note = "en branch"
    return (note,)


if __name__ == "__main__":
    app.run()
'''

# Plain Python with every shape of if-chain, so that the split files can be run and compared.
CHAINS = '''import types


def language_selector(mo, bridge, options=None, default="en"):
    return types.SimpleNamespace(value=default)


mo = bridge = None
lang_sel = language_selector(mo, bridge)

TITLES = {"ru": "RU title", "el": "EL title", "en": "EN title"}


def chain_full(_lang):
    if _lang == "ru":
        out = "russian"
        out += " text"
    elif _lang == "el":
        out = "greek"  # trailing comment
    else:
        out = f"""english
column zero line {_lang}
  indented line"""
    return out


def chain_no_else(_lang):
    out = "none"
    if _lang == "ru":
        out = "ru only"
    elif _lang == "en":
        out = "en only"
    return out


def chain_two_owners(_lang):
    if _lang == "ru":
        out = "ru"
    else:
        out = "el or en"
    return out


def chain_nested(_lang):
    out = []
    for n in (1, 2):
        if _lang == "el":
            if n == 1:
                out.append("greek one")
            else:
                out.append("greek two")
        elif _lang == "ru":
            out.append("ru")
        else:
            out.append("en")
    return out


def one_liner(_lang):
    if _lang == "ru": return "x"
    return "y"


def other_subject(code):
    if code == "ru":
        return 1
    return 2


def ternary(_lang):
    return "A" if _lang == "ru" else "B"
'''


def marimo_save(text):
    """The text as marimo's own save path writes it (what an editor session does to a notebook file)."""
    try:
        from marimo._ast.codegen import generate_filecontents_from_ir
        from marimo._ast.parse import parse_notebook
    except ImportError:
        pytest.skip("marimo's save functions are not importable")
    return generate_filecontents_from_ir(parse_notebook(text, filepath="x.py"))


def run_python(text):
    module = types.ModuleType("fixture")
    exec(compile(text, "fixture", "exec"), module.__dict__)
    return module


def edited(files, lang, old, new):
    assert files[lang].count(old) == 1, old
    return {**files, lang: files[lang].replace(old, new)}


class TestOutName:
    def test_the_language_label_goes_after_the_first_name_part(self):
        assert ll.out_name("notebook.py", "ru") == "notebook_ru.py"
        assert ll.out_name("notebook.26_05_22.py", "el") == "notebook_el.26_05_22.py"
        assert ll.out_name("chapter_09_notebook.py", "en") == "chapter_09_notebook_en.py"


class TestLabels:
    def test_the_labels_are_those_of_the_language_dropdown(self):
        dropdown = types.SimpleNamespace(ui=types.SimpleNamespace(dropdown=lambda **kw: kw))
        assert language_selector(dropdown, None)["options"] == _LANGUAGE_OPTIONS
        assert ll.LABELS == {code: label for label, code in _LANGUAGE_OPTIONS.items()}


class TestFind:
    def test_every_dict_value_and_every_chain_branch_is_a_place(self):
        slots, pin, report = ll.find(NOTEBOOK)
        assert [s.owners for s in slots] == [("ru",), ("el",), ("en",)] * 2 + [("ru",), ("el",), ("en",)]
        assert report["dict entries"] == 6 and report["chains"] == 1
        assert pin["text"] == "language_selector(mo, bridge)" and pin["plain"] and not pin["marked"]

    def test_a_branch_that_is_not_made_of_whole_lines_is_reported_not_split(self):
        _, _, report = ll.find(CHAINS)
        assert [why for _, why in report["unsupported"]] == ["a branch is not made of whole lines (one-line body, tab or a second statement on a line)"]
        assert report["chains"] == 4 and report["dict entries"] == 3

    def test_ternaries_and_other_subjects_are_left_alone(self):
        _, _, report = ll.find(CHAINS)
        assert report["left as they are"]["ternary on the language"] == 1

    def test_an_else_covers_the_languages_that_no_branch_names(self):
        slots, _, _ = ll.find(CHAINS)
        assert ("el", "en") in [s.owners for s in slots]

    def test_a_chain_that_tests_an_unknown_or_a_repeated_code_is_reported(self):
        text = ('def f(_lang):\n    if _lang == "xx":\n        a = 1\n    return 2\n\n\n'
                'def g(_lang):\n    if _lang == "ru":\n        a = 1\n    elif _lang == "ru":\n        a = 2\n    return 3\n')
        _, _, report = ll.find(text)
        assert [why for _, why in report["unsupported"]] == ["an elif test is not a new language code on the same variable"] * 2

    def test_an_else_after_all_three_languages_is_reported(self):
        text = 'def f(_lang):\n    if _lang == "ru":\n        a = 1\n    elif _lang == "el":\n        a = 2\n    elif _lang == "en":\n        a = 3\n    else:\n        a = 4\n'
        _, _, report = ll.find(text)
        assert [why for _, why in report["unsupported"]] == ["the else can never run (all language codes are tested)"]

    def test_a_dict_with_other_keys_is_counted_and_left_alone(self):
        slots, _, report = ll.find('T = {"ru": 1, "el": 2, "de": 3}\n')
        assert slots == [] and report["left as they are"]["dict with other keys"] == 1

    def test_a_tab_indented_branch_is_reported_not_split(self):
        _, _, report = ll.find('def f(_lang):\n\tif _lang == "ru":\n\t\ta = 1\n\treturn 2\n')
        assert [why for _, why in report["unsupported"]] == ["a branch is not made of whole lines (one-line body, tab or a second statement on a line)"]


class TestSplitSource:
    @pytest.mark.parametrize("source", [NOTEBOOK, CHAINS])
    def test_one_notebook_per_language_that_parses_and_joins_back(self, source):
        files, _ = ll.split_source(source)
        assert set(files) == {"ru", "el", "en"}
        for text in files.values():
            compile(text, "x", "exec")
        assert ll.join_source(files) == source

    def test_the_selector_is_fixed_to_the_language_of_the_notebook(self):
        files, _ = ll.split_source(NOTEBOOK)
        for lang, text in files.items():
            assert f'language_selector(mo, bridge, options={{"{ll.LABELS[lang]}": "{lang}"}}, default="{lang}")  # eee-split lang={lang} orig=language_selector(mo, bridge)' in text

    def test_the_text_of_a_language_stays_in_its_own_notebook(self):
        files, _ = ll.split_source(NOTEBOOK)
        for lang, marks in (("ru", ("RU text", "ru branch", "ru ж title")), ("el", ("EL text", "el branch", "el α title")), ("en", ("EN text", "en branch", "en title"))):
            for other, text in files.items():
                assert all((mark in text) == (other == lang) for mark in marks), (lang, other)

    def test_other_values_become_empty_and_other_branches_become_pass(self):
        files, _ = ll.split_source(NOTEBOOK)
        assert '{"ru": "ru ж title", "el": "", "en": ""}' in files["ru"]
        assert files["en"].count("        pass\n") == 2 and 'note = "en branch"' in files["en"]

    def test_each_notebook_gives_the_results_of_its_language(self):
        source = run_python(CHAINS)
        files, _ = ll.split_source(CHAINS)
        for lang, text in files.items():
            module = run_python(text)
            assert module.lang_sel.value == lang
            for name in ("chain_full", "chain_no_else", "chain_two_owners", "chain_nested", "one_liner", "ternary"):
                assert getattr(module, name)(lang) == getattr(source, name)(lang), (lang, name)

    @pytest.mark.parametrize("source, why", [
        ("x = 1\n", "found 0"),
        (NOTEBOOK + "\nagain = language_selector(mo, bridge)\n", "found 2"),
        ("lang_sel = language_selector(mo, bridge)\n", "nothing to split"),
        (NOTEBOOK.replace("\n", "\r\n"), "CR"),
    ])
    def test_a_notebook_that_cannot_be_split_is_refused(self, source, why):
        with pytest.raises(ll.SplitError, match=why):
            ll.split_source(source)

    def test_a_notebook_that_is_split_already_is_refused(self):
        files, _ = ll.split_source(NOTEBOOK)
        with pytest.raises(ll.SplitError, match="not yet split"):
            ll.split_source(files["ru"])

    def test_a_round_trip_that_is_not_exact_writes_nothing(self, monkeypatch):
        monkeypatch.setattr(ll, "join_source", lambda files, original=None: "changed")
        with pytest.raises(ll.SplitError, match="round trip is not exact"):
            ll.split_source(NOTEBOOK)


class TestCanonical:
    def test_a_marimo_save_does_not_change_it(self):
        assert ll.canonical(marimo_save(NOTEBOOK)) == ll.canonical(NOTEBOOK)

    def test_a_changed_code_line_changes_it(self):
        assert ll.canonical(NOTEBOOK.replace('x = "shared"', 'x = "changed"')) != ll.canonical(NOTEBOOK)

    def test_the_def_lines_and_the_final_return_are_left_out(self):
        text = ll.canonical(NOTEBOOK)
        assert "def _(bridge" not in text and "return (x,)" not in text and "def _():" in text


class TestJoinSource:
    def test_without_the_original_the_source_comes_back(self):
        files, _ = ll.split_source(NOTEBOOK)
        assert ll.join_source(files) == NOTEBOOK

    def test_with_the_original_every_byte_stays_whatever_marimo_saved(self):
        files, _ = ll.split_source(NOTEBOOK)
        saved = {lang: marimo_save(text) for lang, text in files.items()}
        assert saved["ru"] != files["ru"]
        live = saved["el"].replace("def _(lang_sel, mo):", "def _(lang_sel: str, mo):")  # an editor session also writes the type of a name into a def line
        assert live != saved["el"]
        for variant in (files, saved, {**files, "el": saved["el"]}, {**files, "ru": saved["ru"]}, {**files, "el": live}):
            assert ll.join_source(variant, NOTEBOOK) == NOTEBOOK

    def test_texts_edited_in_the_language_notebooks_reach_the_notebook_and_nothing_else_changes(self):
        files, _ = ll.split_source(NOTEBOOK)
        edit = edited(edited(files, "el", "EL text", "EL text EDITED\n    one more line"), "en", '"en title"', '"en title EDITED"')
        want = NOTEBOOK.replace("EL text", "EL text EDITED\n    one more line").replace('"en title"', '"en title EDITED"')
        assert ll.join_source(edit, NOTEBOOK) == want
        assert ll.join_source(edit) == want
        assert ll.join_source({lang: marimo_save(text) for lang, text in edit.items()}, NOTEBOOK) == want

    def test_a_chain_branch_edited_in_its_notebook_reaches_the_source(self):
        files, _ = ll.split_source(CHAINS)
        edit = edited(files, "el", 'out = "greek"  # trailing comment', 'out = "greek EDITED"  # trailing comment')
        assert ll.join_source(edit, CHAINS) == CHAINS.replace('out = "greek"', 'out = "greek EDITED"')

    def test_a_name_that_only_one_language_text_uses_does_not_matter(self):
        files, _ = ll.split_source(NOTEBOOK)
        saved = {lang: marimo_save(text) for lang, text in files.items()}
        assert "def _(lang_sel, mo, x):" in saved["ru"] and "def _(lang_sel, mo, x):" not in saved["el"]
        assert ll.join_source(saved, NOTEBOOK) == NOTEBOOK

    def test_comparing_marimo_normalized_texts_instead_would_refuse_that_set(self):
        files, _ = ll.split_source(NOTEBOOK)

        def skeleton(text):
            normalized = marimo_save(text)
            slots, pin, _ = ll.find(normalized)
            return ll.tokenize(normalized, slots, pin)

        assert skeleton(files["ru"]) != skeleton(files["el"])

    def test_two_owners_of_one_place_must_agree(self):
        files, _ = ll.split_source(CHAINS)
        one = edited(files, "el", 'out = "el or en"', 'out = "el or en EDITED"')
        with pytest.raises(ll.MergeError, match="conflict"):
            ll.join_source(one, CHAINS)
        both = edited(one, "en", 'out = "el or en"', 'out = "el or en EDITED"')
        assert ll.join_source(both, CHAINS) == CHAINS.replace('out = "el or en"', 'out = "el or en EDITED"')

    @pytest.mark.parametrize("make, why", [
        (lambda files: (edited(files, "en", 'x = "shared"', 'x = "changed"'), NOTEBOOK), "outside the language texts, the en notebook"),
        (lambda files: (files, NOTEBOOK.replace('x = "shared"', 'x = "changed"')), "outside the language texts, the ru notebook"),
        (lambda files: (edited(files, "ru", '"el": "", "en": ""}', '"el": "oops", "en": ""}'), NOTEBOOK), "belongs to el"),
        (lambda files: ({**files, "el": re.sub(r"  # eee-split.*", "", files["el"])}, NOTEBOOK), "expected one `# eee-split` marker"),
        (lambda files: ({k: v for k, v in files.items() if k != "el"}, NOTEBOOK), "the split was for"),
        (lambda files: ({**files, "el": files["el"] + "\nx = (\n"}, NOTEBOOK), "does not parse"),
        (lambda files: (files, NOTEBOOK.replace("language_selector(mo, bridge)", "language_selector(mo, bridge, default='ru')")), "must hold the call"),
    ])
    def test_a_set_that_would_lose_or_misplace_something_is_refused(self, make, why):
        files, _ = ll.split_source(NOTEBOOK)
        notebooks, original = make(files)
        with pytest.raises(ll.MergeError, match=re.escape(why)):
            ll.join_source(notebooks, original)

    def test_no_notebooks_at_all_is_refused(self):
        with pytest.raises(ll.MergeError, match="no language notebooks"):
            ll.join_source({}, NOTEBOOK)

    def test_a_notebook_given_under_the_wrong_language_is_refused(self):
        files, _ = ll.split_source(NOTEBOOK)
        with pytest.raises(ll.MergeError, match="the file given as ru says lang=el"):
            ll.join_source({**files, "ru": files["el"]}, NOTEBOOK)

    def test_markers_that_name_different_selector_calls_are_refused(self):
        files, _ = ll.split_source(NOTEBOOK)
        other = files["el"].replace("orig=language_selector(mo, bridge)", "orig=language_selector(mo, bridge2)")
        with pytest.raises(ll.MergeError, match="markers differ"):
            ll.join_source({**files, "el": other}, NOTEBOOK)

    def test_line_ends_other_than_lf_are_refused(self):
        files, _ = ll.split_source(NOTEBOOK)
        with pytest.raises(ll.MergeError, match="CR"):
            ll.join_source(files, NOTEBOOK.replace("\n", "\r\n"))

    def test_a_second_selector_call_in_a_notebook_is_refused(self):
        files, _ = ll.split_source(NOTEBOOK)
        extra = "\nagain = language_selector(mo, bridge)\n"
        with pytest.raises(ll.MergeError, match="ru: the marked selector line was not found"):
            ll.join_source({**files, "ru": files["ru"] + extra})
        with pytest.raises(ll.MergeError, match="el: the marked selector line was not found"):
            ll.join_source({**files, "el": files["el"] + extra}, NOTEBOOK)

    def test_a_cell_signature_that_marimo_wraps_over_several_lines_is_not_compared(self):
        files, _ = ll.split_source(NOTEBOOK)
        saved = {lang: marimo_save(text) for lang, text in files.items()}
        assert "def _(\n    alpha_name_five," in saved["ru"]
        assert ll.join_source(saved, NOTEBOOK) == NOTEBOOK


def course(tmp_path, lesson_names, course_names):
    folder = tmp_path / "course" / "2026_01_01"
    folder.mkdir(parents=True)
    for name in lesson_names:
        (folder / name).write_text("x", encoding="utf-8")
    for name in course_names:
        (folder.parent / name).write_text("x", encoding="utf-8")
    return folder


def readme_of(folder, source=NOTEBOOK):
    _, report = ll.split_source(source)
    return ll.readme_text(folder, "notebook.py", {lang: ll.out_name("notebook.py", lang) for lang in ll.LANGS}, report, {"README.md"}, source)


class TestReadmeText:
    def test_the_files_are_listed_by_language_and_the_shared_ones_apart(self, tmp_path):
        folder = course(tmp_path, ["notebook.py", "vocab_a_ru.tsv", "vocab_a_el.tsv", "vocab_a_en.tsv", "greek.md"], ["note_ru.md", "note_el.md", "note_en.md"])
        text = readme_of(folder)
        assert "| Russian (`ru`) | `notebook_ru.py` | `vocab_a_ru.tsv`, `../note_ru.md` |" in text
        assert "| Greek (`el`) | `notebook_el.py` | `vocab_a_el.tsv`, `../note_el.md` |" in text
        assert "`notebook.py`, `greek.md`" in text
        assert "without a language label" not in text

    def test_a_file_without_a_label_belongs_to_the_language_that_has_no_labeled_file_and_the_text_says_so(self, tmp_path):
        folder = course(tmp_path, ["notebook.py", "vocab_a.tsv", "vocab_a_el.tsv", "vocab_a_en.tsv"], [])
        text = readme_of(folder)
        assert "| Russian (`ru`) | `notebook_ru.py` | `vocab_a.tsv` |" in text
        assert "A file without a language label belongs to the language that has no labeled file of the same name." in text

    def test_files_that_git_ignores_are_left_out(self, tmp_path):
        if shutil.which("git") is None:
            pytest.skip("git is not installed")
        folder = course(tmp_path, ["notebook.py", "translations_ru.md", "greek.md"], [])
        (tmp_path / ".gitignore").write_text("translations_*.md\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
        text = readme_of(folder, NOTEBOOK.replace("EL text", "translations_x"))
        assert "`translations_ru.md`," not in text and "| `notebook_ru.py` | - |" in text
        assert "downloaded from the knowledge base" in text

    def test_the_download_sentence_appears_only_when_the_notebook_names_the_translation_files(self, tmp_path):
        folder = course(tmp_path, ["notebook.py"], [])
        assert "downloaded from the knowledge base" not in readme_of(folder)

    def test_a_machine_without_git_lists_the_files_on_disk(self, tmp_path, monkeypatch):
        def no_git(*args, **kwargs):
            raise OSError("git is not installed")

        monkeypatch.setattr(ll.subprocess, "run", no_git)
        folder = course(tmp_path, ["notebook.py", "greek.md"], [])
        assert "`notebook.py`, `greek.md`" in readme_of(folder)


@pytest.fixture
def lesson(tmp_path):
    folder = course(tmp_path, [], [])
    (folder / "notebook.py").write_text(NOTEBOOK, encoding="utf-8", newline="")
    return folder


def command(module, monkeypatch, *args):
    monkeypatch.setattr(sys, "argv", [module.__name__, *map(str, args)])
    module.main()


class TestSplitLessonCommand:
    def test_writes_the_three_notebooks_and_the_file_list_and_never_overwrites(self, lesson, monkeypatch, capsys):
        command(split_lesson, monkeypatch, lesson / "notebook.py")
        assert sorted(p.name for p in lesson.iterdir()) == ["README.md", "notebook.py", "notebook_el.py", "notebook_en.py", "notebook_ru.py"]
        assert "6 dict values and 1 if-chains split" in capsys.readouterr().out
        before = {p.name: p.read_bytes() for p in lesson.iterdir()}
        with pytest.raises(SystemExit, match="not overwritten, nothing written"):
            command(split_lesson, monkeypatch, lesson / "notebook.py")
        assert {p.name: p.read_bytes() for p in lesson.iterdir()} == before

    def test_a_notebook_it_cannot_split_is_refused_with_the_reason(self, lesson, monkeypatch):
        (lesson / "notebook.py").write_text("x = 1\n", encoding="utf-8")
        with pytest.raises(SystemExit, match="found 0"):
            command(split_lesson, monkeypatch, lesson / "notebook.py")
        assert [p.name for p in lesson.iterdir()] == ["notebook.py"]

    def test_the_readme_name_can_be_chosen(self, lesson, monkeypatch):
        command(split_lesson, monkeypatch, lesson / "notebook.py", "--readme", "LANGUAGES.md")
        assert (lesson / "LANGUAGES.md").exists() and not (lesson / "README.md").exists()

    def test_it_runs_as_a_module(self):
        done = subprocess.run([sys.executable, "-m", "eee_project.split_lesson", "--help"], capture_output=True, text=True)
        assert done.returncode == 0 and "notebook_ru.py" in done.stdout

    def test_the_places_it_could_not_split_are_named(self, lesson, monkeypatch, capsys):
        text = NOTEBOOK.replace('if __name__ == "__main__":', 'def f(_lang):\n    if _lang == "ru": return 1\n    return 2\n\n\nif __name__ == "__main__":')
        (lesson / "notebook.py").write_text(text, encoding="utf-8", newline="")
        command(split_lesson, monkeypatch, lesson / "notebook.py")
        assert "not split, line" in capsys.readouterr().out


class TestJoinLessonCommand:
    def split_and_edit(self, lesson, monkeypatch):
        command(split_lesson, monkeypatch, lesson / "notebook.py")
        path = lesson / "notebook_el.py"
        path.write_text(path.read_text(encoding="utf-8").replace("EL text", "EL text EDITED"), encoding="utf-8", newline="")

    def test_a_dry_run_shows_the_change_and_writes_nothing(self, lesson, monkeypatch, capsys):
        self.split_and_edit(lesson, monkeypatch)
        capsys.readouterr()
        command(join_lesson, monkeypatch, lesson / "notebook.py")
        out = capsys.readouterr().out
        assert "+    EL text EDITED" in out and "nothing written" in out
        assert (lesson / "notebook.py").read_text(encoding="utf-8") == NOTEBOOK

    def test_write_changes_the_notebook_and_a_second_run_finds_nothing_to_do(self, lesson, monkeypatch, capsys):
        self.split_and_edit(lesson, monkeypatch)
        command(join_lesson, monkeypatch, lesson / "notebook.py", "--write")
        assert (lesson / "notebook.py").read_text(encoding="utf-8") == NOTEBOOK.replace("EL text", "EL text EDITED")
        capsys.readouterr()
        command(join_lesson, monkeypatch, lesson / "notebook.py")
        assert "no changes" in capsys.readouterr().out

    def test_a_missing_notebook_is_made_from_the_first_language_notebook(self, lesson, monkeypatch):
        self.split_and_edit(lesson, monkeypatch)
        (lesson / "notebook.py").unlink()
        command(join_lesson, monkeypatch, lesson / "notebook.py", "--write")
        assert (lesson / "notebook.py").read_text(encoding="utf-8") == NOTEBOOK.replace("EL text", "EL text EDITED")

    def test_a_missing_language_notebook_is_named(self, lesson, monkeypatch):
        command(split_lesson, monkeypatch, lesson / "notebook.py")
        (lesson / "notebook_en.py").unlink()
        with pytest.raises(SystemExit, match="notebook_en.py"):
            command(join_lesson, monkeypatch, lesson / "notebook.py")

    def test_code_changed_in_a_language_notebook_is_refused(self, lesson, monkeypatch):
        command(split_lesson, monkeypatch, lesson / "notebook.py")
        path = lesson / "notebook_ru.py"
        path.write_text(path.read_text(encoding="utf-8").replace('x = "shared"', 'x = "changed"'), encoding="utf-8", newline="")
        with pytest.raises(SystemExit, match="outside the language texts"):
            command(join_lesson, monkeypatch, lesson / "notebook.py", "--write")
        assert (lesson / "notebook.py").read_text(encoding="utf-8") == NOTEBOOK

    def test_it_runs_as_a_module(self):
        done = subprocess.run([sys.executable, "-m", "eee_project.join_lesson", "--help"], capture_output=True, text=True)
        assert done.returncode == 0 and "--write" in done.stdout

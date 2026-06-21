"""Tests for notebook_utils — greek_compare, strip_diacritics, GreekConfig, nav functions."""
import pytest

import json
import tempfile
from pathlib import Path

from eee_project._grammar_fmt import fmt_ud_feats
from eee_project.notebook_utils import (
    greek_compare,
    strip_diacritics,
    load_ga_config,
    MODERN_GREEK,
    ANCIENT_GREEK,
    GreekUtils,
    eee_topbar,
    eee_footer,
    ConfigStore,
)


# ────────────────────────────────────────── strip_diacritics ──

class TestStripDiacritics:
    def test_monotonic_accent(self):
        assert strip_diacritics("λέγε") == "λεγε"

    def test_monotonic_multi(self):
        assert strip_diacritics("καλημέρα") == "καλημερα"

    def test_polytonic_rough_breathing(self):
        assert strip_diacritics("ἄνθρωπος") == "ανθρωπος"

    def test_polytonic_smooth_breathing(self):
        assert strip_diacritics("ἐν") == "εν"

    def test_polytonic_iota_subscript(self):
        # iota subscript (ᾳ) is category Mn after NFD decompose — gets stripped
        # leaving only the base vowel
        assert strip_diacritics("τῷ") == "τω"

    def test_plain_string_unchanged(self):
        assert strip_diacritics("λεγε") == "λεγε"

    def test_empty(self):
        assert strip_diacritics("") == ""


# ────────────────────────────────────────────── greek_compare ──

class TestGreekCompare:
    # defaults: case_sensitive=False, diacritics=False

    def test_same_stripped(self):
        assert greek_compare("λεγε", "λέγε") is True

    def test_polytonic_vs_bare(self):
        assert greek_compare("ανθρωπος", "ἄνθρωπος") is True

    def test_different_words(self):
        assert greek_compare("λεγε", "λυω") is False

    def test_case_ignored_by_default(self):
        assert greek_compare("Λέγε", "λέγε") is True

    def test_leading_trailing_whitespace(self):
        assert greek_compare("  λεγε  ", "λεγε") is True

    # diacritics=True: NFC forms must match exactly

    def test_diacritics_true_match(self):
        assert greek_compare("λέγε", "λέγε", diacritics=True) is True

    def test_diacritics_true_mismatch(self):
        assert greek_compare("λεγε", "λέγε", diacritics=True) is False

    def test_diacritics_true_case_still_ignored(self):
        assert greek_compare("Λέγε", "λέγε", diacritics=True) is True

    # case_sensitive=True

    def test_case_sensitive_mismatch(self):
        assert greek_compare("Λεγε", "λεγε", case_sensitive=True) is False

    def test_case_sensitive_match(self):
        assert greek_compare("λεγε", "λεγε", case_sensitive=True) is True

    # both flags True

    def test_both_flags_true_exact_match(self):
        assert greek_compare("λέγε", "λέγε", case_sensitive=True, diacritics=True) is True

    def test_both_flags_true_case_fails(self):
        assert greek_compare("Λέγε", "λέγε", case_sensitive=True, diacritics=True) is False

    def test_both_flags_true_accent_fails(self):
        assert greek_compare("λεγε", "λέγε", case_sensitive=True, diacritics=True) is False


# ──────────────────────────────────────────────── GreekConfig ──

class TestModernGreekConfig:
    def test_language(self):
        assert MODERN_GREEK.language == "el"

    def test_has_indef_articles(self):
        assert MODERN_GREEK.indef_articles is not None

    def test_noun_cells_three_case(self):
        cases = [c for _, c in MODERN_GREEK.noun_cells]
        assert 'dat' not in cases
        assert 'nom' in cases and 'acc' in cases and 'gen' in cases

    def test_verb_prefix_future(self):
        assert MODERN_GREEK.verb_prefix.get('future') == 'θα'

    def test_adj_cases_no_dat(self):
        assert 'dat' not in MODERN_GREEK.adj_cases

    def test_compare_diacritics_true(self):
        assert MODERN_GREEK.compare_diacritics is True

    def test_tense_labels_present(self):
        assert 'present' in MODERN_GREEK.tense_labels
        assert MODERN_GREEK.tense_labels['present']['greek'] == 'Ενεστώτας'

    def test_verb_labels_greek_pronouns(self):
        assert MODERN_GREEK.verb_labels[0] == 'εγώ'


class TestAncientGreekConfig:
    def test_language(self):
        assert ANCIENT_GREEK.language == "grc"

    def test_no_indef_articles(self):
        assert ANCIENT_GREEK.indef_articles is None

    def test_noun_cells_four_case(self):
        cases = [c for _, c in ANCIENT_GREEK.noun_cells]
        assert 'dat' in cases

    def test_no_verb_prefix(self):
        assert ANCIENT_GREEK.verb_prefix == {}

    def test_adj_cases_with_dat(self):
        assert 'dat' in ANCIENT_GREEK.adj_cases

    def test_compare_diacritics_false(self):
        assert ANCIENT_GREEK.compare_diacritics is False

    def test_tense_labels_present(self):
        assert 'present' in ANCIENT_GREEK.tense_labels
        assert ANCIENT_GREEK.tense_labels['present']['greek'] == 'Ἐνεστώς'

    def test_verb_labels_numeric(self):
        assert ANCIENT_GREEK.verb_labels[0] == '1 sg'

    def test_has_perfect_tense(self):
        assert 'perfect' in ANCIENT_GREEK.tense_labels
        assert 'perfect' in ANCIENT_GREEK.tense_feats


# ────────────────────────── GreekUtils._plural_articles / TENSE_LABELS ──

class _StubMo:
    class ui:
        @staticmethod
        def text(label=""): return label
        @staticmethod
        def array(items): return items
    @staticmethod
    def md(s): return s


class _StubBackend:
    def paradigm(self, word, pos): return {}


import pandas as _pd

@pytest.fixture
def gu_mg():
    return GreekUtils(_StubBackend(), _StubMo(), _pd)

@pytest.fixture
def gu_ag():
    return GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK)


class TestGreekUtilsConfig:
    def test_tense_labels_mg(self, gu_mg):
        assert 'present' in gu_mg.TENSE_LABELS
        assert gu_mg.TENSE_LABELS['present']['greek'] == 'Ενεστώτας'

    def test_tense_labels_ag(self, gu_ag):
        assert 'present' in gu_ag.TENSE_LABELS
        assert gu_ag.TENSE_LABELS['present']['greek'] == 'Ἐνεστώς'

    def test_plural_articles_mg(self, gu_mg):
        pl = gu_mg._plural_articles()
        assert 'τα' in pl   # neut pl
        assert 'οι' in pl   # masc/fem pl

    def test_plural_articles_ag(self, gu_ag):
        pl = gu_ag._plural_articles()
        assert 'οἱ' in pl   # masc pl nom
        assert 'τά' in pl   # neut pl nom/acc

    def test_ci_mg_ignores_case_keeps_accent(self, gu_mg):
        # MG: compare_diacritics=True → accents matter
        assert gu_mg._ci("λέγε", {"λέγε"}) is True
        assert gu_mg._ci("Λέγε", {"λέγε"}) is True      # case ignored
        assert gu_mg._ci("λεγε", {"λέγε"}) is False     # accent matters

    def test_ci_ag_strips_accents(self, gu_ag):
        # AG: compare_diacritics=False → accents stripped
        assert gu_ag._ci("λεγε", {"λέγε"}) is True
        assert gu_ag._ci("ανθρωπος", {"ἄνθρωπος"}) is True

    def test_ci_optional_suffix_expansion(self, gu_ag):
        # backend returns "λύουσι(ν)" — both λύουσι and λύουσιν must match
        assert gu_ag._ci("λύουσι",  {"λύουσι(ν)"}) is True
        assert gu_ag._ci("λύουσιν", {"λύουσι(ν)"}) is True
        assert gu_ag._ci("λύουσιξ", {"λύουσι(ν)"}) is False


# ──────────────────────────────────────── eee_topbar / eee_footer ──

class _StubHtmlMo:
    """Marimo stub that captures Html output."""
    class Html:
        def __init__(self, s): self.s = s
        def __str__(self): return self.s


class TestEeeTopbar:
    def test_returns_html(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://example.com",
                            lang="en", titles={"en": "Course"})
        assert isinstance(result, _StubHtmlMo.Html)
        assert "eee-topbar" in result.s
        assert "Course" in result.s
        assert "https://example.com" in result.s

    def test_title_dict_falls_back(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://x.com",
                            lang="de", titles={"en": "Course", "ru": "Курс"})
        # "de" not in dict — falls back to first value
        assert "Course" in result.s or "Курс" in result.s

    def test_plain_string_title(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://x.com",
                            lang="en", titles="My Course")
        assert "My Course" in result.s

    def test_empty_back_url_returns_none(self):
        assert eee_topbar(_StubHtmlMo(), back_url="", lang="en", titles="X") is None
        assert eee_topbar(_StubHtmlMo(), back_url=None, lang="en", titles="X") is None

    def test_ga_script_injected(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://x.com", lang="en",
                            titles="T", ga_config={"measurement_id": "G-TEST123"})
        assert "G-TEST123" in result.s
        assert "gtag" in result.s

    def test_ga_no_back_url_returns_html(self):
        result = eee_topbar(_StubHtmlMo(), back_url="", lang="en",
                            titles="T", ga_config={"measurement_id": "G-TEST123"})
        assert result is not None
        assert "G-TEST123" in result.s

    def test_ga_none_no_script(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://x.com", lang="en",
                            titles="T", ga_config=None)
        assert "gtag" not in result.s

    def test_ga_missing_key_no_script(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://x.com", lang="en",
                            titles="T", ga_config={"other": "value"})
        assert "gtag" not in result.s


class TestLoadGaConfig:
    def test_missing_file_returns_none(self, tmp_path):
        assert load_ga_config(tmp_path / "ga.json") is None

    def test_reads_from_explicit_path(self, tmp_path):
        p = tmp_path / "ga.json"
        p.write_text(json.dumps({"measurement_id": "G-ABC"}))
        assert load_ga_config(p) == {"measurement_id": "G-ABC"}

    def test_resolves_notebook_file(self, tmp_path):
        p = tmp_path / "ga.json"
        p.write_text(json.dumps({"measurement_id": "G-XYZ"}))
        nb = tmp_path / "notebook.py"
        nb.write_text("")
        assert load_ga_config(nb) == {"measurement_id": "G-XYZ"}

    def test_resolves_directory(self, tmp_path):
        (tmp_path / "ga.json").write_text(json.dumps({"measurement_id": "G-DIR"}))
        assert load_ga_config(tmp_path) == {"measurement_id": "G-DIR"}

    def test_malformed_json_returns_none(self, tmp_path):
        (tmp_path / "ga.json").write_text("not json{{{")
        assert load_ga_config(tmp_path / "ga.json") is None

    def test_none_path_uses_cwd(self, tmp_path, monkeypatch):
        (tmp_path / "ga.json").write_text(json.dumps({"measurement_id": "G-CWD"}))
        monkeypatch.chdir(tmp_path)
        assert load_ga_config() == {"measurement_id": "G-CWD"}

    def test_none_path_missing_cwd_returns_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        assert load_ga_config() is None


# ──────────────────────────────────────────────────── fmt_ud_feats ──

class TestFmtUd:
    def test_empty_returns_empty(self):
        assert fmt_ud_feats("", "en") == ""

    def test_present_indicative_en(self):
        result = fmt_ud_feats("VerbForm=Fin|Tense=Pres|Mood=Ind|Person=1|Number=Sing", "en")
        assert "pres." in result
        assert "1" in result
        assert "sg." in result

    def test_present_indicative_ru(self):
        result = fmt_ud_feats("VerbForm=Fin|Tense=Pres|Mood=Ind|Person=3|Number=Plur", "ru")
        assert "наст." in result
        assert "3" in result
        assert "мн." in result

    def test_noun_nominative_sg_en(self):
        result = fmt_ud_feats("Case=Nom|Number=Sing", "en")
        assert "Nom." in result
        assert "sg." in result

    def test_non_indicative_mood_shown(self):
        result = fmt_ud_feats("VerbForm=Fin|Tense=Pres|Mood=Sub|Person=1|Number=Sing", "en")
        assert "subj." in result

    def test_indicative_mood_suppressed(self):
        result = fmt_ud_feats("VerbForm=Fin|Tense=Pres|Mood=Ind|Person=1|Number=Sing", "en")
        assert "ind." not in result

    def test_unknown_lang_falls_back_to_en(self):
        result = fmt_ud_feats("Case=Nom|Number=Sing", "zh")
        assert "Nom." in result

    def test_malformed_feats_returns_original(self):
        assert fmt_ud_feats("NOTFEATS", "en") == "NOTFEATS"


# ───────────────────────── make_item_drill_rows / check_item_drill ──

class _FakeInput:
    def __init__(self, placeholder=""):
        self.value = ""
        self.placeholder = placeholder

class _DrillMo:
    """Minimal marimo stub for item-drill tests."""
    class ui:
        @staticmethod
        def text(placeholder=""): return _FakeInput(placeholder)
    @staticmethod
    def md(s): return s
    @staticmethod
    def hstack(items, **kwargs): return list(items)
    @staticmethod
    def vstack(items, **kwargs): return list(items)
    @staticmethod
    def callout(content, kind="info"): return ("callout", kind, content)


class _StubBackend2:
    def paradigm(self, word, pos): return {}


@pytest.fixture
def gu_drill():
    return GreekUtils(_StubBackend2(), _DrillMo())


_DRILL_ITEMS = [
    {"meaning": "говорить", "verb": "λέγω", "sg": "λέγε", "pl": "λέγετε"},
    {"meaning": "слушать",  "verb": "ἀκούω", "sg": "ἄκουε", "pl": "ἀκούετε"},
]


class TestMakeItemDrillRows:
    def test_returns_correct_shape(self, gu_drill):
        inputs_2d, rows = gu_drill.make_item_drill_rows(
            _DRILL_ITEMS, ["verb", "sg", "pl"])
        assert len(inputs_2d) == 2
        assert len(inputs_2d[0]) == 3
        assert len(rows) == 2

    def test_inputs_have_value_attribute(self, gu_drill):
        inputs_2d, _ = gu_drill.make_item_drill_rows(
            _DRILL_ITEMS, ["verb", "sg"])
        assert hasattr(inputs_2d[0][0], "value")
        assert inputs_2d[0][0].value == ""

    def test_custom_placeholders(self, gu_drill):
        inputs_2d, _ = gu_drill.make_item_drill_rows(
            _DRILL_ITEMS, ["sg", "pl"],
            placeholders=["ед. ч.…", "мн. ч.…"])
        assert inputs_2d[0][0].placeholder == "ед. ч.…"
        assert inputs_2d[0][1].placeholder == "мн. ч.…"

    def test_short_placeholder_list_extended(self, gu_drill):
        inputs_2d, _ = gu_drill.make_item_drill_rows(
            _DRILL_ITEMS, ["verb", "sg", "pl"],
            placeholders=["verb…"])
        assert len(inputs_2d[0]) == 3  # no IndexError


class TestCheckItemDrill:
    def test_all_correct_no_diacritics(self, gu_drill):
        inputs_2d, _ = gu_drill.make_item_drill_rows(_DRILL_ITEMS, ["sg", "pl"])
        inputs_2d[0][0].value = "λεγε"   # stripped diacritics — OK by default
        inputs_2d[0][1].value = "λεγετε"
        fb = gu_drill.check_item_drill(_DRILL_ITEMS, inputs_2d, ["sg", "pl"])
        assert len(fb) == 1
        assert "✓" in fb[0]

    def test_wrong_answer_shows_expected(self, gu_drill):
        inputs_2d, _ = gu_drill.make_item_drill_rows(_DRILL_ITEMS, ["sg"])
        inputs_2d[0][0].value = "λεγεις"  # wrong
        fb = gu_drill.check_item_drill(_DRILL_ITEMS, inputs_2d, ["sg"],
                                       field_labels=["sg."])
        assert len(fb) == 1
        assert "✗" in fb[0]
        assert "λέγε" in fb[0]   # expected shown

    def test_empty_inputs_skipped(self, gu_drill):
        inputs_2d, _ = gu_drill.make_item_drill_rows(_DRILL_ITEMS, ["sg"])
        # leave all inputs empty
        fb = gu_drill.check_item_drill(_DRILL_ITEMS, inputs_2d, ["sg"])
        assert fb == []

    def test_strict_diacritics_rejects_stripped(self, gu_drill):
        inputs_2d, _ = gu_drill.make_item_drill_rows(_DRILL_ITEMS, ["sg"])
        inputs_2d[0][0].value = "λεγε"  # missing accent
        fb = gu_drill.check_item_drill(_DRILL_ITEMS, inputs_2d, ["sg"], strict=True)
        assert "✗" in fb[0]

    def test_field_labels_used_in_feedback(self, gu_drill):
        inputs_2d, _ = gu_drill.make_item_drill_rows(_DRILL_ITEMS, ["sg"])
        inputs_2d[0][0].value = "λεγε"
        fb = gu_drill.check_item_drill(_DRILL_ITEMS, inputs_2d, ["sg"],
                                       field_labels=["ед.ч."])
        assert "ед.ч." in fb[0]

    def test_meaning_key(self, gu_drill):
        items = [{"label": "write", "sg": "γράφε"}]
        inputs_2d, _ = gu_drill.make_item_drill_rows(items, ["sg"], meaning_key="label")
        inputs_2d[0][0].value = "γραφε"
        fb = gu_drill.check_item_drill(items, inputs_2d, ["sg"], meaning_key="label")
        assert "write" in fb[0]


# ─────────────────────────── slot_drill_advance / slot_drill_display ──

_SD_ITEMS = [
    {"meaning": "говорить", "verb": "λέγω", "sg": "λέγε", "pl": "λέγετε"},
    {"meaning": "слушать",  "verb": "ἀκούω", "sg": "ἄκουε", "pl": "ἀκούετε"},
]
_SD_FIELDS = [("verb", "словарная форма"), ("sg", "ед."), ("pl", "мн.")]


class _FakeRand:
    def sample(self, seq, k): return list(seq)[:k]


class TestSlotDrillAdvance:
    def _state(self):
        s = {"cv": _SD_ITEMS[0], "rem": _SD_ITEMS[1:], "fi": 0,
             "sc": {"correct": 0, "total": 0}}
        def set_cv(v): s["cv"] = v
        def set_rem(v): s["rem"] = v
        def set_fi(v): s["fi"] = v
        def set_sc(v): s["sc"] = v
        return s, set_cv, set_rem, set_fi, set_sc

    def test_no_click_does_nothing(self, gu_drill):
        s, *setters = self._state()
        gu_drill.slot_drill_advance(
            0, "λέγω", s["cv"], s["rem"], s["fi"], s["sc"],
            _SD_FIELDS, _SD_ITEMS, _FakeRand(), *setters,
        )
        assert s["fi"] == 0  # unchanged

    def test_correct_answer_increments_score(self, gu_drill):
        s, *setters = self._state()
        gu_drill.slot_drill_advance(
            1, "λέγω",  # exact match (MODERN_GREEK config has diacritics=True)
            s["cv"], s["rem"], 0, {"correct": 0, "total": 0},
            _SD_FIELDS, _SD_ITEMS, _FakeRand(), *setters,
        )
        assert s["sc"]["correct"] == 1
        assert s["fi"] == 1  # advanced to next field

    def test_wrong_answer_still_advances(self, gu_drill):
        s, *setters = self._state()
        gu_drill.slot_drill_advance(
            1, "wrong", s["cv"], s["rem"], 1, {"correct": 0, "total": 0},
            _SD_FIELDS, _SD_ITEMS, _FakeRand(), *setters,
        )
        assert s["sc"]["correct"] == 0
        assert s["fi"] == 2  # sg → pl

    def test_last_field_advances_to_next_item(self, gu_drill):
        s, *setters = self._state()
        gu_drill.slot_drill_advance(
            1, "wrong", s["cv"], _SD_ITEMS[1:], 2, {"correct": 0, "total": 0},
            _SD_FIELDS, _SD_ITEMS, _FakeRand(), *setters,
        )
        assert s["cv"] == _SD_ITEMS[1]
        assert s["rem"] == []
        assert s["fi"] == 0

    def test_last_item_last_field_sets_cv_none(self, gu_drill):
        s, *setters = self._state()
        gu_drill.slot_drill_advance(
            1, "wrong", s["cv"], [], 2, {"correct": 0, "total": 0},
            _SD_FIELDS, _SD_ITEMS, _FakeRand(), *setters,
        )
        assert s["cv"] is None

    def test_restart_when_cv_none(self, gu_drill):
        s, *setters = self._state()
        gu_drill.slot_drill_advance(
            1, "", None, [], 0, {"correct": 99, "total": 99},
            _SD_FIELDS, _SD_ITEMS, _FakeRand(), *setters,
        )
        assert s["cv"] == _SD_ITEMS[0]
        assert s["sc"] == {"correct": 0, "total": 0}


class TestSlotDrillDisplay:
    def _btn(self, val=None):
        return type("Btn", (), {"value": val})()

    def _inp(self, val=""):
        return type("Inp", (), {"value": val})()

    def test_done_shows_callout(self, gu_drill):
        result = gu_drill.slot_drill_display(
            None, 0, {"correct": 3, "total": 5},
            self._inp(), self._btn(), self._btn(),
            fields=_SD_FIELDS,
        )
        assert any("callout" in str(x) for x in result)

    def test_active_cv_shows_meaning(self, gu_drill):
        result = gu_drill.slot_drill_display(
            _SD_ITEMS[0], 0, {"correct": 0, "total": 0},
            self._inp(), self._btn(0), self._btn(),
            fields=_SD_FIELDS, title="## Exercise", n_items=2,
        )
        text = " ".join(str(x) for x in result)
        assert "говорить" in text

    def test_correct_answer_shows_check_mark(self, gu_drill):
        result = gu_drill.slot_drill_display(
            _SD_ITEMS[0], 0, {"correct": 0, "total": 0},
            self._inp("λέγω"), self._btn(1), self._btn(),  # exact match
            fields=_SD_FIELDS, n_items=2,
        )
        text = " ".join(str(x) for x in result)
        assert "✓" in text

    def test_wrong_answer_shows_cross(self, gu_drill):
        result = gu_drill.slot_drill_display(
            _SD_ITEMS[0], 0, {"correct": 0, "total": 0},
            self._inp("wrong"), self._btn(1), self._btn(),
            fields=_SD_FIELDS, n_items=2,
        )
        text = " ".join(str(x) for x in result)
        assert "✗" in text

    def test_empty_input_suppresses_feedback(self, gu_drill):
        result = gu_drill.slot_drill_display(
            _SD_ITEMS[0], 0, {"correct": 0, "total": 0},
            self._inp(""), self._btn(1), self._btn(),
            fields=_SD_FIELDS, n_items=2,
        )
        text = " ".join(str(x) for x in result)
        assert "✓" not in text and "✗" not in text

    def test_custom_meaning_key(self, gu_drill):
        items = [{"adj": "καλός", "meaning": "красивый", "adv": "καλῶς"}]
        result = gu_drill.slot_drill_display(
            items[0], 0, {"correct": 0, "total": 0},
            self._inp(), self._btn(0), self._btn(),
            fields=[("adv", "наречие")], n_items=1, meaning_key="adj",
        )
        text = " ".join(str(x) for x in result)
        assert "καλός" in text


class TestEeeFooter:
    def test_returns_html(self):
        result = eee_footer(_StubHtmlMo(), lang="en")
        assert isinstance(result, _StubHtmlMo.Html)
        assert "eee-footer" in result.s
        assert "codeberg.org/EEE-project" in result.s

    def test_russian_label(self):
        result = eee_footer(_StubHtmlMo(), lang="ru")
        assert "Исходный код" in result.s

    def test_greek_label(self):
        result = eee_footer(_StubHtmlMo(), lang="el")
        assert "Πηγαίος" in result.s

    def test_unknown_lang_falls_back_to_english(self):
        result = eee_footer(_StubHtmlMo(), lang="de")
        assert "Source:" in result.s


_SAMPLE_LESSONS = [
    {"nb_id": "nb_AAA", "icon": "Α", "greek": "Δίδαγμα α'",
     "label": "Занятие 1", "title": "Алфавит", "desc": "Буквы",
     "index_url": "https://molab.marimo.io/notebooks/nb_IDX/app"},
    {"nb_id": "nb_BBB", "icon": "Β", "greek": "Δίδαγμα β'",
     "label": "Занятие 2", "title": "Ударения", "desc": "Просодия",
     "index_url": "https://molab.marimo.io/notebooks/nb_IDX/app"},
]
_SAMPLE_GA = {"measurement_id": "G-TEST1234"}


def _make_resp(data: bytes):
    from unittest.mock import MagicMock
    r = MagicMock()
    r.read.return_value = data
    r.__enter__ = lambda s: s
    r.__exit__ = MagicMock(return_value=False)
    return r


class TestConfigStore:
    def test_from_dict_lessons(self):
        cfg = ConfigStore.from_dict(_SAMPLE_LESSONS, _SAMPLE_GA)
        assert len(cfg.lessons()) == 2
        assert cfg.lessons()[0]["nb_id"] == "nb_AAA"

    def test_from_dict_ga(self):
        cfg = ConfigStore.from_dict(_SAMPLE_LESSONS, _SAMPLE_GA)
        assert cfg.ga_config() == _SAMPLE_GA

    def test_from_dict_no_ga(self):
        cfg = ConfigStore.from_dict(_SAMPLE_LESSONS)
        assert cfg.ga_config() is None

    def test_index_url(self):
        cfg = ConfigStore.from_dict(_SAMPLE_LESSONS, _SAMPLE_GA)
        assert cfg.index_url() == "https://molab.marimo.io/notebooks/nb_IDX/app"

    def test_index_url_empty(self):
        cfg = ConfigStore.from_dict([])
        assert cfg.index_url() is None

    def test_from_url_lessons(self):
        from unittest.mock import patch
        _tsv = (
            "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
            "nb_AAA\tΑ\tΔίδαγμα α'\tЗанятие 1\tАлфавит\tБуквы\thttps://example.com/\n"
        )
        with patch("urllib.request.urlopen", return_value=_make_resp(_tsv.encode("utf-8"))):
            cfg = ConfigStore.from_url("https://example.com/lessons.tsv")
        assert len(cfg.lessons()) == 1
        assert cfg.lessons()[0]["nb_id"] == "nb_AAA"
        assert cfg.index_url() == "https://example.com/"
        assert cfg.ga_config() is None

    def test_from_url_with_ga_dict(self):
        from unittest.mock import patch
        _tsv = "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
        with patch("urllib.request.urlopen", return_value=_make_resp(_tsv.encode("utf-8"))):
            cfg = ConfigStore.from_url("https://example.com/lessons.tsv", ga=_SAMPLE_GA)
        assert cfg.ga_config() == _SAMPLE_GA

    def test_from_url_with_ga_url(self):
        import json
        from unittest.mock import patch
        _tsv = "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
        _ga_json = json.dumps(_SAMPLE_GA).encode("utf-8")
        with patch("urllib.request.urlopen", side_effect=[
            _make_resp(_tsv.encode("utf-8")),
            _make_resp(_ga_json),
        ]):
            cfg = ConfigStore.from_url(
                "https://example.com/lessons.tsv",
                ga="https://example.com/ga.json",
            )
        assert cfg.ga_config() == _SAMPLE_GA

    def test_from_file_reads_tsv(self, tmp_path):
        tsv = tmp_path / "lessons.tsv"
        tsv.write_text(
            "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
            "nb_AAA\tΑ\tΔίδαγμα α'\tЗанятие 1\tАлфавит\tБуквы\thttps://example.com/\n",
            encoding="utf-8",
        )
        cfg = ConfigStore.from_file(tmp_path)
        assert len(cfg.lessons()) == 1
        assert cfg.lessons()[0]["nb_id"] == "nb_AAA"
        assert cfg.lessons()[0]["index_url"] == "https://example.com/"

    def test_from_file_reads_ga(self, tmp_path):
        (tmp_path / "lessons.tsv").write_text(
            "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n", encoding="utf-8"
        )
        (tmp_path / "ga.json").write_text('{"measurement_id": "G-XYZ"}', encoding="utf-8")
        cfg = ConfigStore.from_file(tmp_path)
        assert cfg.ga_config() == {"measurement_id": "G-XYZ"}

    def test_from_file_missing_files(self, tmp_path):
        cfg = ConfigStore.from_file(tmp_path)
        assert cfg.lessons() == []
        assert cfg.ga_config() is None

    def test_from_file_parent_lookup(self, tmp_path):
        subdir = tmp_path / "2026_06_09"
        subdir.mkdir()
        tsv = tmp_path / "lessons.tsv"
        tsv.write_text(
            "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
            "nb_AAA\tΑ\t\t\t\t\thttps://example.com/\n",
            encoding="utf-8",
        )
        nb_file = subdir / "notebook.py"
        nb_file.write_text("")
        cfg = ConfigStore.from_file(nb_file)
        assert cfg.index_url() == "https://example.com/"

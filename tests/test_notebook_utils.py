"""Tests for notebook_utils — greek_compare, strip_diacritics, GreekConfig, nav functions."""
import pytest

import dataclasses
import json
from unittest.mock import patch, MagicMock

import marimo as mo

import eee_project as _eee
from eee_project._grammar_fmt import fmt_ud_feats
from eee_project.notebook_utils import (
    MODERN_GREEK,
    ANCIENT_GREEK,
    GreekUtils,
    eee_topbar,
    eee_ga_tracker,
    eee_hero,
    eee_card_list,
    eee_footer,
    _source_host_base,
    magnify_image,
    language_bridge,
    language_selector,
    ConfigStore,
    make_paradigm_form,
    interactive_text,
    _InteractiveTextWidget,
    _DIA_ESM,
    _PARA_ESM,
    _ITEXT_ESM,
    _ITEXT_CSS,
    _UI_LABELS,
)
from conftest import (
    StubMo as _StubMo, StubBackend as _StubBackend, StubMoLayout as _StubMoLayout,
    LangMo as _LangMo, FakeDropdown as _FakeDropdown,
    FakeParadigmBackend as _FakeParadigmBackend,
    SAMPLE_GA as _SAMPLE_GA, make_resp as _make_resp,
)

# Test-only config fixture for the nav_icons/show_prev_when_done
# resolve-from-config tests below -- not exported from the library. Any
# course (Modern or Ancient Greek) can derive the same kind of value for
# itself via dataclasses.replace(MODERN_GREEK/ANCIENT_GREEK, nav_icons=True,
# ...); the library doesn't bake in a single named variant for one language.
_NAV_ICONS_CONFIG = dataclasses.replace(MODERN_GREEK, nav_icons=True, show_prev_when_done=True)


# ────────────────────────────────────────── Modern (el) verb labels ──

class TestModernVerbLabels:
    """el verb slot labels resolve to human text (not raw pipe tags), enforcing the
    ModernGreekBackend.get_tags ↔ verb-*.tsv contract (section-02)."""

    def _tpls(self, terms="ru"):
        from modern_greek_backend_eee import ModernGreekBackend
        return ModernGreekBackend().get_slot_templates("el", "verb", terms)

    def test_el_verb_labels_resolve_all_langs(self):
        # CONTRACT: every one of the 104 verb bundles resolves in every language
        for terms in ("ru", "en", "el"):
            slots = self._tpls(terms)
            assert slots and len(slots) == 104
            for s in slots:
                assert "|" not in s.label, f"unresolved [{terms}] {s.tag} -> {s.label}"

    def test_el_noun_labels_still_resolve(self):
        from modern_greek_backend_eee import ModernGreekBackend
        for s in ModernGreekBackend().get_slot_templates("el", "noun", "ru"):
            assert "|" not in s.label

    def test_el_verb_specific_labels(self):
        by_tag = {s.tag: s.label for s in self._tpls("ru")}
        assert by_tag["Pres|Ind|Act|1|Sing"] == "Наст. акт. 1 ед."
        assert by_tag["Past.Imp|Ind|Act|1|Sing"] == "Имперф. акт. 1 ед."
        assert by_tag["Past.Perf|Ind|Act|3|Plur"] == "Аор. акт. 3 мн."
        assert by_tag["Sub.Perf|Pass|1|Sing"] == "Сосл. страд. 1 ед."
        assert by_tag["Imp.Perf|Act|2|Sing"] == "Повел. сов. акт. 2 ед."
        assert by_tag["Pres.Perf|Ind|Act|1|Sing"] == "Перф. акт. 1 ед."
        assert by_tag["Pqp|Ind|Pass|3|Plur"] == "Плюскв. страд. 3 мн."


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

    def test_not_polytonic(self):
        # Monotonic orthography (post-1982) -- no breathing/subscript marks needed.
        assert MODERN_GREEK.polytonic is False

    def test_nav_icons_false_by_default(self):
        assert MODERN_GREEK.nav_icons is False
        assert MODERN_GREEK.show_prev_when_done is False

    def test_frozen_rejects_direct_mutation(self):
        # The whole point of nav_icons/show_prev_when_done living on the
        # config is that a course opts in via dataclasses.replace() (a new
        # instance) rather than mutating the shared singleton in place --
        # frozen=True makes the unsafe path a hard error, not just a
        # documented caution, so a future edit can't silently break
        # kavafis_ithaki (which shares this same MODERN_GREEK instance).
        with pytest.raises(dataclasses.FrozenInstanceError):
            MODERN_GREEK.nav_icons = True

    def test_replace_derives_independent_instance(self):
        variant = dataclasses.replace(MODERN_GREEK, nav_icons=True)
        assert variant.nav_icons is True
        assert MODERN_GREEK.nav_icons is False  # untouched
        assert variant.language == MODERN_GREEK.language  # every other field carries over


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

    def test_polytonic(self):
        assert ANCIENT_GREEK.polytonic is True

    def test_adj_cases_with_dat(self):
        assert 'dat' in ANCIENT_GREEK.adj_cases

    def test_compare_diacritics_true(self):
        assert ANCIENT_GREEK.compare_diacritics is True

    def test_tense_labels_present(self):
        assert 'present' in ANCIENT_GREEK.tense_labels
        assert ANCIENT_GREEK.tense_labels['present']['greek'] == 'Ἐνεστώς'

    def test_verb_labels_numeric(self):
        assert ANCIENT_GREEK.verb_labels[0] == '1 sg'

    def test_has_perfect_tense(self):
        assert 'perfect' in ANCIENT_GREEK.tense_labels
        assert 'perfect' in ANCIENT_GREEK.tense_feats


# ────────────────────────── GreekUtils._plural_articles / TENSE_LABELS ──

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

    def test_ci_ag_keeps_accents(self, gu_ag):
        # AG: compare_diacritics=True → accents must match
        assert gu_ag._ci("λέγε", {"λέγε"}) is True
        assert gu_ag._ci("λεγε", {"λέγε"}) is False

    def test_ci_optional_suffix_expansion(self, gu_ag):
        # backend returns "λύουσι(ν)" — both λύουσι and λύουσιν must match
        assert gu_ag._ci("λύουσι",  {"λύουσι(ν)"}) is True
        assert gu_ag._ci("λύουσιν", {"λύουσι(ν)"}) is True
        assert gu_ag._ci("λύουσιξ", {"λύουσι(ν)"}) is False


class TestTenseDropdownOptions:
    """tense_labels' translated names come from data/labels/tense-{lang}.tsv --
    never hardcoded in notebook_utils.py, same routing layer as noun/adj/verb
    slot labels. tense_dropdown_options() is the consumer notebooks should call
    instead of hand-rolling per-language tense-selector option dicts."""

    def test_label_dict_loaded_from_tsv_all_langs(self):
        labels = MODERN_GREEK.tense_labels['future_continuous']['label']
        assert labels == {
            'en': 'Continuous Future',
            'ru': 'Будущее продолженное',
            'el': 'Συνεχής Μέλλοντας',
        }

    def test_dropdown_options_en(self, gu_mg):
        opts = gu_mg.tense_dropdown_options('en')
        assert opts['Continuous Future (Συνεχής Μέλλοντας)'] == 'future_continuous'
        assert opts['Simple Future (Απλός Μέλλοντας)'] == 'future'

    def test_dropdown_options_ru(self, gu_mg):
        # regression: chapter 9's own hand-rolled Russian label for this tense
        # was "Длительное будущее" (wrong word order/term) before being fixed
        # to "Будущее продолженное" -- this is the source of truth now.
        opts = gu_mg.tense_dropdown_options('ru')
        assert opts['Будущее продолженное (Συνεχής Μέλλοντας)'] == 'future_continuous'
        assert opts['Простое будущее (Απλός Μέλλοντας)'] == 'future'

    def test_dropdown_options_el_no_redundant_parenthetical(self, gu_mg):
        # the Greek label IS the parenthetical reference -- "Ενεστώτας
        # (Ενεστώτας)" would be a redundant echo of itself, not a real gloss.
        opts = gu_mg.tense_dropdown_options('el')
        assert 'Ενεστώτας' in opts
        assert 'Ενεστώτας (Ενεστώτας)' not in opts

    def test_dropdown_options_preserves_tense_labels_order(self, gu_mg):
        assert list(gu_mg.tense_dropdown_options('en').values()) == [
            'present', 'aorist', 'future', 'future_continuous',
            'past_continuous', 'subjunctive_simple', 'subjunctive_continuous',
            'conditional_simple', 'conditional_continuous',
        ]

    def test_dropdown_options_unknown_lang_falls_back_to_english(self, gu_mg):
        opts = gu_mg.tense_dropdown_options('fr')
        assert 'Continuous Future (Συνεχής Μέλλοντας)' in opts

    def test_ancient_greek_has_no_future_continuous_but_has_perfect(self, gu_ag):
        opts = gu_ag.tense_dropdown_options('ru')
        assert 'Перфект (Παρακείμενος)' in opts
        assert not any('future_continuous' == v for v in opts.values())


class TestNewModernGreekTenses:
    """Regression tests for the 5 tenses restored 2026-07-28 (past_continuous,
    subjunctive_simple/continuous, conditional_simple/continuous) -- these
    existed in the old modern_greek_eee package but were dropped when
    ellinika_b's tense dropdown switched to eee_project's (then 5-tense-only)
    tense_labels. A 6th, genuinely separate 'imperfect' key was restored
    alongside them, then deliberately dropped again the same day once live
    testing showed it and past_continuous are the exact same Παρατατικός
    conjugation under two different English names -- ellinika_b's own
    material calls this tense "past continuous", so that's the one kept.
    Real ModernGreekBackend, not a stub -- these assert actual generated
    Greek forms, not just wiring."""

    @pytest.fixture
    def gu_real(self):
        from modern_greek_backend_eee import ModernGreekBackend
        return GreekUtils(ModernGreekBackend(), _StubMo(), _pd)

    def test_past_continuous_generates_paratatikos_forms(self, gu_real):
        # Παρατατικός -- confirmed by tracing the old engine's own generation
        # path, which pointed 'imperfect' and 'past_continuous' at the exact
        # same stem/ending rules (no separate 'imperfect' key exists here).
        assert gu_real._verb_forms("διαβάζω", "past_continuous", "sec", "sg") == {"διάβαζες"}

    def test_imperfect_is_not_a_modern_greek_tense_key(self, gu_real):
        # Deliberately absent -- past_continuous is the only name for this
        # tense in the Modern Greek config (Ancient Greek's own 'imperfect'
        # is unrelated and still present in ANCIENT_GREEK.tense_labels).
        assert "imperfect" not in MODERN_GREEK.tense_labels
        assert "imperfect" not in MODERN_GREEK.tense_feats

    def test_subjunctive_simple_uses_aorist_subjunctive_stem(self, gu_real):
        assert gu_real._verb_forms("διαβάζω", "subjunctive_simple", "sec", "sg") == {"διαβάσεις"}
        assert MODERN_GREEK.verb_prefix["subjunctive_simple"] == "να"

    def test_subjunctive_continuous_reuses_present_forms(self, gu_real):
        # {Mood: Sub, Aspect: Imp} isn't supported by the engine -- continuous
        # subjunctive reuses present-tense forms with a να prefix, the same
        # pattern future_continuous already uses (θα + present-tense forms).
        assert (gu_real._verb_forms("διαβάζω", "subjunctive_continuous", "sec", "sg")
                == gu_real._verb_forms("διαβάζω", "present", "sec", "sg"))
        assert MODERN_GREEK.verb_prefix["subjunctive_continuous"] == "να"

    def test_conditional_simple_matches_old_engines_own_example(self, gu_real):
        # Old system's own note: "Uses aorist forms for one-time events
        # (e.g., 'Αν διαβάσεις')" -- reproduced exactly here.
        assert gu_real._verb_forms("διαβάζω", "conditional_simple", "sec", "sg") == {"διαβάσεις"}
        assert MODERN_GREEK.verb_prefix["conditional_simple"] == "αν"

    def test_conditional_continuous_matches_old_engines_own_example(self, gu_real):
        # Old system's own note: "Uses present forms for habitual/regular
        # events (e.g., 'Αν διαβάζεις')" -- reproduced exactly here.
        assert gu_real._verb_forms("διαβάζω", "conditional_continuous", "sec", "sg") == {"διαβάζεις"}
        assert MODERN_GREEK.verb_prefix["conditional_continuous"] == "αν"

    def test_el_label_for_past_continuous_names_the_real_tense(self, gu_real):
        # Old system's own Greek label was "Συνεχής Παρακείμενος" (Perfect) --
        # wrong grammatical term for a Παρατατικός/imperfect-shaped form.
        assert gu_real.TENSE_LABELS["past_continuous"]["greek"] == "Συνεχής Παρατατικός"


class TestUiLabel:
    """Paradigm-drill widget-chrome strings come from data/labels/ui-{lang}.tsv --
    never a per-notebook UI_STRINGS dict + local t_ui() closure. Not Config-scoped
    (unlike tense_labels): one GreekUtils instance with no backend at all still
    resolves every key, since this text belongs to the shared widget, not any
    one course's grammar."""

    def test_known_key_en(self):
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.ui_label('check_label', 'en') == 'Check'

    def test_known_key_ru(self):
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.ui_label('check_label', 'ru') == 'Проверить'

    def test_known_key_el(self):
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.ui_label('check_label', 'el') == 'Έλεγχος'

    def test_odyssey_lang_switcher_keys_present_in_all_3_languages(self):
        # New keys added for created_with_eee's Odyssey lang_sel wiring --
        # asserts real translated text, not just non-echoed presence (that's
        # already covered by test_every_known_key_present_in_all_3_languages).
        gu = GreekUtils(mo_module=_StubMo())
        expected = {
            'stanza_label': {'en': 'Stanza', 'ru': 'Строфа', 'el': 'Στροφή'},
            'trans_selector_label': {'en': 'Translation', 'ru': 'Перевод', 'el': 'Μετάφραση'},
            'interlinear_label': {'en': 'interlinear', 'ru': 'подстрочник', 'el': 'λέξη-λέξη'},
            'stanza_match_section_heading': {
                'en': '### Exercise: match the stanza and translation',
                'ru': '### Упражнение: сопоставь строфу и перевод',
                'el': '### Άσκηση: αντιστοίχισε τη στροφή με τη μετάφραση',
            },
            'stanza_match_direction_label': {'en': '**Direction:**', 'ru': '**Направление:**', 'el': '**Κατεύθυνση:**'},
            'stanza_match_toggle_grc_to_tr': {'en': 'Stanza → translation', 'ru': 'Строфа → перевод', 'el': 'Στροφή → μετάφραση'},
            'stanza_match_toggle_tr_to_grc': {'en': 'Translation → stanza', 'ru': 'Перевод → строфа', 'el': 'Μετάφραση → στροφή'},
            'lesson_materials_label': {'en': '**Lesson materials:**', 'ru': '**Материалы занятия:**', 'el': '**Υλικό μαθήματος:**'},
            'exercises_section_heading': {'en': '## Exercises', 'ru': '## Упражнения', 'el': '## Ασκήσεις'},
            'presence_exercise_heading': {
                'en': '### Exercise: word in the translation', 'ru': '### Упражнение: слово в переводе',
                'el': '### Άσκηση: η λέξη στη μετάφραση',
            },
            'word_find_exercise_heading': {
                'en': '### Exercise: find the word', 'ru': '### Упражнение: найди слово',
                'el': '### Άσκηση: βρες τη λέξη',
            },
            'form_check_accordion_label': {
                'en': 'About form-checking (EEE)', 'ru': 'О проверке форм (EEE)',
                'el': 'Σχετικά με τον έλεγχο τύπων (EEE)',
            },
            'period_selector_label': {'en': 'Period', 'ru': 'Период', 'el': 'Περίοδος'},
        }
        for key, per_lang in expected.items():
            for lang, text in per_lang.items():
                assert gu.ui_label(key, lang) == text, f"{key!r}/{lang!r}"

    def test_lang_none_falls_back_to_english(self):
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.ui_label('check_label', None) == gu.ui_label('check_label', 'en')

    def test_unknown_lang_falls_back_to_english(self):
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.ui_label('check_label', 'fr') == gu.ui_label('check_label', 'en')

    def test_unknown_key_returns_key_itself(self):
        # matches the retired per-notebook t_ui()'s own ultimate fallback --
        # never raise, never return an empty string for a typo'd key.
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.ui_label('not_a_real_key', 'en') == 'not_a_real_key'

    def test_every_known_key_present_in_all_3_languages(self):
        # regression: guards against a TSV row silently dropped for one
        # language during a future edit -- every key must resolve in en/ru/el.
        # Iterates _UI_LABELS itself (not a hand-copied key list) so a newly
        # added key is covered automatically, with nothing to keep in sync.
        gu = GreekUtils(mo_module=_StubMo())
        assert len(_UI_LABELS) >= 80  # sanity: catches a broken loader returning {}
        for key in _UI_LABELS:
            for lang in ('en', 'ru', 'el'):
                label = gu.ui_label(key, lang)
                assert label != key, f"{key!r} missing a real {lang} label (echoed the key back)"


# ──────── language_bridge / language_selector / save_language_selection ──

class TestLanguageBridge:
    def test_returns_none_without_anywidget(self):
        import eee_project.notebook_utils as _nu
        orig = _nu._ANYWIDGET_OK
        try:
            _nu._ANYWIDGET_OK = False
            assert language_bridge(_LangMo()) is None
        finally:
            _nu._ANYWIDGET_OK = orig

    def test_returns_wrapped_widget_with_anywidget(self):
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        bridge = language_bridge(_LangMo())
        assert bridge is not None
        assert bridge.stored is None


class TestLanguageSelector:
    def test_bridge_none_uses_default(self):
        selector = language_selector(_LangMo(), None)
        assert selector.value == "en"

    def test_bridge_none_custom_default(self):
        selector = language_selector(_LangMo(), None, default="ru")
        assert selector.value == "ru"

    def test_bridge_unset_uses_default(self):
        # bridge exists but hasn't reported back a real value yet (still
        # None) -- e.g. the very first cell execution, before the
        # browser's (async) localStorage read has had a chance to land.
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        mo_stub = _LangMo()
        bridge = language_bridge(mo_stub)
        selector = language_selector(mo_stub, bridge)
        assert selector.value == "en"

    def test_bridge_real_valid_value_used(self):
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        mo_stub = _LangMo()
        bridge = language_bridge(mo_stub)
        bridge.stored = "ru"
        selector = language_selector(mo_stub, bridge)
        assert selector.value == "ru"

    def test_bridge_real_invalid_value_falls_back_to_default(self):
        # a stale/unrecognized stored value (e.g. a removed language) must
        # not break the selector -- falls back to *default*, not "xx".
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        mo_stub = _LangMo()
        bridge = language_bridge(mo_stub)
        bridge.stored = "xx"
        selector = language_selector(mo_stub, bridge)
        assert selector.value == "en"

    def test_custom_options(self):
        selector = language_selector(_LangMo(), None, options={"Foo": "fo", "Bar": "ba"}, default="ba")
        assert selector.value == "ba"


# ──────────────────────────────────────── eee_topbar / eee_footer ──

class _StubHtmlMo:
    """Marimo stub that captures Html output."""
    class Html:
        def __init__(self, s): self.s = s
        def __str__(self): return self.s
    @staticmethod
    def md(s): return s


class TestEeeTopbar:
    def test_returns_html(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://example.com",
                            lang="en", titles={"en": "Course"})
        assert isinstance(result, _StubHtmlMo.Html)
        assert "eee-topbar" in result.s
        assert "Course" in result.s
        assert "https://example.com" in result.s

    def test_table_left_align_css_present(self):
        # marimo's own theme right-aligns .markdown table cells by default;
        # every notebook's vocabulary/grammar/phrase tables need left instead.
        result = eee_topbar(_StubHtmlMo(), back_url="https://example.com",
                            lang="en", titles={"en": "Course"})
        assert "text-align: left !important" in result.s
        assert ".markdown table td" in result.s

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

    def test_default_opens_new_tab(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://x.com", lang="en", titles="X")
        assert 'target="_blank" rel="noopener"' in result.s

    def test_same_window_omits_target_blank(self):
        # the topbar's separate "EEE Community" Telegram link is external and
        # always target="_blank" regardless of same_window -- only the
        # tb-back in-app navigation link is affected.
        result = eee_topbar(_StubHtmlMo(), back_url="https://x.com", lang="en",
                            titles="X", same_window=True)
        assert '<a class="tb-back" href="https://x.com">' in result.s

    def test_same_window_index_style_omits_target_blank(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://x.com", lang="en",
                            titles="X", style="index", same_window=True)
        assert '<a class="tb-back" href="https://x.com">' in result.s

    def test_ga_script_injected(self):
        # mo.Html() can't execute inline <script> tags, so GA is fired by a
        # real anywidget instead — its _esm carries the measurement ID and
        # gtag calls, not the plain topbar HTML.
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        result = eee_topbar(_FormMo(), back_url="https://x.com", lang="en",
                            titles="T", ga_config={"measurement_id": "G-TEST123"})
        bar, widget = result
        assert "G-TEST123" not in bar.s
        assert "G-TEST123" in widget._esm
        assert "gtag" in widget._esm

    def test_ga_no_back_url_returns_html(self):
        # vstack-wrapped (not the bare widget) -- see the branch's own
        # comment: a bare anywidget cell output doesn't reliably mount in a
        # real WASM export, confirmed via a real browser, not unit-testable
        # with this stub (no real DOM/mount step).
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        result = eee_topbar(_FormMo(), back_url="", lang="en",
                            titles="T", ga_config={"measurement_id": "G-TEST123"})
        assert result is not None
        assert "G-TEST123" in result[0]._esm

    def test_ga_falls_back_to_plain_html_without_anywidget(self):
        import eee_project.notebook_utils as _nu
        orig = _nu._ANYWIDGET_OK
        try:
            _nu._ANYWIDGET_OK = False
            result = eee_topbar(_StubHtmlMo(), back_url="https://x.com", lang="en",
                                titles="T", ga_config={"measurement_id": "G-TEST123"})
            assert isinstance(result, _StubHtmlMo.Html)
            assert "G-TEST123" not in result.s
        finally:
            _nu._ANYWIDGET_OK = orig

    def test_ga_none_no_script(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://x.com", lang="en",
                            titles="T", ga_config=None)
        assert "gtag" not in result.s

    def test_ga_missing_key_no_script(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://x.com", lang="en",
                            titles="T", ga_config={"other": "value"})
        assert "gtag" not in result.s


class TestAnywidgetImportFallback:
    def test_module_imports_and_skips_anywidget_features_when_it_is_missing(self, monkeypatch):
        import importlib.util
        import sys
        import eee_project.notebook_utils as _nu
        name = "_eee_notebook_utils_without_anywidget"
        spec = importlib.util.spec_from_file_location(name, _nu.__file__)
        fresh = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, "anywidget", None)  # makes `import anywidget` raise ImportError
        monkeypatch.setitem(sys.modules, name, fresh)
        spec.loader.exec_module(fresh)
        assert fresh._ANYWIDGET_OK is False
        assert fresh._make_ga_widget(None, {"measurement_id": "G-TEST123"}) is None


class TestEeeGaTracker:
    """A no-chrome sibling to eee_topbar's back_url="" short-circuit, for a
    notebook with no topbar at all -- see eee_ga_tracker's own docstring."""

    def test_fires_ga_widget(self):
        # vstack-wrapped (not the bare widget) -- see the function's own
        # comment: a bare anywidget cell output doesn't reliably mount in a
        # real WASM export, confirmed via a real browser, not unit-testable
        # with this stub (no real DOM/mount step).
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        result = eee_ga_tracker(_FormMo(), {"measurement_id": "G-TEST123"})
        assert result is not None
        assert "G-TEST123" in result[0]._esm
        assert "gtag" in result[0]._esm

    def test_no_ga_config_returns_none(self):
        assert eee_ga_tracker(_FormMo(), None) is None

    def test_missing_measurement_id_returns_none(self):
        assert eee_ga_tracker(_FormMo(), {"other": "value"}) is None


class TestEeeHero:
    _TITLES = {"ru": ("Заголовок", "Подзаголовок"), "el": ("Τίτλος", "Υπότιτλος"), "en": ("Title", "Subtitle")}

    def test_returns_html_with_title_and_subtitle(self):
        result = eee_hero(_StubHtmlMo(), "en", self._TITLES)
        assert isinstance(result, _StubHtmlMo.Html)
        assert "Title" in result.s
        assert "Subtitle" in result.s
        assert "eee-hero" in result.s

    def test_lang_fallback_used_when_translation_missing(self):
        result = eee_hero(_StubHtmlMo(), "fr", self._TITLES, lang_fallback="el")
        assert "Τίτλος" in result.s
        assert "Υπότιτλος" in result.s

    def test_lang_fallback_en(self):
        result = eee_hero(_StubHtmlMo(), "fr", self._TITLES, lang_fallback="en")
        assert "Title" in result.s


class TestEeeCardList:
    _ROW = {
        "url": "https://molab.marimo.io/notebooks/nb_ABC123/app", "icon": "📖", "greek": "λόγος",
        "label_ru": "Урок 1", "label_el": "Μάθημα 1", "label_en": "Lesson 1",
        "title_ru": "Заголовок", "title_el": "Τίτλος", "title_en": "Title",
        "desc_ru": "Описание", "desc_el": "Περιγραφή", "desc_en": "Description",
    }

    def _cfg(self, rows, raw_base="https://example.com/course"):
        return ConfigStore(rows, _raw_base=raw_base)

    def test_returns_html_with_row_fields(self):
        result = eee_card_list(_StubHtmlMo(), self._cfg([self._ROW]), lang="en")
        assert isinstance(result, _StubHtmlMo.Html)
        assert "Lesson 1" in result.s
        assert "Title" in result.s
        assert "Description" in result.s
        assert "λόγος" in result.s

    def test_url_used_verbatim(self):
        row = {**self._ROW, "url": "https://example.com/custom"}
        result = eee_card_list(_StubHtmlMo(), self._cfg([row]), lang="en")
        assert 'href="https://example.com/custom"' in result.s
        assert "molab.marimo.io" not in result.s

    def test_card_link_has_target_blank_and_noopener(self):
        result = eee_card_list(_StubHtmlMo(), self._cfg([self._ROW]), lang="en")
        assert 'target="_blank" rel="noopener"' in result.s

    def test_same_window_omits_target_blank(self):
        result = eee_card_list(_StubHtmlMo(), self._cfg([self._ROW]), lang="en", same_window=True)
        assert "target=" not in result.s
        assert f'href="{self._ROW["url"]}"' in result.s

    def test_empty_url_renders_disabled_card(self):
        row = {**self._ROW, "url": ""}
        result = eee_card_list(_StubHtmlMo(), self._cfg([row]), lang="en")
        assert "eee-card-disabled" in result.s
        assert "coming soon" in result.s
        assert "<a " not in result.s

    def test_lang_fallback_used_when_translation_missing(self):
        result = eee_card_list(_StubHtmlMo(), self._cfg([self._ROW]), lang="fr", lang_fallback="el")
        assert "Μάθημα 1" in result.s
        assert "Τίτλος" in result.s

    def test_lang_fallback_en(self):
        result = eee_card_list(_StubHtmlMo(), self._cfg([self._ROW]), lang="fr", lang_fallback="en")
        assert "Lesson 1" in result.s

    def test_empty_lessons_returns_load_error(self):
        result = eee_card_list(_StubHtmlMo(), self._cfg([]), lang="en")
        assert "Couldn't load file" in result
        assert "https://example.com/course/index.tsv" in result

    def test_empty_lessons_load_error_russian(self):
        result = eee_card_list(_StubHtmlMo(), self._cfg([]), lang="ru")
        assert "Не удалось загрузить файл" in result

    def test_empty_lessons_load_error_falls_back(self):
        result = eee_card_list(_StubHtmlMo(), self._cfg([]), lang="fr", lang_fallback="en")
        assert "Couldn't load file" in result


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

    def test_pron_type_prs_shown(self):
        """PronType=Prs adds a rendered fragment to the label -- comparing
        against the identical feature string minus PronType is what
        actually proves PronType is being formatted, not silently
        dropped (a bare "result != ''" would pass vacuously here, since
        Person/Number/Case already produce non-empty output on their
        own -- confirmed empirically while writing this test: both
        strings produced byte-identical output before implementation)."""
        with_pt = fmt_ud_feats("PronType=Prs|Case=Nom|Number=Sing|Person=1", "en")
        without_pt = fmt_ud_feats("Case=Nom|Number=Sing|Person=1", "en")
        assert with_pt != without_pt

    def test_pron_type_dem_shown(self):
        with_pt = fmt_ud_feats("PronType=Dem|Case=Nom|Number=Sing|Gender=Masc", "en")
        without_pt = fmt_ud_feats("Case=Nom|Number=Sing|Gender=Masc", "en")
        assert with_pt != without_pt

    def test_pron_type_rel_shown(self):
        with_pt = fmt_ud_feats("PronType=Rel|Case=Nom|Number=Sing|Gender=Masc", "en")
        without_pt = fmt_ud_feats("Case=Nom|Number=Sing|Gender=Masc", "en")
        assert with_pt != without_pt

    def test_pron_type_int_shown(self):
        with_pt = fmt_ud_feats("PronType=Int|Case=Nom|Number=Sing|Gender=Masc", "en")
        without_pt = fmt_ud_feats("Case=Nom|Number=Sing|Gender=Masc", "en")
        assert with_pt != without_pt

    def test_pron_type_ind_shown(self):
        with_pt = fmt_ud_feats("PronType=Ind|Case=Nom|Number=Sing|Gender=Masc", "en")
        without_pt = fmt_ud_feats("Case=Nom|Number=Sing|Gender=Masc", "en")
        assert with_pt != without_pt

    def test_pron_type_rcp_shown(self):
        with_pt = fmt_ud_feats("PronType=Rcp|Case=Gen|Number=Dual|Gender=Masc", "en")
        without_pt = fmt_ud_feats("Case=Gen|Number=Dual|Gender=Masc", "en")
        assert with_pt != without_pt

    def test_pron_type_values_render_distinctly(self):
        """The six PronType labels (Prs/Dem/Rel/Int/Ind/Rcp), rendered
        alongside an otherwise-identical, already-formatted feature set,
        must not all collapse to one identical fragment. Deliberately
        holds Case/Number/Gender constant across all six calls so the
        only thing that can make results differ is real PronType
        formatting (a raw-string fallback, which would trivially make
        six *different input strings* look "distinct" without actually
        formatting anything, is ruled out this way -- confirmed this
        exact trap during test-writing: an earlier version of this test
        used bare "PronType=X" alone and passed vacuously before
        implementation, since fmt_ud_feats' raw-fallback-on-no-match
        behavior preserves distinctness of literally any six different
        inputs for free)."""
        results = {
            fmt_ud_feats(f"PronType={pt}|Case=Nom|Number=Sing|Gender=Masc", "en")
            for pt in ("Prs", "Dem", "Rel", "Int", "Ind", "Rcp")
        }
        assert len(results) == 6

    def test_pron_type_absent_from_label_when_not_present(self):
        """Sanity check: PronType handling must not leak into labels for
        non-pronoun feature strings that never had PronType to begin
        with (regression guard against an over-eager default)."""
        result = fmt_ud_feats("Case=Nom|Number=Sing", "en")
        for pt_label in ("Prs", "Dem", "Rel", "Int", "Ind", "Rcp"):
            assert pt_label not in result

    def test_pron_type_ru_values_render_distinctly(self):
        """Same shape as test_pron_type_values_render_distinctly, but for
        "ru" -- the language column with an actual collision risk (Prs's
        abbreviation was originally "личн.", byte-identical to
        VerbForm=Fin's own "личн."). Not exercised by the "en"-only tests
        above; caught in code review that this file had zero Russian
        PronType coverage despite Russian being the notebooks' primary
        display language."""
        results = {
            fmt_ud_feats(f"PronType={pt}|Case=Nom|Number=Sing|Gender=Masc", "ru")
            for pt in ("Prs", "Dem", "Rel", "Int", "Ind", "Rcp")
        }
        assert len(results) == 6

    def test_pron_type_prs_ru_distinct_from_verbform_fin_ru(self):
        """PronType=Prs's Russian label must not collide with
        VerbForm=Fin's -- they're grammatically distinct concepts
        (personal pronoun vs. finite verb form) that happen to share the
        same natural Russian abbreviation root ("личн."). VerbForm and
        PronType never co-occur in one feats dict today (verbs and
        pronouns are disjoint pos values), so this never produces a
        visibly broken single label, but a reader comparing labels
        across different word-type tables would otherwise see the same
        abbreviation mean two unrelated things."""
        prs_label = fmt_ud_feats("PronType=Prs", "ru")
        fin_label = fmt_ud_feats("VerbForm=Fin", "ru")
        assert prs_label != fin_label


# ───────────────────────── make_item_drill_rows / check_item_drill ──

class _FakeInput:
    def __init__(self, placeholder=""):
        self.value = ""
        self.placeholder = placeholder

class _DrillMo(_StubMoLayout):
    """Minimal marimo stub for item-drill tests."""
    class ui:
        @staticmethod
        def text(placeholder=""): return _FakeInput(placeholder)


@pytest.fixture
def gu_drill():
    return GreekUtils(_StubBackend(), _DrillMo())


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
        inputs_2d[0][0].value = "λεγε"   # stripped diacritics — OK with strict=False
        inputs_2d[0][1].value = "λεγετε"
        fb = gu_drill.check_item_drill(_DRILL_ITEMS, inputs_2d, ["sg", "pl"],
                                       strict=False)
        assert len(fb) == 1
        assert "✓" in fb[0]

    def test_all_correct_with_diacritics_default(self, gu_drill):
        inputs_2d, _ = gu_drill.make_item_drill_rows(_DRILL_ITEMS, ["sg", "pl"])
        inputs_2d[0][0].value = "λέγε"   # exact diacritics — OK with default
        inputs_2d[0][1].value = "λέγετε"
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

    def test_no_prev_next_renders_spacers_not_links(self):
        result = eee_footer(_StubHtmlMo(), lang="en")
        assert "footer-nav-spacer" in result.s
        assert "footer-nav\"" not in result.s

    def test_prev_url_renders_left_triangle_link(self):
        result = eee_footer(_StubHtmlMo(), lang="en", prev_url="/course/chapter_01/", same_window=True)
        assert '<a class="footer-nav" href="/course/chapter_01/">◀</a>' in result.s
        assert "▶" not in result.s

    def test_next_url_renders_right_triangle_link(self):
        result = eee_footer(_StubHtmlMo(), lang="en", next_url="/course/chapter_03/", same_window=True)
        assert '<a class="footer-nav" href="/course/chapter_03/">▶</a>' in result.s
        assert "◀" not in result.s

    def test_prev_and_next_both_render(self):
        result = eee_footer(_StubHtmlMo(), lang="en",
                             prev_url="/course/chapter_01/", next_url="/course/chapter_03/")
        assert '<a class="footer-nav" href="/course/chapter_01/"' in result.s
        assert '<a class="footer-nav" href="/course/chapter_03/"' in result.s
        # Missing side still gets no spacer element once the other side is
        # present (the CSS rule for it is always embedded, so check for the
        # actual <span>, not the bare class-name substring).
        assert '<span class="footer-nav-spacer">' not in result.s

    def test_prev_next_default_new_tab(self):
        result = eee_footer(_StubHtmlMo(), lang="en", prev_url="/course/chapter_01/")
        assert '<a class="footer-nav" href="/course/chapter_01/" target="_blank" rel="noopener">◀</a>' in result.s

    def test_prev_next_same_window_true_omits_target(self):
        result = eee_footer(_StubHtmlMo(), lang="en", prev_url="/course/chapter_01/", same_window=True)
        assert '<a class="footer-nav" href="/course/chapter_01/">◀</a>' in result.s

    def test_same_window_does_not_affect_source_link(self):
        result = eee_footer(_StubHtmlMo(), lang="en", same_window=True)
        assert '<a href="https://codeberg.org/EEE-project" target="_blank">' in result.s


class TestSourceHostBase:
    """_source_host_base() / eee_footer()'s link must match the serving
    host, not always Codeberg -- see eee_footer's own docstring."""

    @staticmethod
    def _install_fake_js(monkeypatch, hostname):
        # Mocks js.self (the Worker global marimo's Pyodide kernel actually
        # runs in), not js.window -- confirmed directly against a real
        # exported notebook that `from js import window` raises ImportError
        # there; only `self` is valid.
        import sys
        import types
        fake_location = types.SimpleNamespace(hostname=hostname)
        fake_self = types.SimpleNamespace(location=fake_location)
        fake_js = types.SimpleNamespace(**{"self": fake_self})
        monkeypatch.setitem(sys.modules, "js", fake_js)

    def test_eee_footer_links_to_detected_host(self, monkeypatch):
        _source_host_base.cache_clear()
        self._install_fake_js(monkeypatch, "eee-project.github.io")
        result = eee_footer(_StubHtmlMo(), lang="en")
        assert 'href="https://github.com/EEE-project"' in result.s
        assert "github.com/EEE-project" in result.s
        assert "codeberg.org/EEE-project" not in result.s


class TestMagnifyImage:
    _RAW_BASE = "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main/odyssey/2026_06_15"

    def test_missing_path_falls_back_to_remote_url(self, tmp_path):
        # No local file -- both the click-through and the thumbnail fall back
        # to the remote URL rather than rendering nothing, regardless of
        # prefer_local (there's no local file to prefer).
        result = magnify_image(_StubHtmlMo(), tmp_path / "missing.jpg", raw_base=self._RAW_BASE, width=280)
        assert isinstance(result, _StubHtmlMo.Html)
        assert result.s.count(f"{self._RAW_BASE}/missing.jpg") == 2
        assert "data:image" not in result.s
        result_pl = magnify_image(_StubHtmlMo(), tmp_path / "missing.jpg", raw_base=self._RAW_BASE, prefer_local=True)
        assert result_pl.s.count(f"{self._RAW_BASE}/missing.jpg") == 2

    def test_existing_path_wraps_in_magnify_link(self, tmp_path):
        img = tmp_path / "pic.jpg"
        img.write_bytes(b"\xff\xd8\xff\xe0fake-jpeg-bytes")
        result = magnify_image(_StubHtmlMo(), img, raw_base=self._RAW_BASE, width=280)
        assert isinstance(result, _StubHtmlMo.Html)
        assert 'target="_blank"' in result.s
        assert f'<a href="{self._RAW_BASE}/pic.jpg"' in result.s
        assert "max-width:280px" in result.s
        assert "cursor:pointer" in result.s

    def test_default_ignores_local_file_thumbnail_stays_remote(self, tmp_path):
        # prefer_local defaults to False -- matches every existing call site
        # (7 already-shipped Odyssey lessons): the thumbnail must stay on the
        # remote URL even when a local copy exists, so those lessons keep
        # HTTP-cacheable thumbnails instead of silently switching to inline
        # base64 blobs on every render.
        img = tmp_path / "pic.png"
        img.write_bytes(b"\x89PNGfake-bytes")
        result = magnify_image(_StubHtmlMo(), img, raw_base=self._RAW_BASE, width=None)
        assert "data:image" not in result.s
        assert result.s.count(f"{self._RAW_BASE}/pic.png") == 2

    def test_prefer_local_reads_local_bytes_click_through_stays_remote(self, tmp_path):
        import base64
        img = tmp_path / "pic.png"
        _bytes = b"\x89PNGfake-bytes"
        img.write_bytes(_bytes)
        result = magnify_image(_StubHtmlMo(), img, raw_base=self._RAW_BASE, width=None, prefer_local=True)
        # click-through link: remote URL, exactly once (never a data-URI --
        # that's the specific thing that breaks inside a sandboxed iframe)
        assert f'<a href="{self._RAW_BASE}/pic.png" target="_blank"' in result.s
        assert result.s.count(f"{self._RAW_BASE}/pic.png") == 1
        # thumbnail: local bytes, base64-encoded, not the remote URL
        _expected_src = f"data:image/png;base64,{base64.b64encode(_bytes).decode('ascii')}"
        assert f'<img src="{_expected_src}"' in result.s

    def test_raw_base_trailing_slash_does_not_double_up(self, tmp_path):
        img = tmp_path / "pic.jpg"
        img.write_bytes(b"fake")
        result = magnify_image(_StubHtmlMo(), img, raw_base=self._RAW_BASE + "/", width=None)
        assert f"{self._RAW_BASE}/pic.jpg" in result.s
        assert "//pic.jpg" not in result.s

    def test_no_width_omits_pixel_max_width(self, tmp_path):
        img = tmp_path / "pic.jpg"
        img.write_bytes(b"fake")
        result = magnify_image(_StubHtmlMo(), img, raw_base=self._RAW_BASE)
        assert "max-width:100%" in result.s


_SAMPLE_LESSONS = [
    {"nb_id": "nb_AAA", "icon": "Α", "greek": "Δίδαγμα α'",
     "label": "Занятие 1", "title": "Алфавит", "desc": "Буквы",
     "index_url": "https://molab.marimo.io/notebooks/nb_IDX/app"},
    {"nb_id": "nb_BBB", "icon": "Β", "greek": "Δίδαγμα β'",
     "label": "Занятие 2", "title": "Ударения", "desc": "Просодия",
     "index_url": "https://molab.marimo.io/notebooks/nb_IDX/app"},
]


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
        _tsv = (
            "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
            "nb_AAA\tΑ\tΔίδαγμα α'\tЗанятие 1\tАлфавит\tБуквы\thttps://example.com/\n"
        )
        with patch("urllib.request.urlopen", return_value=_make_resp(_tsv.encode("utf-8"))):
            cfg = ConfigStore.from_url("https://example.com/index.tsv")
        assert len(cfg.lessons()) == 1
        assert cfg.lessons()[0]["nb_id"] == "nb_AAA"
        assert cfg.index_url() == "https://example.com/"
        assert cfg.ga_config() is None

    def test_from_url_with_ga_dict(self):
        _tsv = "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
        with patch("urllib.request.urlopen", return_value=_make_resp(_tsv.encode("utf-8"))):
            cfg = ConfigStore.from_url("https://example.com/index.tsv", ga=_SAMPLE_GA)
        assert cfg.ga_config() == _SAMPLE_GA

    def test_from_url_with_ga_url(self):
        import json
        _tsv = "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
        _ga_json = json.dumps(_SAMPLE_GA).encode("utf-8")
        with patch("urllib.request.urlopen", side_effect=[
            _make_resp(_tsv.encode("utf-8")),
            _make_resp(_ga_json),
        ]):
            cfg = ConfigStore.from_url(
                "https://example.com/index.tsv",
                ga="https://example.com/ga.json",
            )
        assert cfg.ga_config() == _SAMPLE_GA

    def test_from_url_rewrites_codeberg_urls_before_fetch(self):
        # Both the lessons TSV and the ga= URL must go out via the CORS-safe
        # Codeberg API form, not the plain git-web raw URL, since from_url()
        # is the exact "molab pattern" that also runs under a self-hosted
        # WASM export where CORS is enforced.
        _source_host_base.cache_clear()
        _tsv = "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
        seen_urls = []

        def fake_urlopen(url, timeout=None):
            seen_urls.append(url)
            if "ga.json" in url:
                return _make_resp(json.dumps(_SAMPLE_GA).encode("utf-8"))
            return _make_resp(_tsv.encode("utf-8"))

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            cfg = ConfigStore.from_url(
                "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main/palaestra/index.tsv",
                ga="https://codeberg.org/EEE-project/created_with_eee/raw/branch/main/ga.json",
            )
        assert seen_urls == [
            "https://codeberg.org/api/v1/repos/EEE-project/created_with_eee/raw/palaestra/index.tsv?ref=main",
            "https://codeberg.org/api/v1/repos/EEE-project/created_with_eee/raw/ga.json?ref=main",
        ]
        assert cfg.ga_config() == _SAMPLE_GA
        # raw_base stays on the original git-web form -- it backs the
        # human-facing magnify_image() click-through link, not a fetch.
        assert cfg.raw_base == "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main/palaestra"

    def test_from_file_reads_tsv(self, tmp_path):
        tsv = tmp_path / "index.tsv"
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
        (tmp_path / "index.tsv").write_text(
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
        tsv = tmp_path / "index.tsv"
        tsv.write_text(
            "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
            "nb_AAA\tΑ\t\t\t\t\thttps://example.com/\n",
            encoding="utf-8",
        )
        nb_file = subdir / "notebook.py"
        nb_file.write_text("")
        cfg = ConfigStore.from_file(nb_file)
        assert cfg.index_url() == "https://example.com/"


# ─────────────────────────── GreekUtils.resolve_word_grammar ──

class _SlotStub:
    def __init__(self, tag, features):
        self.tag = tag
        self.features = features
        self.label = tag


class _GrammarBackend:
    def paradigm(self, lemma, pos):
        if lemma == "θεός" and pos == "noun":
            return {".NSM": {"θεός"}, ".GSM": {"θεοῦ"}, ".NPM": {"θεοί"}}
        return {}

    def get_slot_templates(self, lang, pos, terms_lang="en"):
        if pos == "noun":
            return [
                _SlotStub(".NSM", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}),
                _SlotStub(".GSM", {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}),
                _SlotStub(".NPM", {"Case": "Nom", "Number": "Plur", "Gender": "Masc"}),
            ]
        return []


@pytest.fixture
def gu_gram():
    return GreekUtils(mo_module=_StubMo())


class TestResolveWordGrammar:
    def test_known_form_gets_label(self, gu_gram):
        words = [{"form": "θεός", "lemma": "θεός", "pos": "noun", "meaning": "god"}]
        result = gu_gram.resolve_word_grammar(words, _GrammarBackend(), "ru")
        assert result[0]["grammar_label"] == "ед. Им. м."

    def test_unknown_lemma_gets_empty_label(self, gu_gram):
        words = [{"form": "λόγος", "lemma": "λόγος", "pos": "noun", "meaning": "word"}]
        result = gu_gram.resolve_word_grammar(words, _GrammarBackend(), "ru")
        assert result[0]["grammar_label"] == ""

    def test_non_quizzable_pos_gets_empty_label(self, gu_gram):
        words = [{"form": "δέ", "lemma": "δέ", "pos": "particle", "meaning": "and"}]
        result = gu_gram.resolve_word_grammar(words, _GrammarBackend(), "ru")
        assert result[0]["grammar_label"] == ""

    def test_adj_pos_routes_to_adjective(self, gu_gram):
        words = [{"form": "θεός", "lemma": "θεός", "pos": "adj", "meaning": "divine"}]

        class _AdjBackend(_GrammarBackend):
            def paradigm(self, lemma, pos):
                return {"x": {"θεός"}} if pos == "adjective" else {}
            def get_slot_templates(self, lang, pos, terms_lang="en"):
                if pos == "adjective":
                    return [_SlotStub("x", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"})]
                return []

        result = gu_gram.resolve_word_grammar(words, _AdjBackend(), "ru")
        assert result[0]["grammar_label"] == "ед. Им. м."

    def test_original_dicts_not_mutated(self, gu_gram):
        w = {"form": "θεός", "lemma": "θεός", "pos": "noun", "meaning": "god"}
        gu_gram.resolve_word_grammar([w], _GrammarBackend(), "ru")
        assert "grammar_label" not in w

    def test_backend_none_gives_empty_label(self, gu_gram):
        words = [{"form": "θεός", "lemma": "θεός", "pos": "noun", "meaning": "god"}]
        result = gu_gram.resolve_word_grammar(words, None, "ru")
        assert result[0]["grammar_label"] == ""

    def test_missing_lemma_falls_back_to_form(self, gu_gram):
        """Flat-vocab word dicts (load_vocab_tsv) have no lemma key."""
        words = [{"form": "θεός", "pos": "noun", "meaning": "god"}]
        result = gu_gram.resolve_word_grammar(words, _GrammarBackend(), "ru")
        assert result[0]["grammar_label"] == "ед. Им. м."

    def test_pronoun_pos_gets_label(self, gu_gram):
        """pos="pronoun" gets a real, non-empty grammar_label -- previously
        fell through to "" since "pronoun" wasn't in the eee_pos in (...)
        tuple. No _POS translation needed (unlike "adj"->"adjective")
        since the course-TSV pos value and the backend's canonical pos
        string are both "pronoun"."""

        class _PronBackend(_GrammarBackend):
            def paradigm(self, lemma, pos):
                return {"x": {"ἐγώ"}} if pos == "pronoun" else {}
            def get_slot_templates(self, lang, pos, terms_lang="en"):
                if pos == "pronoun":
                    return [_SlotStub("x", {"Case": "Nom", "Number": "Sing", "Person": "1", "PronType": "Prs"})]
                return []

        words = [{"form": "ἐγώ", "lemma": "ἐγώ", "pos": "pronoun", "meaning": "I"}]
        result = gu_gram.resolve_word_grammar(words, _PronBackend(), "ru")
        assert result[0]["grammar_label"] != ""

    def test_pronoun_resolves_correct_prontype_among_colliding_tags(self, gu_gram):
        """Regression guard for a real bug found in section-05's code
        review (2026-07-12): pronoun-tags.tsv legitimately has multiple
        rows sharing the same tag string across pronoun families (e.g.
        .NSM is used by both a demonstrative and a relative pronoun,
        each with a different PronType). A naive first-tag-match loop
        (this method's original implementation) always resolves to
        whichever slot happens to sort first -- here, deliberately
        Dem before Rel, mirroring pronoun-tags.tsv's real row order --
        silently mislabeling the SECOND lemma's PronType. This test
        fails against the naive implementation and must pass against
        the fix."""

        class _CollidingPronBackend(_GrammarBackend):
            def paradigm(self, lemma, pos):
                if pos != "pronoun":
                    return {}
                if lemma == "ὅς":
                    return {".NSM": {"ὅς"}}
                return {}
            def get_slot_templates(self, lang, pos, terms_lang="en"):
                if pos != "pronoun":
                    return []
                # Dem row sorts first, exactly like the real pronoun-tags.tsv --
                # the same tag .NSM is legitimately shared by both families.
                return [
                    _SlotStub(".NSM", {"Case": "Nom", "Number": "Sing", "Gender": "Masc", "PronType": "Dem"}),
                    _SlotStub(".NSM", {"Case": "Nom", "Number": "Sing", "Gender": "Masc", "PronType": "Rel"}),
                ]

        words = [{"form": "ὅς", "lemma": "ὅς", "pos": "pronoun", "meaning": "who"}]
        result = gu_gram.resolve_word_grammar(words, _CollidingPronBackend(), "en")
        assert "rel" in result[0]["grammar_label"].lower(), (
            f"expected the Rel-family PronType label (lemma=ὅς), got {result[0]['grammar_label']!r} "
            "-- if this contains 'dem' instead, the naive first-match-wins bug has regressed"
        )


class TestOdysseyPosConstants:
    """LEXICON_TAG_POS/LEXICON_TAG_POS_ALIASES/TRANSLATION_PRESENCE_CONTENT_POS
    used to be hand-duplicated identically in every Odyssey lesson notebook --
    now real, importable constants so a future POS addition is a one-line
    change instead of a 5-notebook sweep."""

    def test_values(self):
        import eee_project as eee
        assert eee.LEXICON_TAG_POS == {"noun", "verb", "adj", "pronoun"}
        assert eee.LEXICON_TAG_POS_ALIASES == {"adj": "adjective"}
        assert eee.TRANSLATION_PRESENCE_CONTENT_POS == {"noun", "verb", "adj", "adv", "name"}

    def test_lexicon_tag_and_translation_presence_sets_are_independent(self):
        # The two sets must stay genuinely distinct objects -- a past
        # session's stale-kernel save reverted one while editing the other
        # precisely because they look similar but control different things.
        import eee_project as eee
        assert eee.LEXICON_TAG_POS is not eee.TRANSLATION_PRESENCE_CONTENT_POS
        assert eee.LEXICON_TAG_POS != eee.TRANSLATION_PRESENCE_CONTENT_POS


# ──────────────── helpers for slot/word drill and quiz form tests ──────────

class _FakeBtn:
    def __init__(self, value=None, disabled=False, label="", kind="neutral"):
        self.value = value
        self.disabled = disabled
        self.label = label
        self.kind = kind


class _FakeRadio:
    def __init__(self, options=None, value=None, label=""):
        self.options = list(options or [""])
        self.value = value
        self.label = label


class _FakeDiaUI:
    value = {"enter_pressed": 0}


class _FakeWI:
    """Minimal diacritics-text widget stub (write_input)."""
    def __init__(self, val=""):
        self.value = val
        self._ui = _FakeDiaUI()


def _dia(value: str = ""):
    """A bare ``dia_reactive``-shaped stub exposing just the live-typed
    ``"value"`` key -- for :meth:`word_drill_check_button` tests, which
    only ever read ``dia_reactive.value.get("value")``."""
    ui = _FakeDiaUI()
    ui.value = {"value": value}
    return ui


class _FormMo(_StubMoLayout):
    """Extended marimo stub with button/radio support."""
    class Html:
        def __init__(self, s): self.s = s
        def __str__(self): return self.s
        def __repr__(self): return self.s
    class ui:
        @staticmethod
        def button(label="", on_click=None, disabled=False, kind="neutral"):
            return _FakeBtn(value=None, disabled=disabled, label=label, kind=kind)
        @staticmethod
        def radio(options=None, value=None, label=""):
            return _FakeRadio(options, value, label)
        @staticmethod
        def text(placeholder="", full_width=False, value=""):
            return type("_FT", (), {"value": value or ""})()
        @staticmethod
        def switch(value=False):
            return _FakeBtn(value=value)
        @staticmethod
        def dropdown(options=None, value=None, label=""):
            return _FakeDropdown(options, value, label)
        @staticmethod
        def anywidget(inst):
            return inst
    @staticmethod
    def stop(cond, content): raise StopIteration(content)


def _pair(v):
    """Return (getter, setter, box) for a mutable state value."""
    b = [v]
    return lambda: b[0], lambda x: b.__setitem__(0, x), b


def _form_state(cv=None, rem=None, sc=None, rst=None, hist=None, fut=None):
    """Shared cv/remaining/score/restore_entry/history/future state tuple --
    every ``*Form`` test class's own ``_state`` method delegates here."""
    cv_g, cv_s, cv_b = _pair(cv)
    rem_g, rem_s, rem_b = _pair(rem)
    sc_g, sc_s, sc_b = _pair(sc or {"correct": 0, "total": 0})
    rst_g, rst_s, _ = _pair(rst)
    hist_g, hist_s, hist_b = _pair(hist or [])
    fut_g, fut_s, _ = _pair(fut or [])
    return (cv_g, cv_s, cv_b, rem_g, rem_s, rem_b,
            sc_g, sc_s, sc_b, rst_g, rst_s, hist_g, hist_s, hist_b, fut_g, fut_s)


@pytest.fixture
def gu_form():
    return GreekUtils(mo_module=_FormMo())


_WD_VOCAB = [
    {"meaning": "говорить",  "form": "λέγε"},
    {"meaning": "слушать",   "form": "ἄκουε"},
    {"meaning": "писать",    "form": "γράφε"},
    {"meaning": "читать",    "form": "ἀναγίγνωσκε"},
]

_WQ_VOCAB = [
    {"meaning": "говорить", "form": "λέγω",  "lemma": "λέγω",  "context": ""},
    {"meaning": "слушать",  "form": "ἀκούω", "lemma": "ἀκούω", "context": ""},
    {"meaning": "писать",   "form": "γράφω", "lemma": "γράφω", "context": ""},
    {"meaning": "видеть",   "form": "ὁράω",  "lemma": "ὁράω",  "context": ""},
    {"meaning": "нести",    "form": "φέρω",  "lemma": "φέρω",  "context": ""},
]


# ────────────────────────────────────────── word_drill_done ──

class TestWordDrillDone:
    def test_true_when_exhausted(self, gu_form):
        assert gu_form.word_drill_done(None, []) is True

    def test_false_when_cv_present(self, gu_form):
        assert gu_form.word_drill_done({"form": "λύω"}, []) is False

    def test_false_when_remaining_none(self, gu_form):
        assert gu_form.word_drill_done(None, None) is False

    def test_false_when_remaining_nonempty(self, gu_form):
        assert gu_form.word_drill_done(None, [{"form": "λύω"}]) is False


# ────────────────────────────────────────── word_drill_check_button ──

class TestWordDrillCheckButton:
    """Unit tests for GreekUtils.word_drill_check_button — the single-field
    analogue of TestDirtyCheckButton, for word_drill's diacritics-text input."""

    def test_clean_when_no_input(self, gu_form):
        btn = gu_form.word_drill_check_button(_dia(""), None)
        assert btn.kind == "neutral"

    def test_dirty_when_input_never_checked(self, gu_form):
        btn = gu_form.word_drill_check_button(_dia("λέγε"), None)
        assert btn.kind == "warn"

    def test_clean_when_input_matches_last_check(self, gu_form):
        btn = gu_form.word_drill_check_button(_dia("λέγε"), "λέγε")
        assert btn.kind == "neutral"

    def test_dirty_when_input_changed_since_last_check(self, gu_form):
        btn = gu_form.word_drill_check_button(_dia("λέγεις"), "λέγε")
        assert btn.kind == "warn"

    def test_default_label_is_check(self, gu_form):
        btn = gu_form.word_drill_check_button(_dia(""), None)
        assert btn.label == "Check"

    def test_label_can_be_overridden(self, gu_form):
        btn = gu_form.word_drill_check_button(_dia(""), None, label="Проверить")
        assert btn.label == "Проверить"


# ────────────────────────────────────────── word_drill_widgets ──

class TestWordDrillWidgets:
    def test_returns_five_tuple(self, gu_form):
        wi = MagicMock(); wi._ui = MagicMock()
        with patch.object(gu_form, "diacritics_text", return_value=wi):
            result = gu_form.word_drill_widgets(cv={}, remaining=[])
        assert len(result) == 5

    def test_prev_disabled_with_no_history(self, gu_form):
        wi = MagicMock(); wi._ui = MagicMock()
        with patch.object(gu_form, "diacritics_text", return_value=wi):
            _, _, _, prev_btn, _ = gu_form.word_drill_widgets(cv={}, remaining=[], history_len=0)
        assert prev_btn.disabled is True

    def test_prev_enabled_with_history(self, gu_form):
        wi = MagicMock(); wi._ui = MagicMock()
        with patch.object(gu_form, "diacritics_text", return_value=wi):
            _, _, _, prev_btn, _ = gu_form.word_drill_widgets(cv={}, remaining=[], history_len=3)
        assert prev_btn.disabled is False

    def test_label_overrides_check_button_text(self, gu_form):
        wi = MagicMock(); wi._ui = MagicMock()
        with patch.object(gu_form, "diacritics_text", return_value=wi):
            _, _, check_btn, _, _ = gu_form.word_drill_widgets(cv={}, remaining=[], label="Check")
        assert check_btn.label == "Check"

    def test_lang_en_changes_nav_button_labels(self, gu_form):
        wi = MagicMock(); wi._ui = MagicMock()
        with patch.object(gu_form, "diacritics_text", return_value=wi):
            _, _, _, prev_btn, next_btn = gu_form.word_drill_widgets(cv={}, remaining=[], lang="en")
        assert next_btn.label == "Next"
        assert prev_btn.label == "Prev"

    def test_done_true_when_cv_none_and_remaining_empty(self, gu_form):
        wi = MagicMock(); wi._ui = MagicMock()
        with patch.object(gu_form, "diacritics_text", return_value=wi):
            _, _, _, _, next_btn = gu_form.word_drill_widgets(cv=None, remaining=[])
        assert next_btn.label == "Пройти снова"

    def test_done_false_when_cv_present(self, gu_form):
        wi = MagicMock(); wi._ui = MagicMock()
        with patch.object(gu_form, "diacritics_text", return_value=wi):
            _, _, _, _, next_btn = gu_form.word_drill_widgets(cv={"form": "λύω"}, remaining=[])
        assert next_btn.label == "Следующий"

    def test_nav_icons_true_uses_triangle_labels(self, gu_form):
        # Triangle decorates the localized text, doesn't replace it --
        # arrow points in the direction of travel (before Prev, after Next).
        wi = MagicMock(); wi._ui = MagicMock()
        with patch.object(gu_form, "diacritics_text", return_value=wi):
            _, _, _, prev_btn, next_btn = gu_form.word_drill_widgets(cv={}, remaining=[], nav_icons=True)
        assert prev_btn.label == "◀ Предыдущий"
        assert next_btn.label == "Следующий ▶"

    def test_nav_icons_true_done_uses_restart_glyph(self, gu_form):
        # cv=None, remaining=[] -> word_drill_done() is True -- the restart
        # action must not look identical to "skip forward" (▶ next to a
        # "press «Again»" done-screen callout would visually contradict it).
        # Icon before text here, matching make_renew_button's own convention.
        wi = MagicMock(); wi._ui = MagicMock()
        with patch.object(gu_form, "diacritics_text", return_value=wi):
            _, _, _, _, next_btn = gu_form.word_drill_widgets(cv=None, remaining=[], nav_icons=True)
        assert next_btn.label == "↺ Пройти снова"

    def test_config_nav_icons_true_used_with_no_explicit_kwarg(self):
        gu = GreekUtils(mo_module=_FormMo(), config=_NAV_ICONS_CONFIG)
        wi = MagicMock(); wi._ui = MagicMock()
        with patch.object(gu, "diacritics_text", return_value=wi):
            _, _, _, prev_btn, next_btn = gu.word_drill_widgets(cv={}, remaining=[])
        assert prev_btn.label == "◀ Предыдущий"
        assert next_btn.label == "Следующий ▶"


# ────────────────────────────────────────── make_renew_button ──

class TestMakeRenewButton:
    def test_returns_renew_button(self, gu_form):
        btn = gu_form.make_renew_button()
        assert btn.label == "↺ Новый набор"

    def test_lang_en(self, gu_form):
        btn = gu_form.make_renew_button(lang="en")
        assert btn.label == "↺ New set"

    def test_lang_el(self, gu_form):
        btn = gu_form.make_renew_button(lang="el")
        assert btn.label == "↺ Νέα επιλογή"


class TestIconNavRow:
    """Unit tests for GreekUtils._icon_nav_row -- the nav_icons=True button
    row builder shared by word_drill_display, word_quiz_form, and
    _paradigm_drill_form (previously three near-identical inline copies)."""

    def test_prev_first_next_last_both_enabled(self, gu_form):
        prev, mid, next_ = object(), object(), object()
        row = gu_form._icon_nav_row(prev, next_, mid, prev_disabled=False)
        assert row == [prev, mid, next_]

    def test_prev_hidden_when_disabled(self, gu_form):
        prev, mid, next_ = object(), object(), object()
        row = gu_form._icon_nav_row(prev, next_, mid, prev_disabled=True)
        assert row == [mid, next_]

    def test_multiple_middle_widgets_all_kept_in_order(self, gu_form):
        prev, next_, m1, m2 = object(), object(), object(), object()
        row = gu_form._icon_nav_row(prev, next_, m1, m2, prev_disabled=False)
        assert row == [prev, m1, m2, next_]

    def test_none_middle_widget_dropped(self, gu_form):
        # e.g. word_quiz_form passing an unused renew_btn=None straight through
        prev, next_ = object(), object()
        row = gu_form._icon_nav_row(prev, next_, None, prev_disabled=False)
        assert row == [prev, next_]

    def test_no_middle_widgets(self, gu_form):
        prev, next_ = object(), object()
        row = gu_form._icon_nav_row(prev, next_, prev_disabled=False)
        assert row == [prev, next_]


class TestIctusTogglePanel:
    def test_wires_switches_and_ictus_color(self, gu_form):
        show_ictus = object()
        show_homer = object()
        panel = gu_form.ictus_toggle_panel(
            show_ictus, show_homer, "note text",
            ictus_color="green", ictus_color_name="зелёным",
        )
        assert panel[0][0] is show_ictus
        assert panel[1][0] is show_homer
        assert "color:green" in panel[0][1]
        assert "зелёным" in panel[0][1]

    def test_passes_eee_note_to_accordion(self, gu_form):
        panel = gu_form.ictus_toggle_panel(
            object(), object(), "the note text",
            ictus_color="#980000", ictus_color_name="красным",
        )
        assert panel[2] == {"О морфологическом движке EEE": "the note text"}

    def test_lang_en_translates_note_text_but_keeps_caller_color_name(self, gu_form):
        panel = gu_form.ictus_toggle_panel(
            object(), object(), "the note text",
            ictus_color="green", ictus_color_name="green", lang="en",
        )
        assert "Ictus (stressed syllables)" in panel[0][1]
        assert "Homeric lexicon" in panel[1][1]
        assert panel[2] == {"About the EEE morphological engine": "the note text"}


class TestRenderGlossPanel:
    def test_no_selection_shows_placeholder(self, gu_form):
        panel = gu_form.render_gloss_panel(
            [{"form": "x", "lemma": "x"}], "not-there", lambda w: "",
        )
        assert "Выберите слово" in panel

    def test_no_selection_shows_placeholder_lang_en(self, gu_form):
        panel = gu_form.render_gloss_panel(
            [{"form": "x", "lemma": "x"}], "not-there", lambda w: "", lang="en",
        )
        assert "Select a word" in panel
        assert "Выберите" not in panel

    def test_selected_word_without_lexicon_tables(self, gu_form):
        words = [{"form": "λόγος", "lemma": "λόγος", "context": "word", "meaning": "word/reason"}]
        panel = gu_form.render_gloss_panel(words, "λόγος", lambda w: "")
        assert "λόγος" in panel
        assert "word/reason" in panel

    def test_grammar_label_becomes_an_italic_second_line(self, gu_form):
        words = [{"form": "λόγος", "lemma": "λόγος", "context": "word", "meaning": "word/reason",
                  "grammar_label": "ед. Им. м."}]
        panel = gu_form.render_gloss_panel(words, "λόγος", lambda w: "")
        assert "  \n_ед. Им. м._" in panel

    def test_no_grammar_label_adds_no_second_line(self, gu_form):
        words = [{"form": "λόγος", "lemma": "λόγος", "context": "word", "meaning": "word/reason"}]
        panel = gu_form.render_gloss_panel(words, "λόγος", lambda w: "")
        assert "\n" not in panel

    def test_selected_word_with_lexicon_tables(self, gu_form):
        words = [{"form": "λόγος", "lemma": "λόγος", "context": "word", "meaning": "word/reason"}]
        panel = gu_form.render_gloss_panel(words, "λόγος", lambda w: "<table>...</table>")
        assert "λόγος" in panel[0]
        assert "word/reason" in panel[0]
        assert "Формы слова по эпохам" in panel[1]
        assert str(panel[2]) == "<table>...</table>"


class TestRenderGlossSelector:
    """render_gloss_selector -- Cell 1 of the real-dropdown gloss panel
    (see build_grc_period_tables); pairs with TestRenderGlossTable below."""

    def test_no_selection_returns_none_state_and_placeholder_panel(self, gu_form):
        tables, selector, panel = gu_form.render_gloss_selector(
            [{"form": "x", "lemma": "x"}], "not-there", lambda w: None,
        )
        assert (tables, selector) == (None, None)
        assert "Выберите слово" in panel

    def test_no_selection_placeholder_lang_en(self, gu_form):
        _, _, panel = gu_form.render_gloss_selector(
            [{"form": "x", "lemma": "x"}], "not-there", lambda w: None, lang="en",
        )
        assert "Select a word" in panel
        assert "Выберите" not in panel

    def test_word_with_no_tables_returns_none_selector_and_tables(self, gu_form):
        words = [{"form": "λόγος", "lemma": "λόγος", "context": "word", "meaning": "word/reason"}]
        tables, selector, panel = gu_form.render_gloss_selector(words, "λόγος", lambda w: None)
        assert selector is None
        assert tables is None
        assert "λόγος" in panel[0]

    def test_word_with_one_table_builds_no_selector(self, gu_form):
        # a single period needs no picker at all
        words = [{"form": "λόγος", "lemma": "λόγος", "context": "word", "meaning": "word/reason"}]
        tables, selector, _ = gu_form.render_gloss_selector(
            words, "λόγος", lambda w: [("homer", "<table>H</table>")],
        )
        assert selector is None
        assert tables == [("homer", "<table>H</table>")]

    def test_word_with_multiple_tables_builds_dropdown_defaulting_to_first(self, gu_form):
        words = [{"form": "λόγος", "lemma": "λόγος", "context": "word", "meaning": "word/reason"}]
        tables, selector, panel = gu_form.render_gloss_selector(
            words, "λόγος",
            lambda w: [("homer", "<table>H</table>"), ("lsj", "<table>A</table>")],
        )
        assert selector is not None
        assert selector.value == "homer"
        assert len(tables) == 2
        assert selector in panel  # the dropdown itself is part of the displayed panel

    def test_dropdown_label_from_ui_label(self, gu_form):
        words = [{"form": "λόγος", "lemma": "λόγος", "context": "word", "meaning": "word/reason"}]
        _, selector, _ = gu_form.render_gloss_selector(
            words, "λόγος",
            lambda w: [("homer", "<t>H</t>"), ("lsj", "<t>A</t>")],
            lang="en",
        )
        assert selector.label == "Period"


class TestRenderGlossTable:
    """render_gloss_table -- Cell 2 of the real-dropdown gloss panel; must
    be called from a cell taking period_selector as its own parameter, see
    the method's own docstring."""

    def test_no_tables_renders_nothing(self, gu_form):
        assert gu_form.render_gloss_table(None, None) is None

    def test_renders_the_selected_period(self, gu_form):
        tables = [("homer", "<table>HOMER</table>"), ("lsj", "<table>LSJ</table>")]
        selector = _FakeDropdown(options={"Attic": "lsj"}, value="Attic")
        html = str(gu_form.render_gloss_table(tables, selector))
        assert "LSJ" in html and "HOMER" not in html

    def test_no_selector_falls_back_to_first_period(self, gu_form):
        tables = [("homer", "<table>HOMER</table>")]
        html = str(gu_form.render_gloss_table(tables, None))
        assert "HOMER" in html


class TestResetQuizState:
    def test_resets_all_six_setters(self, gu_form):
        _, set_cv, cv_b = _pair("stale")
        _, set_remaining, rem_b = _pair(["stale"])
        _, set_score, sc_b = _pair({"correct": 5, "total": 5})
        _, set_history, hist_b = _pair(["stale"])
        _, set_future, fut_b = _pair(["stale"])
        _, set_restore_entry, rst_b = _pair("stale")

        gu_form.reset_quiz_state(_FakeBtn(value=1), set_cv, set_remaining,
                                  set_score, set_history, set_future, set_restore_entry)

        assert cv_b[0] is None
        assert rem_b[0] is None
        assert sc_b[0] == {"correct": 0, "total": 0}
        assert hist_b[0] == []
        assert fut_b[0] == []
        assert rst_b[0] is None

    def test_reads_renew_btn_value_without_raising(self, gu_form):
        # No assertion on the read itself -- just that a button-shaped
        # object without a .value would blow up loudly, not silently.
        _, set_cv, _ = _pair(None)
        _, set_remaining, _ = _pair(None)
        _, set_score, _ = _pair(None)
        _, set_history, _ = _pair(None)
        _, set_future, _ = _pair(None)
        _, set_restore_entry, _ = _pair(None)
        gu_form.reset_quiz_state(_FakeBtn(value=3), set_cv, set_remaining,
                                  set_score, set_history, set_future, set_restore_entry)


# ────────────────────────────────────────── word_drill_form ──

class TestWordDrillWidgetsLangDefaults:
    def test_check_label_defaults_per_lang(self, gu_form):
        _, _, check_btn, _, _ = gu_form.word_drill_widgets(cv={}, remaining=[], lang="en")
        assert check_btn.label == "Check"

    def test_default_lang_stays_russian(self, gu_form):
        _, _, check_btn, _, _ = gu_form.word_drill_widgets(cv={}, remaining=[])
        assert check_btn.label == "Проверить"


class TestWordDrillForm:
    def _state(self, cv=None, rem=None, sc=None, rst=None, hist=None, fut=None):
        cv_g, cv_s, cv_b = _pair(cv)
        rem_g, rem_s, rem_b = _pair(rem)
        sc_g, sc_s, sc_b = _pair(sc or {"correct": 0, "total": 0})
        rst_g, rst_s, _ = _pair(rst)
        hist_g, hist_s, _ = _pair(hist or [])
        fut_g, fut_s, _ = _pair(fut or [])
        return (cv_g, cv_s, cv_b, rem_g, rem_s, rem_b,
                sc_g, sc_s, sc_b, rst_g, rst_s, hist_g, hist_s, fut_g, fut_s)

    def _call(self, gu, state, wi=None, next_v=None, prev_v=None, check_v=None, vocab=None, lang="ru",
              get_checked=None, set_checked=None, nav_icons=False):
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, fut_g, fut_s = state
        wi = wi or _FakeWI()
        return gu.word_drill_form(
            cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
            hist_g, hist_s, fut_g, fut_s,
            wi, wi._ui, _FakeBtn(check_v), _FakeBtn(prev_v), _FakeBtn(next_v),
            vocab=vocab or _WD_VOCAB,
            lang=lang,
            get_checked=get_checked, set_checked=set_checked, nav_icons=nav_icons,
        )

    def test_uninit_initializes_and_returns_placeholder(self, gu_form):
        state = self._state(rem=None)
        cv_b = state[2]; rem_b = state[5]
        result = self._call(gu_form, state)
        assert result == "*...*"
        assert cv_b[0] is not None
        assert rem_b[0] is not None

    def test_display_shows_meaning(self, gu_form):
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        result = self._call(gu_form, state)
        assert "говорить" in " ".join(str(x) for x in result)

    def test_next_advances_and_returns_placeholder(self, gu_form):
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        result = self._call(gu_form, state, next_v=1)
        assert result == "*...*"

    def test_next_scores_correct_answer(self, gu_form):
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        sc_b = state[8]
        self._call(gu_form, state, wi=_FakeWI(_WD_VOCAB[0]["form"]), next_v=1)
        assert sc_b[0]["correct"] == 1
        assert sc_b[0]["total"] == 1

    # Check-button auto-advance: mirrors _paradigm_drill_form's "correct ->
    # immediately advance, no separate Next click needed" behavior.

    def test_check_correct_auto_advances(self, gu_form):
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        cv_b = state[2]; rem_b = state[5]; sc_b = state[8]
        result = self._call(gu_form, state, wi=_FakeWI(_WD_VOCAB[0]["form"]), check_v=1)
        assert result == "*...*"
        assert cv_b[0] == _WD_VOCAB[1]
        assert rem_b[0] == _WD_VOCAB[2:]
        assert sc_b[0] == {"correct": 1, "total": 1}

    def test_enter_correct_auto_advances(self, gu_form):
        # Enter must advance exactly like the Check button -- verified this
        # can't double-fire even though enter_pressed never auto-resets
        # (see the long comment at the fix site for why: write_input
        # rebuilds empty on the very re-run this triggers, before this
        # code ever re-reads the stale enter_pressed count).
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        cv_b = state[2]; rem_b = state[5]; sc_b = state[8]
        wi = _FakeWI(_WD_VOCAB[0]["form"])
        wi._ui.value = {"enter_pressed": 1}
        result = self._call(gu_form, state, wi=wi, check_v=None)
        assert result == "*...*"
        assert cv_b[0] == _WD_VOCAB[1]
        assert rem_b[0] == _WD_VOCAB[2:]
        assert sc_b[0] == {"correct": 1, "total": 1}

    def test_enter_with_zero_count_does_not_advance(self, gu_form):
        # enter_pressed=0 (the default -- Enter never actually pressed)
        # must not be treated as truthy the way a real press (nonzero) is.
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        cv_b = state[2]
        self._call(gu_form, state, wi=_FakeWI(_WD_VOCAB[0]["form"]), check_v=None)
        assert cv_b[0] == _WD_VOCAB[0]

    def test_check_wrong_does_not_advance(self, gu_form):
        # Falls through to word_drill_display instead -- same "stay on this
        # word, show feedback" behavior as before this fix, unchanged.
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        cv_b = state[2]; sc_b = state[8]
        result = self._call(gu_form, state, wi=_FakeWI("wrong answer"), check_v=1)
        assert result != "*...*"
        assert cv_b[0] == _WD_VOCAB[0]
        assert sc_b[0] == {"correct": 0, "total": 0}

    def test_check_empty_input_does_not_advance(self, gu_form):
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        cv_b = state[2]
        result = self._call(gu_form, state, wi=_FakeWI(""), check_v=1)
        assert result != "*...*"
        assert cv_b[0] == _WD_VOCAB[0]

    def test_check_correct_records_history(self, gu_form):
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        hist_b = [None]
        orig_hist_s = state[12]
        def _capture(v): hist_b[0] = v; orig_hist_s(v)
        state = state[:12] + (_capture,) + state[13:]
        self._call(gu_form, state, wi=_FakeWI(_WD_VOCAB[0]["form"]), check_v=1)
        assert hist_b[0] == [{"word": _WD_VOCAB[0], "answer": _WD_VOCAB[0]["form"], "correct": True}]

    def test_check_correct_ignored_while_browsing_future(self, gu_form):
        # Matches the Next-button's own "future" branch being a distinct
        # code path from a normal new answer -- Check shouldn't auto-advance
        # past whatever's being reviewed via Prev/Next history navigation.
        fut_entry = {"word": _WD_VOCAB[1], "answer": _WD_VOCAB[1]["form"], "correct": True}
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[2:], fut=[fut_entry])
        cv_b = state[2]
        result = self._call(gu_form, state, wi=_FakeWI(_WD_VOCAB[0]["form"]), check_v=1)
        assert result != "*...*"
        assert cv_b[0] == _WD_VOCAB[0]

    def test_check_without_click_does_not_advance(self, gu_form):
        # check_v=None (the default) -- typing alone, with no Check click,
        # must not auto-advance.
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        cv_b = state[2]
        self._call(gu_form, state, wi=_FakeWI(_WD_VOCAB[0]["form"]))
        assert cv_b[0] == _WD_VOCAB[0]

    def test_done_shows_callout(self, gu_form):
        state = self._state(cv=None, rem=[], sc={"correct": 2, "total": 4})
        with pytest.raises(StopIteration) as exc_info:
            self._call(gu_form, state)
        assert "callout" in str(exc_info.value.args[0])

    def test_prev_goes_back(self, gu_form):
        past = {"word": _WD_VOCAB[1], "answer": _WD_VOCAB[1]["form"], "correct": True}
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[2:],
                            sc={"correct": 1, "total": 1}, hist=[past])
        cv_b = state[2]; sc_b = state[8]
        result = self._call(gu_form, state, prev_v=1)
        assert result == "*...*"
        assert cv_b[0] == _WD_VOCAB[1]
        assert sc_b[0]["total"] == 0

    def test_prev_stores_answer_key_in_history(self, gu_form):
        # Verify history entries use "answer" key (unified with word_quiz_form).
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        hist_b = [None]
        orig_hist_s = state[12]
        def _capture(v): hist_b[0] = v; orig_hist_s(v)
        state = state[:12] + (_capture,) + state[13:]
        self._call(gu_form, state, wi=_FakeWI(_WD_VOCAB[0]["form"]), next_v=1)
        assert hist_b[0] is not None
        assert "answer" in hist_b[0][0]
        assert "typed" not in hist_b[0][0]

    def test_next_restart_after_done(self, gu_form):
        state = self._state(cv=None, rem=[], sc={"correct": 2, "total": 4})
        cv_b = state[2]; sc_b = state[8]
        result = self._call(gu_form, state, next_v=1)
        assert result == "*...*"
        assert cv_b[0] is not None
        assert sc_b[0]["total"] == 0

    def test_next_forward_through_future(self, gu_form):
        fut_entry = {"word": _WD_VOCAB[1], "answer": _WD_VOCAB[1]["form"], "correct": True}
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[2:],
                            sc={"correct": 0, "total": 0}, fut=[fut_entry])
        cv_b = state[2]
        result = self._call(gu_form, state, next_v=1)
        assert result == "*...*"
        assert cv_b[0] == _WD_VOCAB[1]

    def test_feedback_md_correct(self, gu_form):
        mo = _FormMo()
        result = gu_form._feedback_md(mo, True, "говорить", "λέγε")
        assert "✓" in str(result)
        assert "#2d9e2d" in str(result)

    def test_feedback_md_wrong(self, gu_form):
        mo = _FormMo()
        result = gu_form._feedback_md(mo, False, "говорить", "λέγε")
        assert "✗" in str(result)
        assert "#d32f2f" in str(result)

    def test_lang_en_changes_progress_label(self, gu_form):
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        result = self._call(gu_form, state, lang="en")
        text = " ".join(str(x) for x in result)
        assert "correct" in text
        assert "правильно" not in text

    def test_nav_icons_forwarded_to_display(self, gu_form):
        # No history -- word_drill_form computes prev_disabled=True itself
        # (a real check_btn/prev_btn has no readable .disabled to read back),
        # so nav_icons hides Prev: 2 buttons, not 3.
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        result = self._call(gu_form, state, nav_icons=True)
        assert len(result[-1]) == 2

    def test_nav_icons_shows_prev_with_history(self, gu_form):
        past = {"word": _WD_VOCAB[1], "answer": _WD_VOCAB[1]["form"], "correct": True}
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[2:], hist=[past])
        result = self._call(gu_form, state, nav_icons=True)
        assert len(result[-1]) == 3

    def test_config_nav_icons_true_used_with_no_explicit_kwarg(self):
        # Same repro as test_nav_icons_forwarded_to_display, but nav_icons is
        # never passed at all -- proves the resolve-from-config path, not
        # just that an explicit True still works.
        gu = GreekUtils(mo_module=_FormMo(), config=_NAV_ICONS_CONFIG)
        cv_g, cv_s, _ = _pair(_WD_VOCAB[0])
        rem_g, rem_s, _ = _pair(_WD_VOCAB[1:])
        sc_g, sc_s, _ = _pair({"correct": 0, "total": 0})
        rst_g, rst_s, _ = _pair(None)
        hist_g, hist_s, _ = _pair([])
        fut_g, fut_s, _ = _pair([])
        wi = _FakeWI()
        result = gu.word_drill_form(
            cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
            hist_g, hist_s, fut_g, fut_s,
            wi, wi._ui, _FakeBtn(None), _FakeBtn(None), _FakeBtn(None),
            vocab=_WD_VOCAB,
        )
        assert len(result[-1]) == 2

    # get_checked/set_checked: tracks the exact text last submitted via
    # Check/Enter for the current word, for word_drill_check_button's
    # "warn"-when-dirty coloring -- mirrors _paradigm_drill_form's own
    # "cap" snapshot, updated on every check attempt (right or wrong),
    # reset/restored in lockstep with restore_entry at every transition.

    def test_checked_records_wrong_attempt(self, gu_form):
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        chk_g, chk_s, chk_b = _pair(None)
        self._call(gu_form, state, wi=_FakeWI("wrong answer"), check_v=1,
                   get_checked=chk_g, set_checked=chk_s)
        assert chk_b[0] == "wrong answer"

    def test_checked_resets_on_correct_auto_advance(self, gu_form):
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        chk_g, chk_s, chk_b = _pair("stale")
        self._call(gu_form, state, wi=_FakeWI(_WD_VOCAB[0]["form"]), check_v=1,
                   get_checked=chk_g, set_checked=chk_s)
        assert chk_b[0] is None

    def test_checked_resets_on_next_normal_advance(self, gu_form):
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        chk_g, chk_s, chk_b = _pair("stale")
        self._call(gu_form, state, wi=_FakeWI("wrong"), next_v=1,
                   get_checked=chk_g, set_checked=chk_s)
        assert chk_b[0] is None

    def test_checked_resets_on_restart(self, gu_form):
        state = self._state(cv=None, rem=[], sc={"correct": 2, "total": 4})
        chk_g, chk_s, chk_b = _pair("stale")
        self._call(gu_form, state, next_v=1, get_checked=chk_g, set_checked=chk_s)
        assert chk_b[0] is None

    def test_checked_restored_on_next_forward_through_future(self, gu_form):
        fut_entry = {"word": _WD_VOCAB[1], "answer": _WD_VOCAB[1]["form"], "correct": True}
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[2:],
                            sc={"correct": 0, "total": 0}, fut=[fut_entry])
        chk_g, chk_s, chk_b = _pair("stale")
        self._call(gu_form, state, next_v=1, get_checked=chk_g, set_checked=chk_s)
        assert chk_b[0] == _WD_VOCAB[1]["form"]

    def test_checked_restored_on_prev(self, gu_form):
        past = {"word": _WD_VOCAB[1], "answer": _WD_VOCAB[1]["form"], "correct": True}
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[2:],
                            sc={"correct": 1, "total": 1}, hist=[past])
        chk_g, chk_s, chk_b = _pair(None)
        self._call(gu_form, state, prev_v=1, get_checked=chk_g, set_checked=chk_s)
        assert chk_b[0] == _WD_VOCAB[1]["form"]

    def test_checked_untouched_when_not_wired(self, gu_form):
        # get_checked/set_checked both default None -- existing callers
        # (Odyssey) unaffected, no crash from the optional bookkeeping.
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        result = self._call(gu_form, state, wi=_FakeWI(_WD_VOCAB[0]["form"]), check_v=1)
        assert result == "*...*"

    def test_wrong_check_shows_feedback_with_checked_wired(self, gu_form):
        # Regression test: a check_btn built via word_drill_check_button
        # rebuilds (and its own transient click value resets) the moment
        # set_checked's state update lands, which would otherwise erase the
        # click signal before word_drill_display ever shows feedback for a
        # wrong answer. Confirmed missing live before word_drill_display's
        # own `checked` parameter was added to cover this exact case.
        state = self._state(cv=_WD_VOCAB[0], rem=_WD_VOCAB[1:])
        chk_g, chk_s, _ = _pair(None)
        result = self._call(gu_form, state, wi=_FakeWI("wrong answer"), check_v=1,
                            get_checked=chk_g, set_checked=chk_s)
        assert "✗" in str(result)


# ────────────────────────────────────────── word_quiz_widgets ──

class TestWordQuizWidgets:
    def test_no_cv_placeholder_radio(self, gu_form):
        radio, _, _ = gu_form.word_quiz_widgets(cv=None, remaining=[], vocab=_WQ_VOCAB)
        assert radio.options == [""]

    def test_cv_gives_multiple_options(self, gu_form):
        radio, _, _ = gu_form.word_quiz_widgets(cv=_WQ_VOCAB[0], remaining=_WQ_VOCAB[1:], vocab=_WQ_VOCAB)
        assert len(radio.options) > 1

    def test_done_flag_changes_next_label(self, gu_form):
        _, next_btn, _ = gu_form.word_quiz_widgets(cv=None, remaining=[], vocab=_WQ_VOCAB)
        assert "снова" in next_btn.label

    def test_lang_en_changes_button_and_radio_labels(self, gu_form):
        radio, next_btn, prev_btn = gu_form.word_quiz_widgets(
            cv=_WQ_VOCAB[0], remaining=_WQ_VOCAB[1:], vocab=_WQ_VOCAB, lang="en"
        )
        assert next_btn.label == "Next"
        assert prev_btn.label == "Prev"
        assert "Form in text:" in radio.label

    def test_prev_disabled_when_no_history(self, gu_form):
        _, _, prev_btn = gu_form.word_quiz_widgets(cv=None, remaining=_WQ_VOCAB, vocab=_WQ_VOCAB, history_len=0)
        assert prev_btn.disabled is True

    def test_restore_entry_sets_radio_value(self, gu_form):
        w = _WQ_VOCAB[0]
        radio, _, _ = gu_form.word_quiz_widgets(
            cv=w, remaining=_WQ_VOCAB[1:], vocab=_WQ_VOCAB,
            restore_entry={"answer": w["form"], "correct": True},
        )
        assert radio.value == w["form"]

    def test_nav_icons_true_uses_triangle_labels(self, gu_form):
        _, next_btn, prev_btn = gu_form.word_quiz_widgets(
            cv=_WQ_VOCAB[0], remaining=_WQ_VOCAB[1:], vocab=_WQ_VOCAB, nav_icons=True,
        )
        assert next_btn.label == "Следующий ▶"
        assert prev_btn.label == "◀ Предыдущий"

    def test_nav_icons_true_done_uses_restart_glyph(self, gu_form):
        _, next_btn, _ = gu_form.word_quiz_widgets(
            cv=None, remaining=[], vocab=_WQ_VOCAB, nav_icons=True,
        )
        assert next_btn.label == "↺ Пройти снова"

    def test_config_nav_icons_true_used_with_no_explicit_kwarg(self):
        gu = GreekUtils(mo_module=_FormMo(), config=_NAV_ICONS_CONFIG)
        _, next_btn, prev_btn = gu.word_quiz_widgets(
            cv=_WQ_VOCAB[0], remaining=_WQ_VOCAB[1:], vocab=_WQ_VOCAB,
        )
        assert next_btn.label == "Следующий ▶"
        assert prev_btn.label == "◀ Предыдущий"


# ────────────────────────────────────────── word_quiz_form ──

class TestWordQuizForm:
    def _state(self, cv=None, rem=None, sc=None, rst=None, hist=None, fut=None):
        return _form_state(cv, rem, sc, rst, hist, fut)

    def _call(self, gu, state, radio=None, next_v=None, prev_v=None, vocab=None,
              build_paradigm_table=None, lang="ru", renew_btn=None, nav_icons=False):
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, _, fut_g, fut_s = state
        return gu.word_quiz_form(
            cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
            hist_g, hist_s, fut_g, fut_s,
            radio or _FakeRadio(), _FakeBtn(next_v), _FakeBtn(prev_v),
            vocab=vocab or _WQ_VOCAB,
            build_paradigm_table=build_paradigm_table,
            lang=lang,
            renew_btn=renew_btn,
            nav_icons=nav_icons,
        )

    def test_uninit_initializes(self, gu_form):
        state = self._state(rem=None)
        cv_b = state[2]; rem_b = state[5]
        result = self._call(gu_form, state)
        assert result == "*...*"
        assert cv_b[0] is not None
        assert rem_b[0] is not None

    def test_next_with_answer_advances(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        sc_b = state[8]
        result = self._call(gu_form, state, radio=_FakeRadio(value=w["form"]), next_v=1)
        assert result == "*...*"
        assert sc_b[0]["total"] == 1

    def test_next_without_answer_advances_scored_wrong(self, gu_form):
        # Matches word_drill_form's own blank-submit skip -- Next always
        # advances, an empty/no selection just can't be correct.
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        cv_b = state[2]; sc_b = state[8]
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1)
        assert result == "*...*"
        assert cv_b[0] == _WQ_VOCAB[1]
        assert sc_b[0] == {"correct": 0, "total": 1}

    def test_next_without_answer_records_none_in_history(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        hist_b = state[13]
        self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1)
        assert hist_b[0] == [{"word": w, "answer": None, "correct": False}]

    def test_renew_btn_included_in_nav_row(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        renew = _FakeBtn(label="renew")
        result = self._call(gu_form, state, renew_btn=renew)
        assert renew in result[-1]

    def test_nav_icons_keeps_next_last_with_renew_btn(self, gu_form):
        # renew_btn must not push Next out of the last slot in icon mode --
        # Prev/Next stay first/last regardless of what else is in the row
        # (the default, non-icon row keeps renew_btn last -- see
        # test_renew_btn_included_in_nav_row -- this is opt-in reordering).
        past = {"word": _WQ_VOCAB[1], "answer": _WQ_VOCAB[1]["form"], "correct": True}
        state = self._state(cv=_WQ_VOCAB[0], rem=_WQ_VOCAB[2:], hist=[past])
        renew = _FakeBtn(label="renew")
        result = self._call(gu_form, state, renew_btn=renew, nav_icons=True)
        row = result[-1]
        assert len(row) == 3
        assert row[1] is renew

    def test_no_renew_btn_omitted_from_nav_row(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        result = self._call(gu_form, state)
        assert len(result[-1]) == 2

    def test_nav_icons_hides_prev_with_no_history(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])  # hist defaults to []
        result = self._call(gu_form, state, nav_icons=True)
        assert len(result[-1]) == 1

    def test_nav_icons_shows_prev_with_history(self, gu_form):
        past = {"word": _WQ_VOCAB[1], "answer": _WQ_VOCAB[1]["form"], "correct": True}
        state = self._state(cv=_WQ_VOCAB[0], rem=_WQ_VOCAB[2:], hist=[past])
        result = self._call(gu_form, state, nav_icons=True)
        assert len(result[-1]) == 2

    def test_config_nav_icons_true_used_with_no_explicit_kwarg(self):
        gu = GreekUtils(mo_module=_FormMo(), config=_NAV_ICONS_CONFIG)
        w = _WQ_VOCAB[0]
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, _, fut_g, fut_s = \
            self._state(cv=w, rem=_WQ_VOCAB[1:])
        result = gu.word_quiz_form(
            cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
            hist_g, hist_s, fut_g, fut_s,
            _FakeRadio(), _FakeBtn(None), _FakeBtn(None),
            vocab=_WQ_VOCAB,
        )
        assert len(result[-1]) == 1

    def test_nav_icons_false_keeps_prev_visible_with_no_history(self, gu_form):
        # Default -- Prev stays visible-but-greyed (real marimo disables it
        # via the button's own disabled arg), same as before this feature.
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        result = self._call(gu_form, state)
        assert len(result[-1]) == 2

    def test_done_shows_callout(self, gu_form):
        state = self._state(cv=None, rem=[], sc={"correct": 3, "total": 5})
        with pytest.raises(StopIteration) as exc_info:
            self._call(gu_form, state)
        assert "callout" in str(exc_info.value.args[0])

    def test_prev_goes_back(self, gu_form):
        past = {"word": _WQ_VOCAB[1], "answer": _WQ_VOCAB[1]["form"], "correct": True}
        state = self._state(cv=_WQ_VOCAB[0], rem=_WQ_VOCAB[2:],
                            sc={"correct": 1, "total": 1}, hist=[past])
        cv_b = state[2]; sc_b = state[8]; hist_b = state[13]
        result = self._call(gu_form, state, prev_v=1)
        assert result == "*...*"
        assert cv_b[0] == _WQ_VOCAB[1]
        assert sc_b[0]["total"] == 0
        assert hist_b[0] == []

    def test_next_restart_after_done(self, gu_form):
        state = self._state(cv=None, rem=[], sc={"correct": 3, "total": 5})
        cv_b = state[2]; sc_b = state[8]
        result = self._call(gu_form, state, next_v=1)
        assert result == "*...*"
        assert cv_b[0] is not None
        assert sc_b[0]["total"] == 0

    def test_next_forward_through_future(self, gu_form):
        fut_entry = {"word": _WQ_VOCAB[1], "answer": _WQ_VOCAB[1]["form"], "correct": True}
        state = self._state(cv=_WQ_VOCAB[0], rem=_WQ_VOCAB[2:],
                            sc={"correct": 0, "total": 0}, fut=[fut_entry])
        cv_b = state[2]
        result = self._call(gu_form, state,
                            radio=_FakeRadio(value=_WQ_VOCAB[0]["form"]), next_v=1)
        assert result == "*...*"
        assert cv_b[0] == _WQ_VOCAB[1]

    def test_prev_reanswer_shows_new_feedback(self, gu_form):
        # Bug: after Prev, changing the radio selection must show new feedback,
        # not the old restore_entry result.
        past = {"word": _WQ_VOCAB[0], "answer": _WQ_VOCAB[0]["form"], "correct": True}
        restore = {"answer": past["answer"], "correct": True}
        # Viewing the restored question with a different (wrong) live selection
        state = self._state(
            cv=_WQ_VOCAB[0], rem=_WQ_VOCAB[2:],
            sc={"correct": 0, "total": 0},
            rst=restore, hist=[],
            fut=[{"word": _WQ_VOCAB[1], "answer": None, "correct": None}],
        )
        wrong = _WQ_VOCAB[1]["form"]  # a different word's form — always wrong
        result = self._call(gu_form, state, radio=_FakeRadio(value=wrong))
        # Must show ✗ (new wrong answer), not ✓ (old restore_entry)
        assert "✗" in str(result)
        assert "✓" not in str(result)

    def test_correct_answer_with_table_shows_table(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        result = self._call(
            gu_form, state, radio=_FakeRadio(value=w["form"]),
            build_paradigm_table=lambda word, lang: "<table>PARADIGM</table>",
        )
        assert "PARADIGM" in str(result)

    def test_correct_answer_no_table_data_shows_fallback(self, gu_form):
        w = {"meaning": "узнал", "form": "ἔγνω", "lemma": "γιγνώσκω", "context": ""}
        state = self._state(cv=w, rem=[])
        result = self._call(
            gu_form, state, radio=_FakeRadio(value=w["form"]),
            build_paradigm_table=lambda word, lang: None,
        )
        text = str(result)
        assert "ἔγνω" in text
        assert "отсутствует в парадигме" in text
        assert "γιγνώσκω" in text

    def test_correct_answer_no_table_data_fallback_is_localized(self, gu_form):
        w = {"meaning": "knew", "form": "ἔγνω", "lemma": "γιγνώσκω", "context": ""}
        state = self._state(cv=w, rem=[])
        result = self._call(
            gu_form, state, radio=_FakeRadio(value=w["form"]),
            build_paradigm_table=lambda word, lang: None, lang="en",
        )
        text = str(result)
        assert "missing in the paradigm of" in text
        assert "отсутствует" not in text

    def test_wrong_answer_never_calls_build_paradigm_table(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        calls = []

        def _spy(word, lang):
            calls.append(word)
            return "<table>SHOULD NOT APPEAR</table>"

        result = self._call(
            gu_form, state, radio=_FakeRadio(value=_WQ_VOCAB[1]["form"]),
            build_paradigm_table=_spy,
        )
        assert calls == []
        assert "SHOULD NOT APPEAR" not in str(result)

    def test_build_paradigm_table_exception_shows_error_text(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])

        def _boom(word, lang):
            raise ValueError("backend unavailable")

        result = self._call(
            gu_form, state, radio=_FakeRadio(value=w["form"]),
            build_paradigm_table=_boom,
        )
        assert "backend unavailable" in str(result)

    def test_no_build_paradigm_table_preserves_old_behavior(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        result = self._call(gu_form, state, radio=_FakeRadio(value=w["form"]))
        assert "отсутствует" not in str(result)

    def test_default_lang_is_russian(self, gu_form):
        state = self._state(cv=_WQ_VOCAB[0], rem=_WQ_VOCAB[1:])
        result = self._call(gu_form, state, radio=_FakeRadio(value=None))
        assert "правильно" in str(result)

    def test_lang_en_changes_progress_label(self, gu_form):
        state = self._state(cv=_WQ_VOCAB[0], rem=_WQ_VOCAB[1:])
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), lang="en")
        assert "correct" in str(result)
        assert "правильно" not in str(result)

    def test_done_with_show_prev_when_done_includes_prev(self, gu_form):
        next_btn = _FakeBtn(value=0, label="↺")
        prev_btn = _FakeBtn(value=0, label="◀")
        state = self._state(rem=[])
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, _, fut_g, fut_s = state
        with pytest.raises(StopIteration) as exc_info:
            gu_form.word_quiz_form(
                cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
                hist_g, hist_s, fut_g, fut_s,
                _FakeRadio(), next_btn, prev_btn,
                vocab=_WQ_VOCAB,
                show_prev_when_done=True,
            )
        content = exc_info.value.args[0]
        assert content[-1] == [prev_btn, next_btn]

    def test_done_without_show_prev_when_done_keeps_next_btn_bare(self, gu_form):
        # Default False -- every existing caller keeps today's exact shape
        # (a bare next_btn, not wrapped in an hstack with anything).
        next_btn = _FakeBtn(value=0, label="↺")
        state = self._state(rem=[])
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, _, fut_g, fut_s = state
        with pytest.raises(StopIteration) as exc_info:
            gu_form.word_quiz_form(
                cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
                hist_g, hist_s, fut_g, fut_s,
                _FakeRadio(), next_btn, _FakeBtn(value=0),
                vocab=_WQ_VOCAB,
            )
        content = exc_info.value.args[0]
        assert content[-1] is next_btn

    def test_config_show_prev_when_done_true_used_with_no_explicit_kwarg(self):
        gu = GreekUtils(mo_module=_FormMo(), config=_NAV_ICONS_CONFIG)
        next_btn = _FakeBtn(value=0, label="↺")
        prev_btn = _FakeBtn(value=0, label="◀")
        state = self._state(rem=[])
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, _, fut_g, fut_s = state
        with pytest.raises(StopIteration) as exc_info:
            gu.word_quiz_form(
                cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
                hist_g, hist_s, fut_g, fut_s,
                _FakeRadio(), next_btn, prev_btn,
                vocab=_WQ_VOCAB,
            )
        content = exc_info.value.args[0]
        assert content[-1] == [prev_btn, next_btn]


# ────────────────────────────────────────── make_paradigm_form ──

class TestMakeParadigmForm:
    """make_paradigm_form: multi-input paradigm drill widget."""

    _LABELS = ["1 sg:", "2 sg:", "3 sg:", "1 pl:", "2 pl:", "3 pl:"]

    def _mo(self):
        return _FormMo()

    def test_labels_stored(self):
        w = make_paradigm_form(self._mo(), self._LABELS)
        assert w.labels == self._LABELS

    def test_values_initialised_empty(self):
        w = make_paradigm_form(self._mo(), self._LABELS)
        assert w.values == [""] * len(self._LABELS)

    def test_values_prefilled_when_given(self):
        prefill = ["λέγω", "λέγεις", "λέγει", "λέγομεν", "λέγετε", "λέγουσι"]
        w = make_paradigm_form(self._mo(), self._LABELS, values=prefill)
        assert w.values == prefill

    def test_values_default_none_means_blank(self):
        w = make_paradigm_form(self._mo(), self._LABELS, values=None)
        assert w.values == [""] * len(self._LABELS)

    def test_labels_are_copied(self):
        labels = ["a:", "b:"]
        w = make_paradigm_form(self._mo(), labels)
        labels.append("c:")
        assert len(w.labels) == 2

    def test_polytonic_defaults_true(self):
        w = make_paradigm_form(self._mo(), self._LABELS)
        assert w.polytonic is True

    def test_polytonic_false_stored(self):
        w = make_paradigm_form(self._mo(), self._LABELS, polytonic=False)
        assert w.polytonic is False

    def test_no_anywidget_raises(self):
        import eee_project.notebook_utils as _nu
        orig = _nu._ANYWIDGET_OK
        try:
            _nu._ANYWIDGET_OK = False
            with pytest.raises(ImportError, match="anywidget"):
                make_paradigm_form(self._mo(), self._LABELS)
        finally:
            _nu._ANYWIDGET_OK = orig

    def test_esm_filters_marks_by_polytonic_traitlet(self):
        # The bar's mark set must be chosen from the live `polytonic` traitlet
        # at render time, not baked in at module-load time -- same widget class
        # serves both Ancient and Modern Greek instances.
        import eee_project.notebook_utils as _nu
        assert "model.get('polytonic')" in _nu._PARA_ESM
        assert "MONOTONIC_MARKS" in _nu._PARA_ESM

    def test_esm_focus_request_guards_against_late_reply_race(self):
        # focus_request's Python round trip is async; if the user has already
        # moved focus elsewhere by the time the reply lands (e.g. clicked past
        # the auto-advance target to type in a later field), applying it would
        # yank focus back to the field they intentionally skipped. The ESM must
        # only honor the request if focus is still on the request's own origin
        # field (tracked via pendingOrigin, not the racy submit_request.field_index,
        # which a newer Enter can overwrite before this reply lands).
        import eee_project.notebook_utils as _nu
        assert "focusedInp!==inputs[originIdx]" in _nu._PARA_ESM

    def test_esm_locks_origin_field_on_submit(self):
        # A fast typist who doesn't wait for the round trip must not be able
        # to keep typing into the field they just pressed Enter in -- that's
        # what actually corrupted fields (text piling up in the wrong slot,
        # or being select()ed and then erased by the very next keystroke).
        # Locking it read-only the instant Enter fires closes that window
        # entirely, instead of guessing after the fact whether it was hit.
        import eee_project.notebook_utils as _nu
        assert "inputs[idx].readOnly=true" in _nu._PARA_ESM
        assert "pendingOrigin.set(reqId,idx)" in _nu._PARA_ESM

    def test_esm_focus_request_matches_reply_to_exact_request(self):
        # The reply must be matched to the specific request it answers (by
        # the request_id Python already echoes back) rather than merely
        # "has anything changed since" -- a deterministic identity check,
        # not a timing guess. A reply for a superseded request still
        # releases that request's lock, but must not move focus.
        import eee_project.notebook_utils as _nu
        assert "pendingOrigin.get(request_id)" in _nu._PARA_ESM

    def test_esm_submit_refuses_already_locked_field(self):
        # fireSubmit itself won't re-lock or re-request a field that's
        # already read-only (a reply is still in flight for it) -- this is
        # what keeps a field's in-flight-request count at 1 in the common
        # case (impatient repeat-Enter on the same still-locked field).
        import eee_project.notebook_utils as _nu
        assert "if(idx>=0&&idx<inputs.length&&inputs[idx].readOnly)return;" in _nu._PARA_ESM

    def test_esm_lock_release_checks_for_other_pending_requests(self):
        # Belt-and-suspenders: even though fireSubmit's own guard makes a
        # second concurrent request for the same field unlikely, a field
        # must still only actually unlock once no *other* pending request
        # names it -- unlocking on the first of two replies, even a stale
        # or superseded one, would reopen the corruption window for
        # whichever request is still outstanding on that same field.
        import eee_project.notebook_utils as _nu
        assert "function releaseLock(idx){" in _nu._PARA_ESM
        assert "for(const v of pendingOrigin.values())if(v===idx)return;" in _nu._PARA_ESM

    def test_esm_reply_staleness_uses_submit_request_directly(self):
        # submit_request.request_id already is the request id (fireSubmit
        # sends the next value, every reply echoes back the one it
        # answered) -- comparing against model.get('submit_request')
        # directly means there's no separate "last sent" variable that
        # could drift out of sync with it.
        import eee_project.notebook_utils as _nu
        assert "request_id!==(model.get('submit_request').request_id||0)" in _nu._PARA_ESM
        assert "let lastReqId" not in _nu._PARA_ESM

    def test_esm_submit_request_bundles_both_fields_in_one_set(self):
        # request_id and field_index only mean something together -- one
        # model.set() call for both, not two separate traits that could
        # (even if only theoretically today) be observed mid-update.
        import eee_project.notebook_utils as _nu
        assert "model.set('submit_request',{request_id:reqId,field_index:idx});" in _nu._PARA_ESM

    def test_esm_focus_request_is_a_named_dict_not_a_positional_pair(self):
        # focus_request always carries an ack (request_id, to release the
        # lock) and *optionally* a real navigation instruction (advance_to,
        # null on a wrong answer or the last field). A plain [index, seq]
        # pair made that "sometimes it's just an ack" dual purpose invisible
        # in the shape itself -- a null advance_to says it directly.
        import eee_project.notebook_utils as _nu
        assert "const{request_id,advance_to}=model.get('focus_request')||{};" in _nu._PARA_ESM
        assert "advance_to!=null&&advance_to<inputs.length" in _nu._PARA_ESM

    def test_esm_submit_locks_release_on_timeout_backstop(self):
        # If Python's reply for this exact request never arrives (e.g.
        # coalesced away by a second Enter on a different field before the
        # first was processed), the lock must not be permanent.
        import eee_project.notebook_utils as _nu
        assert "},3000);" in _nu._PARA_ESM

    def test_esm_diacritic_composition_respects_readonly_lock(self):
        # readOnly blocks the browser's native text insertion, but diacritic
        # mark composition bypasses that entirely -- it calls
        # e.preventDefault() in beforeinput and then assigns inp.value=...
        # directly via JS, which readOnly does not block. Confirmed live: a
        # locked field would still accept a composed accented character
        # (e.g. clicking "acute" then typing a vowel) even though plain
        # typing into the same locked field was correctly rejected. The
        # handler must check readOnly itself.
        import eee_project.notebook_utils as _nu
        assert "if(inp.readOnly)return;" in _nu._PARA_ESM

    def test_esm_clear_mark_button_respects_readonly_lock(self):
        # Same bypass risk as composition: the "clear last mark" button
        # also assigns inp.value= directly, on whatever focusedInp
        # currently is -- which can be a locked field waiting on a reply.
        import eee_project.notebook_utils as _nu
        assert "if(!focusedInp||focusedInp.readOnly)return;" in _nu._PARA_ESM


# ────────────────────────────────────────── paste fix in ESM strings ──

# ────────────────────────────────────────── check_noun_test ──

class TestCheckNounTest:
    """Unit tests for GreekUtils.check_noun_test — logic branches."""

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    def _form(self, values, *, test_word=None, ac=None, is_pt=False):
        import types
        ns = types.SimpleNamespace(
            value=values,
            is_pluralia_tantum=is_pt,
        )
        if test_word is not None:
            ns.test_word = test_word
        if ac is not None:
            ns.active_cases = ac
        return ns

    def test_noun_form_none_returns_false(self, gu):
        ok, fb = gu.check_noun_test("ὁ ἀγρός", None)
        assert ok is False and fb == ""

    def test_empty_value_returns_false(self, gu):
        form = self._form([], test_word="ὁ ἀγρός")
        ok, fb = gu.check_noun_test("ὁ ἀγρός", form)
        assert ok is False and fb == ""

    def test_active_cases_none_uses_config_default(self, gu):
        # active_cases not set → computed from config noun_cells
        # _StubBackend.paradigm returns {} so forms are unknown → reported wrong
        form = self._form(["ἀγρός"], test_word="ὁ ἀγρός")
        # No active_cases attr → getattr returns None → falls into branch 1314-1315
        ok, fb = gu.check_noun_test("ὁ ἀγρός", form)
        assert ok is False  # stub returns no forms → mismatch

    def test_empty_field_in_values_marks_wrong(self, gu):
        # First value empty → _chk returns (False, []) for that slot
        form = self._form(
            ["", "ἀγρῷ"],
            test_word="ὁ ἀγρός",
            ac=[["sg", "nom"], ["sg", "dat"]],
        )
        ok, fb = gu.check_noun_test("ὁ ἀγρός", form)
        assert ok is False  # empty slot makes overall result False

    def test_article_error_ordered_before_noun_error(self):
        # Both parts wrong in the same slot: the article error must read
        # first, matching the order the answer is actually written (ὁ ἀγρός)
        # -- regression test for reordering _chk's error appends.
        def _paradigm_fn(word, pos):
            if pos != "noun":
                return {}
            return {"masc": {"sg": {"nom": {"ἀγρός"}}}}
        gu = GreekUtils(_StubBackend(_paradigm_fn), _StubMo(), config=ANCIENT_GREEK)
        form = self._form(["ἡ ΛΑΘΟΣ"], test_word="ὁ ἀγρός", ac=[["sg", "nom"]])
        ok, fb = gu.check_noun_test("ὁ ἀγρός", form, article=True, lang="en")
        assert ok is False
        assert "article" in fb and "noun" in fb
        assert fb.index("article") < fb.index("noun")

    def test_word_without_leading_article_fallback(self, gu):
        # No leading article → _detected_genders stays None → _genders_at falls back to backend
        # _StubBackend returns {} for all genders → correct_arts empty → article not checked
        form = self._form(
            ["λόγος"],
            test_word="λόγος",
            ac=[["sg", "nom"]],
        )
        ok, fb = gu.check_noun_test("λόγος", form)
        assert ok is False  # stub returns no forms → unknown → wrong

    # ------------------------------------------------------- indefinite=True

    @staticmethod
    def _mg_paradigm_fn(word, pos):
        if pos != "noun":
            return {}
        return {"masc": {"sg": {"nom": {"λόγος"}}}}

    @pytest.fixture
    def gu_mg(self):
        return GreekUtils(_StubBackend(self._mg_paradigm_fn), _StubMo(), config=MODERN_GREEK)

    def test_indefinite_true_checks_extra_slot(self, gu_mg):
        # value has one extra entry past ac -- the indefinite-article slot
        # for the sole (singular) case in ac
        form = self._form(["ο λόγος", "ένας λόγος"], test_word="ο λόγος", ac=[["sg", "nom"]])
        ok, fb = gu_mg.check_noun_test("ο λόγος", form, article=True, indefinite=True)
        assert ok is True and fb == ""

    def test_indefinite_true_wrong_indef_article_reported(self, gu_mg):
        form = self._form(["ο λόγος", "μία λόγος"], test_word="ο λόγος", ac=[["sg", "nom"]])
        ok, fb = gu_mg.check_noun_test("ο λόγος", form, article=True, indefinite=True, lang="en")
        assert ok is False
        assert "article" in fb

    def test_indefinite_false_ignores_extra_value_entries(self, gu_mg):
        # Without indefinite=True, only zip(value, ac) is consulted -- an
        # extra trailing value (even a wrong one) is simply never checked
        form = self._form(["ο λόγος", "WRONG"], test_word="ο λόγος", ac=[["sg", "nom"]])
        ok, fb = gu_mg.check_noun_test("ο λόγος", form, article=True, indefinite=False)
        assert ok is True

    def test_indefinite_no_op_without_config_indef_articles(self, gu):
        # gu (this class's default fixture) is ANCIENT_GREEK-configured --
        # indefinite=True has nothing to add, same result as indefinite=False
        form = self._form(["ἀγρός"], test_word="ἀγρός", ac=[["sg", "nom"]])
        with_indef = gu.check_noun_test("ἀγρός", form, indefinite=True)
        without_indef = gu.check_noun_test("ἀγρός", form, indefinite=False)
        assert with_indef == without_indef


# ────────────────────────────────────────── check_verb_test ──

class TestCheckVerbTest:
    """Unit tests for GreekUtils.check_verb_test — logic branches."""

    @pytest.fixture
    def gu_ag(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    @pytest.fixture
    def gu_mg(self):
        return GreekUtils(_StubBackend(), _StubMo())

    def _form(self, values, verb_word="λύω"):
        import types
        ns = types.SimpleNamespace(value=values, verb_word=verb_word)
        return ns

    def test_form_none_returns_false(self, gu_ag):
        ok, fb = gu_ag.check_verb_test("λύω", None, "present")
        assert ok is False and fb == ""

    def test_empty_form_field_marks_wrong(self, gu_ag):
        # First slot empty → ok=False, but no error message for that slot
        values = [""] + ["λύεις", "λύει", "λύομεν", "λύετε", "λύουσι"]
        ok, fb = gu_ag.check_verb_test("λύω", self._form(values), "present")
        assert ok is False

    def test_prefix_stripped_before_comparison(self, gu_mg):
        # MG future: prefix 'θα' must be present; cv = value minus prefix
        # Stub returns {} → forms unknown → ok=False, but line 1411 IS executed
        values = ["θα λύσω", "θα λύσεις", "θα λύσει", "θα λύσουμε", "θα λύσετε", "θα λύσουν"]
        ok, fb = gu_mg.check_verb_test("λύω", self._form(values), "future")
        assert ok is False  # stub returns no forms
        # expected in feedback should carry the 'θα' prefix
        assert "θα" in fb

    def test_prefix_missing_shows_error(self, gu_mg):
        # MG future without θα prefix → error message about the prefix
        values = ["λύσω", "", "", "", "", ""]
        ok, fb = gu_mg.check_verb_test("λύω", self._form(values), "future")
        assert ok is False
        assert "θα" in fb


# ────────────────────────────────────────── check_verb_slot ──

class TestCheckVerbSlot:
    """Unit tests for GreekUtils.check_verb_slot — single-slot correctness."""

    @staticmethod
    def _ag_paradigm_fn(word, pos):
        if pos != "verb":
            return {}
        return {"present": {"active": {"ind": {
            "sg": {"pri": {"λύω"}, "sec": {"λύεις"}, "ter": {"λύει"}},
            "pl": {"pri": {"λύομεν"}, "sec": {"λύετε"}, "ter": {"λύουσι"}},
        }}}}

    @staticmethod
    def _mg_future_paradigm_fn(word, pos):
        if pos != "verb":
            return {}
        return {"conjunctive": {"active": {"ind": {
            "sg": {"pri": {"λύσω"}, "sec": {"λύσεις"}, "ter": {"λύσει"}},
            "pl": {"pri": {"λύσουμε"}, "sec": {"λύσετε"}, "ter": {"λύσουν"}},
        }}}}

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(self._ag_paradigm_fn), _StubMo(), config=ANCIENT_GREEK)

    def test_correct_value(self, gu):
        assert gu.check_verb_slot("λύω", "present", 0, "λύω") is True

    def test_wrong_value(self, gu):
        assert gu.check_verb_slot("λύω", "present", 0, "WRONG") is False

    def test_empty_or_none_value(self, gu):
        assert gu.check_verb_slot("λύω", "present", 0, "") is False
        assert gu.check_verb_slot("λύω", "present", 0, None) is False

    def test_unknown_tense(self, gu):
        assert gu.check_verb_slot("λύω", "nonexistent", 0, "λύω") is False

    def test_slot_index_out_of_range(self, gu):
        assert gu.check_verb_slot("λύω", "present", 99, "λύω") is False
        assert gu.check_verb_slot("λύω", "present", -1, "λύω") is False

    def test_prefix_required_present_and_correct(self):
        gu = GreekUtils(_StubBackend(self._mg_future_paradigm_fn), _StubMo())
        assert gu.check_verb_slot("λύω", "future", 0, "θα λύσω") is True

    def test_prefix_required_but_missing(self):
        gu = GreekUtils(_StubBackend(self._mg_future_paradigm_fn), _StubMo())
        assert gu.check_verb_slot("λύω", "future", 0, "λύσω") is False

    def test_prefix_glued_no_space_rejected(self):
        gu = GreekUtils(_StubBackend(self._mg_future_paradigm_fn), _StubMo())
        assert gu.check_verb_slot("λύω", "future", 0, "θαλύσω") is False


# ────────────────────────────────────────── check_noun_slot ──

class TestCheckNounSlot:
    """Unit tests for GreekUtils.check_noun_slot — single-slot correctness."""

    @staticmethod
    def _paradigm_fn(word, pos):
        if pos != "noun":
            return {}
        return {"masc": {
            "sg": {"nom": {"ἀγρός"}, "acc": {"ἀγρόν"}, "gen": {"ἀγροῦ"}, "dat": {"ἀγρῷ"}},
            "pl": {"nom": {"ἀγροί"}, "acc": {"ἀγρούς"}, "gen": {"ἀγρῶν"}, "dat": {"ἀγροῖς"}},
        }}

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(self._paradigm_fn), _StubMo(), config=ANCIENT_GREEK)

    def test_correct_noun_no_article_required(self, gu):
        assert gu.check_noun_slot("ὁ ἀγρός", 0, "ἀγρός", article=False) is True

    def test_correct_noun_with_correct_article(self, gu):
        assert gu.check_noun_slot("ὁ ἀγρός", 0, "ὁ ἀγρός", article=True) is True

    def test_correct_noun_missing_required_article(self, gu):
        assert gu.check_noun_slot("ὁ ἀγρός", 0, "ἀγρός", article=True) is False

    def test_correct_noun_wrong_article(self, gu):
        assert gu.check_noun_slot("ὁ ἀγρός", 0, "ἡ ἀγρός", article=True) is False

    def test_wrong_noun_form(self, gu):
        assert gu.check_noun_slot("ὁ ἀγρός", 0, "WRONG", article=False) is False

    def test_empty_value(self, gu):
        assert gu.check_noun_slot("ὁ ἀγρός", 0, "", article=False) is False

    def test_slot_index_out_of_range(self, gu):
        assert gu.check_noun_slot("ὁ ἀγρός", 99, "ἀγρός") is False

    def test_active_cases_override(self, gu):
        # slot 0 with a custom active_cases pointing at 'gen' instead of the default 'nom'
        assert gu.check_noun_slot(
            "ὁ ἀγρός", 0, "ἀγροῦ", article=False, active_cases=[("sg", "gen")]
        ) is True

    # ------------------------------------------------------- indefinite=True

    @staticmethod
    def _mg_paradigm_fn(word, pos):
        if pos != "noun":
            return {}
        return {"masc": {"sg": {"nom": {"λόγος"}, "gen": {"λόγου"}}}}

    @pytest.fixture
    def gu_mg(self):
        return GreekUtils(_StubBackend(self._mg_paradigm_fn), _StubMo(), config=MODERN_GREEK)

    def test_indefinite_slot_correct(self, gu_mg):
        # index 2 == len(active_cases) -> first (and only) entry of the
        # singular-only indef_cells subset, i.e. active_cases[0] again
        assert gu_mg.check_noun_slot(
            "ο λόγος", 2, "ένας λόγος",
            active_cases=[("sg", "nom"), ("sg", "gen")], indefinite=True,
        ) is True

    def test_indefinite_slot_wrong_article(self, gu_mg):
        assert gu_mg.check_noun_slot(
            "ο λόγος", 2, "μία λόγος",
            active_cases=[("sg", "nom"), ("sg", "gen")], indefinite=True,
        ) is False

    def test_indefinite_slot_always_requires_article(self, gu_mg):
        # indefinite slots require their article regardless of `article`,
        # which only controls the definite slots
        assert gu_mg.check_noun_slot(
            "ο λόγος", 2, "λόγος",
            active_cases=[("sg", "nom"), ("sg", "gen")], indefinite=True, article=False,
        ) is False

    def test_indefinite_false_leaves_range_unchanged(self, gu_mg):
        # without indefinite=True, index 2 (== len(active_cases)) is simply
        # out of range, not reinterpreted as an indefinite slot
        assert gu_mg.check_noun_slot(
            "ο λόγος", 2, "ένας λόγος",
            active_cases=[("sg", "nom"), ("sg", "gen")], indefinite=False,
        ) is False

    def test_indefinite_no_op_without_config_indef_articles(self, gu):
        # gu (this class's default fixture) is ANCIENT_GREEK-configured --
        # indef_articles is None, so indefinite=True adds no valid slots
        assert gu.check_noun_slot(
            "ὁ ἀγρός", 1, "τις ἀγρός", active_cases=[("sg", "nom")], indefinite=True,
        ) is False

    def test_indefinite_excludes_plural_cases(self, gu_mg):
        # active_cases has one sg and one pl entry -> indef_cells is only
        # the sg one, so index 2 (== len(active_cases)) is the sole valid
        # indefinite slot and index 3 is out of range
        assert gu_mg.check_noun_slot(
            "ο λόγος", 3, "ένας λόγος",
            active_cases=[("sg", "nom"), ("pl", "nom")], indefinite=True,
        ) is False


# ────────────────────────────────────────── save_entry ──

class TestSaveEntry:
    """Unit tests for GreekUtils.save_entry."""

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    def test_no_current_word_is_noop(self, gu):
        entered = {"existing": ["x"]}
        assert gu.save_entry(entered, None, _pdform(["a"])) is entered

    def test_merges_current_word(self, gu):
        result = gu.save_entry({}, {"form": "λύω"}, _pdform(["a", "b"]))
        assert result == {"λύω": ["a", "b"]}

    def test_preserves_other_entries(self, gu):
        result = gu.save_entry({"other": ["x"]}, {"form": "νέος"}, _pdform(["c"]))
        assert result == {"other": ["x"], "νέος": ["c"]}

    def test_custom_word_key(self, gu):
        result = gu.save_entry({}, {"Word": "λύω"}, _pdform(["a", "b"]), word_key="Word")
        assert result == {"λύω": ["a", "b"]}


# ────────────────────────────────────────── make_paradigm_drill_state ──

class _StateMo:
    """Minimal mo stub with a real mo.state() -- unlike the rest of
    GreekUtils, make_paradigm_drill_state actually calls self._mo.state()."""
    @staticmethod
    def state(v):
        g, s, _ = _pair(v)
        return g, s


class TestMakeParadigmDrillState:
    """Unit tests for GreekUtils.make_paradigm_drill_state."""

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StateMo(), config=ANCIENT_GREEK)

    def test_returns_20_tuple(self, gu):
        assert len(gu.make_paradigm_drill_state([])) == 20

    def test_initial_words_seeded(self, gu):
        vocab = [{"Word": "λύω"}, {"Word": "νέος"}]
        words, *_ = gu.make_paradigm_drill_state(vocab)
        assert words() == vocab
        assert words() is not vocab  # a fresh copy, not the same list object

    def test_everything_else_starts_empty(self, gu):
        (_, _, hist, _, msg, _, cap, _, entered, _, sub_cnt, _, prev_cnt, _,
         nxt_cnt, _, entercnt, _, restart_cnt, _) = gu.make_paradigm_drill_state([{"Word": "λύω"}])
        assert hist() == []
        assert msg() == ""
        assert cap() is None
        assert entered() == {}
        assert sub_cnt() == 0
        assert prev_cnt() == 0
        assert nxt_cnt() == 0
        assert entercnt() == 0
        assert restart_cnt() == 0

    def test_pairs_are_independent(self, gu):
        words, set_words, hist, set_hist, *_ = gu.make_paradigm_drill_state([])
        set_words(["x"])
        set_hist(["y"])
        assert words() == ["x"]
        assert hist() == ["y"]

    def test_order_matches_pack_paradigm_state(self, gu):
        # The 20-tuple must unpack directly into the same positional order
        # _pack_paradigm_state (and every *_paradigm_drill_form sibling)
        # expects -- verify the mapping directly rather than trusting it.
        state_tuple = gu.make_paradigm_drill_state([])
        packed = gu._pack_paradigm_state(*state_tuple)
        assert packed["words"] == (state_tuple[0], state_tuple[1])
        assert packed["restart_cnt"] == (state_tuple[18], state_tuple[19])


class TestMakeErrorTrackingState:
    """Unit tests for GreekUtils.make_error_tracking_state."""

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StateMo(), config=ANCIENT_GREEK)

    def test_starts_with_no_mistakes_and_no_retries(self, gu):
        errors, _, retry_cnt, _ = gu.make_error_tracking_state()
        assert errors() == {}
        assert retry_cnt() == 0

    def test_each_setter_drives_its_own_getter(self, gu):
        errors, set_errors, retry_cnt, set_retry_cnt = gu.make_error_tracking_state()
        set_errors({"λύω": 2})
        assert (errors(), retry_cnt()) == ({"λύω": 2}, 0)
        set_retry_cnt(3)
        assert (errors(), retry_cnt()) == ({"λύω": 2}, 3)


# ────────────────────────────────────────── reset_paradigm_drill_state ──

class TestResetParadigmDrillState:
    """Unit tests for GreekUtils.reset_paradigm_drill_state."""

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    def test_resets_all_state(self, gu):
        calls = {}

        def tracker(name):
            return lambda v: calls.__setitem__(name, v)

        vocab = [{"Word": "λύω"}, {"Word": "νέος"}]
        gu.reset_paradigm_drill_state(
            vocab,
            tracker("words"), tracker("hist"), tracker("msg"), tracker("cap"),
            tracker("entered"), tracker("sub"), tracker("prev"), tracker("nxt"),
        )
        # words is a *shuffled* copy -- same elements, not necessarily vocab's
        # own order (see test_reshuffles_on_restart for the exact mechanism).
        assert sorted(calls["words"], key=lambda d: d["Word"]) == sorted(vocab, key=lambda d: d["Word"])
        assert calls["words"] is not vocab  # a fresh copy, not the same list object
        assert calls["hist"] == []
        assert calls["msg"] == ""
        assert calls["cap"] is None
        assert calls["entered"] == {}
        assert calls["sub"] == 0
        assert calls["prev"] == 0
        assert calls["nxt"] == 0

    def test_reshuffles_on_restart(self, gu):
        # REGRESSION: "start over" used to call set_words(list(vocab))
        # directly -- resetting the queue to vocab's own (e.g. table) order
        # instead of a fresh random order, unlike the initial
        # make_paradigm_drill_state() call which wraps it in random.sample.
        # Real reported bug: a verb test always showed words in table order
        # after switching tense and pressing restart.
        calls = {}

        def tracker(name):
            return lambda v: calls.__setitem__(name, v)

        vocab = [{"Word": w} for w in "abcdefghijklmnopqrst"]
        shuffled = list(reversed(vocab))
        with patch("eee_project.notebook_utils._random.sample", return_value=shuffled) as mock_sample:
            gu.reset_paradigm_drill_state(
                vocab,
                tracker("words"), tracker("hist"), tracker("msg"), tracker("cap"),
                tracker("entered"), tracker("sub"), tracker("prev"), tracker("nxt"),
            )
        mock_sample.assert_called_once_with(vocab, len(vocab))
        assert calls["words"] == shuffled


# ────────────────────────────────────────── dirty_check_button ──

class TestDirtyCheckButton:
    """Unit tests for GreekUtils.dirty_check_button."""

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    def test_clean_when_no_input(self, gu):
        btn = gu.dirty_check_button(_pdform(["", ""]), lambda: None, None, "verb_word")
        assert btn.kind == "neutral"

    def test_dirty_when_input_never_checked(self, gu):
        btn = gu.dirty_check_button(_pdform(["λύω", ""]), lambda: None, {"form": "λύω"}, "verb_word")
        assert btn.kind == "warn"

    def test_clean_when_input_matches_last_check(self, gu):
        import types
        snap = types.SimpleNamespace(verb_word="λύω", value=["λύω", ""])
        btn = gu.dirty_check_button(_pdform(["λύω", ""]), lambda: snap, {"form": "λύω"}, "verb_word")
        assert btn.kind == "neutral"

    def test_dirty_when_input_changed_since_last_check(self, gu):
        import types
        snap = types.SimpleNamespace(verb_word="λύω", value=["λύω", ""])
        btn = gu.dirty_check_button(_pdform(["λύεις", ""]), lambda: snap, {"form": "λύω"}, "verb_word")
        assert btn.kind == "warn"

    def test_dirty_when_last_check_was_a_different_word(self, gu):
        import types
        snap = types.SimpleNamespace(verb_word="OTHER", value=["λύω", ""])
        btn = gu.dirty_check_button(_pdform(["λύω", ""]), lambda: snap, {"form": "λύω"}, "verb_word")
        assert btn.kind == "warn"

    def test_default_label_is_english(self, gu):
        btn = gu.dirty_check_button(_pdform([""]), lambda: None, None, "verb_word")
        assert btn.label == "Check"

    def test_label_can_be_overridden(self, gu):
        btn = gu.dirty_check_button(_pdform([""]), lambda: None, None, "verb_word", label="Проверить")
        assert btn.label == "Проверить"

    def test_custom_word_key(self, gu):
        btn = gu.dirty_check_button(
            _pdform(["λύω", ""]), lambda: None, {"Word": "λύω"}, "verb_word", word_key="Word"
        )
        assert btn.kind == "warn"


# ────────────────────────────────────────── retry_mistakes_button ──

class TestRetryMistakesButton:
    """Unit tests for GreekUtils.retry_mistakes_button."""

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    def test_disabled_until_a_mistake_is_recorded(self, gu):
        assert gu.retry_mistakes_button({}).disabled is True
        assert gu.retry_mistakes_button({"λύω": 1}).disabled is False

    @pytest.mark.parametrize("kwargs, label", [
        ({}, "Ошибки"), ({"lang": "ru"}, "Ошибки"), ({"lang": "en"}, "Errors"), ({"lang": "el"}, "Λάθη"),
    ])
    def test_default_label_follows_lang(self, gu, kwargs, label):
        assert gu.retry_mistakes_button({}, **kwargs).label == label

    def test_label_can_be_overridden(self, gu):
        assert gu.retry_mistakes_button({}, label="Again").label == "Again"

    def test_each_click_increments_the_counter(self, gu):
        on_click = gu.retry_mistakes_button({"λύω": 1}).on_click
        assert on_click(None) == 1
        assert on_click(4) == 5


# ────────────────────────────────────────── paradigm_drill_widgets ──

class TestParadigmDrillWidgets:
    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    def _patched(self):
        return patch("eee_project.notebook_utils.make_paradigm_form", return_value=_pdform([""]))

    def test_returns_four_tuple(self, gu):
        with self._patched():
            result = gu.paradigm_drill_widgets(labels=["1 sg:"])
        assert len(result) == 4

    def test_does_not_depend_on_cap(self, gu):
        # No cap/cv/attr_name params at all — this is the point of the split
        # (see the function's own docstring): the form-creation cell must
        # not be rebuilt just because a check snapshot changed.
        import inspect
        assert "cap" not in inspect.signature(gu.paradigm_drill_widgets).parameters

    def test_passes_config_polytonic_to_form(self, gu):
        # gu's config is ANCIENT_GREEK (polytonic=True) — must reach make_paradigm_form,
        # not silently default, so a Modern Greek GreekUtils instance gets polytonic=False.
        with patch("eee_project.notebook_utils.make_paradigm_form",
                   return_value=_pdform([""])) as mock_form:
            gu.paradigm_drill_widgets(labels=["1 sg:"])
        assert mock_form.call_args.kwargs["polytonic"] is True

    def test_modern_greek_config_passes_polytonic_false(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=MODERN_GREEK)
        with patch("eee_project.notebook_utils.make_paradigm_form",
                   return_value=_pdform([""])) as mock_form:
            gu.paradigm_drill_widgets(labels=["Sg. Nom.:"])
        assert mock_form.call_args.kwargs["polytonic"] is False

    def test_prev_disabled_with_no_history(self, gu):
        with self._patched():
            _, prev_btn, _, _ = gu.paradigm_drill_widgets(labels=["1 sg:"], history_len=0)
        assert prev_btn.disabled is True

    def test_prev_enabled_with_history(self, gu):
        with self._patched():
            _, prev_btn, _, _ = gu.paradigm_drill_widgets(labels=["1 sg:"], history_len=2)
        assert prev_btn.disabled is False

    def test_nxt_enabled_with_one_remaining(self, gu):
        # Confirmed with the user: Next moving the sole remaining word
        # straight to "done" works fine unscored (no per-word score to get
        # wrong on skip in this family) -- no longer disabled at exactly 1,
        # matching word_drill_widgets' own next_btn (never disabled at all).
        with self._patched():
            _, _, nxt_btn, _ = gu.paradigm_drill_widgets(labels=["1 sg:"], remaining_len=1)
        assert nxt_btn.disabled is False

    def test_nxt_enabled_with_more_remaining(self, gu):
        with self._patched():
            _, _, nxt_btn, _ = gu.paradigm_drill_widgets(labels=["1 sg:"], remaining_len=3)
        assert nxt_btn.disabled is False

    def test_nxt_disabled_with_zero_remaining(self, gu):
        # Practically unreachable (a current word always counts itself in
        # remaining_len), but the parameter still supports it defensively.
        with self._patched():
            _, _, nxt_btn, _ = gu.paradigm_drill_widgets(labels=["1 sg:"], remaining_len=0)
        assert nxt_btn.disabled is True

    def test_restart_btn_uses_custom_label(self, gu):
        with self._patched():
            _, _, _, restart_btn = gu.paradigm_drill_widgets(
                labels=["1 sg:"], restart_label="Начать заново",
            )
        assert restart_btn.label == "Начать заново"

    def test_default_lang_is_ru(self, gu):
        with self._patched():
            _, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(labels=["1 sg:"])
        assert nxt_btn.label == "Следующее"
        assert prev_btn.label == "Предыдущее"
        assert restart_btn.label == "Пройти снова"

    def test_lang_en_uses_english_labels(self, gu):
        # Plain text, matching ru/el and nav_next_label/nav_prev_label's own
        # convention. Restart's default now comes from nav_again_label
        # ("Again") rather than the since-retired restart_label key
        # ("Start over") -- confirmed with the user that the two wordings
        # were an unintentional gap, not a deliberate distinction, since
        # word_drill_form/word_quiz_form's own restart button already says
        # "Again" and both buttons do the exact same thing (reshuffle and
        # start the round over).
        with self._patched():
            _, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="en",
            )
        assert nxt_btn.label == "Next"
        assert prev_btn.label == "Prev"
        assert restart_btn.label == "Again"

    def test_lang_el_uses_greek_labels(self, gu):
        with self._patched():
            _, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="el",
            )
        assert nxt_btn.label == "Επόμενο"
        assert prev_btn.label == "Προηγούμενο"
        assert restart_btn.label == "Ξανά"

    def test_explicit_labels_override_lang_default(self, gu):
        with self._patched():
            _, prev_btn, nxt_btn, _ = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="en", next_label="Continue", prev_label="Back",
            )
        assert nxt_btn.label == "Continue"
        assert prev_btn.label == "Back"

    def test_nav_icons_true_decorates_default_labels(self, gu):
        with self._patched():
            _, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="en", nav_icons=True,
            )
        assert prev_btn.label == "◀ Prev"
        assert nxt_btn.label == "Next ▶"
        assert restart_btn.label == "↺ Again"

    def test_nav_icons_true_decorates_explicit_label_override_too(self, gu):
        # Whichever text ends up in effect gets decorated, not just the
        # looked-up default -- the caller asked for icon mode either way.
        with self._patched():
            _, prev_btn, nxt_btn, _ = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="en", next_label="Continue", prev_label="Back",
                nav_icons=True,
            )
        assert nxt_btn.label == "Continue ▶"
        assert prev_btn.label == "◀ Back"

    def test_nav_icons_false_default_leaves_labels_plain(self, gu):
        with self._patched():
            _, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="en",
            )
        assert "◀" not in prev_btn.label and "▶" not in nxt_btn.label and "↺" not in restart_btn.label

    def test_config_nav_icons_true_decorates_labels_with_no_explicit_kwarg(self):
        # nav_icons omitted entirely (not even nav_icons=None) -- must resolve
        # from config.nav_icons, not silently fall back to the old hardcoded
        # False default.
        gu = GreekUtils(_StubBackend(), _StubMo(), config=_NAV_ICONS_CONFIG)
        with self._patched():
            _, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="en",
            )
        assert prev_btn.label == "◀ Prev"
        assert nxt_btn.label == "Next ▶"
        assert restart_btn.label == "↺ Again"

    def test_explicit_nav_icons_false_overrides_config_true(self):
        # An explicit False must still win over a config default of True --
        # config only supplies the default when the caller passes nothing.
        gu = GreekUtils(_StubBackend(), _StubMo(), config=_NAV_ICONS_CONFIG)
        with self._patched():
            _, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="en", nav_icons=False,
            )
        assert "◀" not in prev_btn.label and "▶" not in nxt_btn.label and "↺" not in restart_btn.label


# ────────────────────────────────────────── verb_paradigm_drill_form / noun_paradigm_drill_form ──

def _pdform(values, submit_count=0, enter_field_index=0, focus_request=None):
    """Fake make_paradigm_form() return value: .widget.values/.submit_request/etc.
    Keeps the caller-facing submit_count/enter_field_index parameter names
    (every call site in this file uses them) even though the widget itself
    now bundles both into one submit_request dict."""
    import types
    widget = types.SimpleNamespace(
        values=values,
        submit_request={"request_id": submit_count, "field_index": enter_field_index},
        focus_request=focus_request or {},
    )
    return types.SimpleNamespace(widget=widget)


class _ParadigmDrillFormBase:
    """Shared state/call scaffolding for the three *_paradigm_drill_form
    test classes — subclasses set ``_VOCAB`` and a thin ``_call``."""
    _VOCAB: list = []

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _FormMo(), config=ANCIENT_GREEK)

    def _state(self, words=None, hist=None, msg="", cap=None, entered=None,
               sub_cnt=0, prev_cnt=0, nxt_cnt=0, entercnt=0, restart_cnt=0):
        return {
            "words": _pair(words if words is not None else list(self._VOCAB)),
            "hist": _pair(hist or []),
            "msg": _pair(msg),
            "cap": _pair(cap),
            "entered": _pair(entered or {}),
            "sub_cnt": _pair(sub_cnt),
            "prev_cnt": _pair(prev_cnt),
            "nxt_cnt": _pair(nxt_cnt),
            "entercnt": _pair(entercnt),
            "restart_cnt": _pair(restart_cnt),
        }

    def _call_form(self, fn, state, cv, form, check_v=None, prev_v=None, nxt_v=None,
                   restart_v=None, **kwargs):
        s = state
        kwargs.setdefault("vocab", self._VOCAB)
        return fn(
            s["words"][0], s["words"][1],
            s["hist"][0], s["hist"][1],
            s["msg"][0], s["msg"][1],
            s["cap"][0], s["cap"][1],
            s["entered"][0], s["entered"][1],
            s["sub_cnt"][0], s["sub_cnt"][1],
            s["prev_cnt"][0], s["prev_cnt"][1],
            s["nxt_cnt"][0], s["nxt_cnt"][1],
            s["entercnt"][0], s["entercnt"][1],
            s["restart_cnt"][0], s["restart_cnt"][1],
            cv, form, _FakeBtn(check_v), _FakeBtn(prev_v), _FakeBtn(nxt_v), _FakeBtn(restart_v),
            **kwargs,
        )

    def _assert_same_words(self, actual: list, expected: list) -> None:
        """A restarted queue is shuffled (see TestResetParadigmDrillState.
        test_reshuffles_on_restart), so check same elements, not same order.
        """
        assert sorted(actual, key=lambda d: d["form"]) == sorted(expected, key=lambda d: d["form"])


class TestVerbParadigmDrillForm(_ParadigmDrillFormBase):
    _VOCAB = [{"form": "λύω", "meaning": "I loose"}, {"form": "ἄγω", "meaning": "I lead"}]

    def _meta(self, active_slots=None):
        import types
        return types.SimpleNamespace(
            active_slots=active_slots or [("sg", "pri"), ("sg", "sec"), ("sg", "ter"),
                                           ("pl", "pri"), ("pl", "sec"), ("pl", "ter")],
        )

    def _call(self, gu, state, cv, form, verb_meta, **kwargs):
        return self._call_form(gu.verb_paradigm_drill_form, state, cv, form,
                               verb_meta=verb_meta, **kwargs)

    def test_done_shows_callout_and_restart(self, gu):
        state = self._state(words=[])
        result = self._call(gu, state, None, _pdform([]), self._meta())
        assert "callout" in str(result)

    def test_restart_click_resets_state(self, gu):
        state = self._state(
            words=[self._VOCAB[0]], hist=[self._VOCAB[1]], entered={"λύω": ["x"]},
        )
        result = self._call(gu, state, self._VOCAB[0], _pdform([""]), self._meta(), restart_v=1)
        assert result == "*...*"
        self._assert_same_words(state["words"][2][0], self._VOCAB)
        assert state["hist"][2][0] == []
        assert state["entered"][2][0] == {}

    def test_correct_full_check_advances_and_saves(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_verb_test", return_value=(True, "")):
            result = self._call(gu, state, cv, _pdform(["λύω"]), self._meta(), check_v=1)
        assert result == "*...*"
        assert cv not in state["words"][2][0]
        assert cv in state["hist"][2][0]
        assert state["entered"][2][0].get("λύω") == ["λύω"]
        assert "λύω" in state["msg"][2][0]

    def test_wrong_full_check_shows_feedback_no_advance(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_verb_test", return_value=(False, "❌ wrong")):
            result = self._call(gu, state, cv, _pdform(["asd"]), self._meta(), check_v=1)
        assert "❌ wrong" in str(result)
        assert cv in state["words"][2][0]

    def test_lang_reaches_check_verb_test(self, gu):
        # Regression: verb_paradigm_drill_form used to have no lang param at
        # all -- check_verb_test's wrong-answer feedback text ("entered ...,
        # must be ...") was always hardcoded English no matter what language
        # the notebook was using. Confirm lang now actually threads through.
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_verb_test", return_value=(False, "")) as m:
            self._call(gu, state, cv, _pdform(["asd"]), self._meta(), check_v=1, lang="el")
        assert m.call_args.kwargs.get("lang") == "el"

    # nav_icons: reorders check/prev/next so Prev/Next stay first/last, and
    # hides (not just disables) Prev when there's no history yet. Next is
    # never hidden (or disabled) at all -- confirmed with the user that
    # skipping the sole remaining word straight to "done" via Next should
    # work, matching word_drill/word_quiz's own next_btn (never disabled
    # by remaining count either).

    def test_nav_icons_hides_prev_with_no_history(self, gu):
        cv = self._VOCAB[0]
        state = self._state()  # default: both words remaining, hist=[]
        result = self._call(gu, state, cv, _pdform(["", ""]), self._meta(), nav_icons=True)
        assert len(result[-2]) == 2  # [check_btn, nxt_btn] -- no prev_btn

    def test_config_nav_icons_true_used_with_no_explicit_kwarg(self):
        gu = GreekUtils(_StubBackend(), _FormMo(), config=_NAV_ICONS_CONFIG)
        cv = self._VOCAB[0]
        state = self._state()
        result = self._call(gu, state, cv, _pdform(["", ""]), self._meta())
        assert len(result[-2]) == 2  # [check_btn, nxt_btn] -- no prev_btn

    def test_nav_icons_shows_next_even_with_one_remaining(self, gu):
        cv = self._VOCAB[0]
        state = self._state(words=[cv], hist=[{"form": "dummy", "meaning": "dummy"}])
        result = self._call(gu, state, cv, _pdform(["", ""]), self._meta(), nav_icons=True)
        assert len(result[-2]) == 3  # [prev_btn, check_btn, nxt_btn] -- nxt_btn never hides

    def test_nav_icons_shows_both_with_history_and_remaining(self, gu):
        cv = self._VOCAB[0]
        state = self._state(hist=[{"form": "dummy", "meaning": "dummy"}])
        result = self._call(gu, state, cv, _pdform(["", ""]), self._meta(), nav_icons=True)
        assert len(result[-2]) == 3  # [prev_btn, check_btn, nxt_btn]

    def test_nav_icons_false_default_row_unchanged(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        result = self._call(gu, state, cv, _pdform(["", ""]), self._meta())
        assert len(result[-2]) == 3  # [check_btn, prev_btn, nxt_btn] -- prev just disabled, still shown

    def test_lang_defaults_to_ru(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_verb_test", return_value=(False, "")) as m:
            self._call(gu, state, cv, _pdform(["asd"]), self._meta(), check_v=1)
        assert m.call_args.kwargs.get("lang") == "ru"

    def test_previous_words_confirmation_is_shown_with_the_next_word(self, gu):
        state = self._state(words=[self._VOCAB[1]], hist=[self._VOCAB[0]], msg="✓ λύω — I loose")
        result = self._call(gu, state, self._VOCAB[1], _pdform(["", ""]), self._meta())
        assert "✓ λύω — I loose" in result

    def test_no_confirmation_line_when_there_is_nothing_to_confirm(self, gu):
        with_msg = self._call(gu, self._state(msg="✓ x"), self._VOCAB[0], _pdform(["", ""]), self._meta())
        without = self._call(gu, self._state(), self._VOCAB[0], _pdform(["", ""]), self._meta())
        assert len(with_msg) == len(without) + 1

    def test_enter_on_correct_slot_advances_focus(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["λύω", ""], submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_verb_slot", return_value=True), \
             patch.object(gu, "check_verb_test", return_value=(False, "")):
            self._call(gu, state, cv, form, self._meta())
        assert form.widget.focus_request == {"request_id": 1, "advance_to": 1}

    def test_verb_meta_omitted_falls_back_to_full_slots(self, gu):
        # REGRESSION: verb_meta used to be a required kwarg -- any caller
        # that forgot to compute/pass it crashed with TypeError the moment
        # a student picked a word. Omitting it now degrades to the full,
        # unfiltered config.verb_slots list instead.
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["λύω", ""], submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_verb_slot", return_value=True) as mock_slot, \
             patch.object(gu, "check_verb_test", return_value=(False, "")):
            self._call_form(gu.verb_paradigm_drill_form, state, cv, form, tense="present")
        mock_slot.assert_called_with(cv["form"], "present", 0, "λύω", active_slots=gu._cfg.verb_slots)

    def test_enter_on_correct_last_slot_has_no_advance_target(self, gu):
        # No field beyond the last one to advance to, but the JS side still
        # needs a reply to release the lock it placed on this exact field.
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["λύω"], submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_verb_slot", return_value=True), \
             patch.object(gu, "check_verb_test", return_value=(False, "")):
            self._call(gu, state, cv, form, self._meta())
        assert form.widget.focus_request == {"request_id": 1, "advance_to": None}

    def test_enter_on_wrong_slot_does_not_advance_focus(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["asd", ""], submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_verb_slot", return_value=False), \
             patch.object(gu, "check_verb_test", return_value=(False, "")):
            self._call(gu, state, cv, form, self._meta())
        # Still replies (advance_to=None, not omitted) -- the JS side locks
        # the origin field on every Enter and needs a reply to release that
        # lock, even when the answer was wrong.
        assert form.widget.focus_request == {"request_id": 1, "advance_to": None}

    def test_next_button_persists_and_advances_regardless_of_correctness(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_verb_test", return_value=(False, "")):
            result = self._call(gu, state, cv, _pdform(["asd"]), self._meta(), nxt_v=1)
        assert result == "*...*"
        assert cv not in state["words"][2][0]
        assert cv in state["hist"][2][0]
        assert state["entered"][2][0].get("λύω") == ["asd"]

    def test_prev_button_restores_previous_word(self, gu):
        prev_word = self._VOCAB[1]
        cv = self._VOCAB[0]
        state = self._state(hist=[prev_word])
        with patch.object(gu, "check_verb_test", return_value=(False, "")):
            result = self._call(gu, state, cv, _pdform([""]), self._meta(), prev_v=1)
        assert result == "*...*"
        assert state["words"][2][0][0] == prev_word
        assert state["hist"][2][0] == []

    def test_custom_word_key(self, gu):
        cv = {"Word": "λύω", "Translation": "I loose"}
        state = self._state(words=[cv])
        with patch.object(gu, "check_verb_test", return_value=(True, "")):
            result = self._call(gu, state, cv, _pdform(["λύω"]), self._meta(), check_v=1, word_key="Word", meaning_key="Translation")
        assert result == "*...*"
        assert state["entered"][2][0].get("λύω") == ["λύω"]

    # ─────────────────────────────────────── retry-mistakes (error tracking) ──

    def test_wrong_full_check_increments_error_count(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, errors_box = _pair({})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        with patch.object(gu, "check_verb_test", return_value=(False, "❌ wrong")):
            self._call(gu, state, cv, _pdform(["asd"]), self._meta(), check_v=1,
                      get_errors=get_errors, set_errors=set_errors,
                      get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {"λύω": 1}

    def test_wrong_full_check_twice_increments_to_two(self, gu):
        # Reuses one state dict across two calls -- get_sub_cnt()'s watermark
        # must carry over for the second check_v=2 click to register as new,
        # same as a real reactive re-render would.
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, errors_box = _pair({})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        with patch.object(gu, "check_verb_test", return_value=(False, "❌ wrong")):
            self._call(gu, state, cv, _pdform(["asd"]), self._meta(), check_v=1,
                      get_errors=get_errors, set_errors=set_errors,
                      get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
            self._call(gu, state, cv, _pdform(["def"]), self._meta(), check_v=2,
                      get_errors=get_errors, set_errors=set_errors,
                      get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {"λύω": 2}

    def test_progress_line_shows_error_total_mid_session(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, _ = _pair({"λύω": 2, "ἄγω": 1})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        with patch.object(gu, "check_verb_test", return_value=(False, "")):
            result = self._call(gu, state, cv, _pdform(["asd"] * 6), self._meta(),
                                get_errors=get_errors, set_errors=set_errors,
                                get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert "❌ 3" in result[0]

    def test_progress_line_omits_error_count_when_none_recorded(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, _ = _pair({})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        with patch.object(gu, "check_verb_test", return_value=(False, "")):
            result = self._call(gu, state, cv, _pdform(["asd"] * 6), self._meta(),
                                get_errors=get_errors, set_errors=set_errors,
                                get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert "❌" not in result[0]

    def test_correct_full_check_does_not_touch_errors(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, errors_box = _pair({})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        with patch.object(gu, "check_verb_test", return_value=(True, "")):
            self._call(gu, state, cv, _pdform(["λύω"]), self._meta(), check_v=1,
                      get_errors=get_errors, set_errors=set_errors,
                      get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {}

    def test_correct_full_check_does_not_clear_this_words_existing_error_count(self, gu):
        # REGRESSION (confirmed live): a mistake typed and immediately
        # self-corrected within one attempt -- before that same word's own
        # final correct submission -- must still count. Clearing per-word
        # the instant it's next answered correctly was tried and reverted:
        # it made a live-reported mistake vanish from the tally before the
        # round even ended. Mistake counts only reset at a round boundary
        # (restart/retry), not mid-round on a correct answer -- see
        # test_retry_button_clears_errors_when_starting_new_round below.
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, errors_box = _pair({"λύω": 3, "ἄγω": 2})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        with patch.object(gu, "check_verb_test", return_value=(True, "")):
            self._call(gu, state, cv, _pdform(["λύω"]), self._meta(), check_v=1,
                      get_errors=get_errors, set_errors=set_errors,
                      get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {"λύω": 3, "ἄγω": 2}

    def test_empty_check_click_does_not_count_as_error(self, gu):
        # A Check click with nothing typed yet (e.g. an accidental/premature
        # click) must not inflate the mistake count -- same has_input guard
        # dirty_check_button already uses.
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, errors_box = _pair({})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        with patch.object(gu, "check_verb_test", return_value=(False, "")):
            self._call(gu, state, cv, _pdform([""] * 6), self._meta(), check_v=1,
                      get_errors=get_errors, set_errors=set_errors,
                      get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {}

    def test_wrong_enter_on_field_increments_error_count(self, gu):
        # REGRESSION: per-field Enter-navigation is this drill's primary
        # interaction (not a secondary path to the Check button) -- a
        # student who types-and-Enters through every field, getting one
        # wrong along the way, must still have it counted even though
        # they never clicked Check.
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, errors_box = _pair({})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        form = _pdform(["asd", ""], submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_verb_slot", return_value=False), \
             patch.object(gu, "check_verb_test", return_value=(False, "")):
            self._call(gu, state, cv, form, self._meta(),
                      get_errors=get_errors, set_errors=set_errors,
                      get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {"λύω": 1}

    def test_correct_enter_on_field_does_not_increment_error_count(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, errors_box = _pair({})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        form = _pdform(["λύω", ""], submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_verb_slot", return_value=True), \
             patch.object(gu, "check_verb_test", return_value=(False, "")):
            self._call(gu, state, cv, form, self._meta(),
                      get_errors=get_errors, set_errors=set_errors,
                      get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {}

    def test_empty_enter_on_field_does_not_count_as_error(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, errors_box = _pair({})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        form = _pdform(["", ""], submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_verb_slot", return_value=False), \
             patch.object(gu, "check_verb_test", return_value=(False, "")):
            self._call(gu, state, cv, form, self._meta(),
                      get_errors=get_errors, set_errors=set_errors,
                      get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {}

    def test_without_error_tracking_wrong_check_is_unaffected(self, gu):
        # REGRESSION: get_errors/set_errors/get_retry_cnt/set_retry_cnt/
        # retry_btn are all optional, defaulting to None -- every
        # pre-existing call site (none of them pass these) must behave
        # exactly as before.
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_verb_test", return_value=(False, "❌ wrong")):
            result = self._call(gu, state, cv, _pdform(["asd"]), self._meta(), check_v=1)
        assert "❌ wrong" in str(result)

    def test_retry_button_starts_round_with_only_error_words(self, gu):
        get_errors, set_errors, _ = _pair({"ἄγω": 2})
        get_retry_cnt, set_retry_cnt, retry_cnt_box = _pair(0)
        state = self._state(words=[])  # done with the full pass
        result = self._call(gu, state, None, _pdform([]), self._meta(),
                            get_errors=get_errors, set_errors=set_errors,
                            get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt,
                            retry_btn=_FakeBtn(1))
        assert result == "*...*"
        assert state["words"][2][0] == [self._VOCAB[1]]  # only ἄγω, the one with a recorded error
        assert retry_cnt_box[0] == 1

    def test_retry_button_clears_errors_when_starting_new_round(self, gu):
        # REGRESSION (confirmed live): with errors kept forever, a word
        # fixed in an earlier retry round kept resurfacing in every later
        # "retry mistakes" click, since nothing ever cleared it. Starting a
        # new round (retry, same as restart) clears the whole dict --
        # confirmed separately (test below) that the mistake *list* is
        # still read correctly before this clear happens.
        get_errors, set_errors, errors_box = _pair({"ἄγω": 2})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        state = self._state(words=[])
        self._call(gu, state, None, _pdform([]), self._meta(),
                  get_errors=get_errors, set_errors=set_errors,
                  get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt,
                  retry_btn=_FakeBtn(1))
        assert errors_box[0] == {}

    def test_retry_button_reads_mistake_list_before_clearing_it(self, gu):
        get_errors, set_errors, _ = _pair({"ἄγω": 2})
        get_retry_cnt, set_retry_cnt, retry_cnt_box = _pair(0)
        state = self._state(words=[])
        result = self._call(gu, state, None, _pdform([]), self._meta(),
                            get_errors=get_errors, set_errors=set_errors,
                            get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt,
                            retry_btn=_FakeBtn(1))
        assert result == "*...*"
        assert [w["form"] for w in state["words"][2][0]] == ["ἄγω"]
        assert retry_cnt_box[0] == 1

    def test_progress_line_reflects_retry_round_size_not_full_vocab(self, gu):
        # REGRESSION (confirmed live): retrying 1 mistake out of a 2-word
        # vocab still showed "2 / 2" (len(vocab)) instead of "1 / 1" (this
        # round's actual size).
        get_errors, set_errors, _ = _pair({"ἄγω": 2})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        state = self._state(words=[])
        self._call(gu, state, None, _pdform([]), self._meta(),
                  get_errors=get_errors, set_errors=set_errors,
                  get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt,
                  retry_btn=_FakeBtn(1))
        cv = state["words"][2][0][0]  # the retry round's only word
        with patch.object(gu, "check_verb_test", return_value=(False, "")):
            result = self._call(gu, state, cv, _pdform([""]), self._meta(),
                                get_errors=get_errors, set_errors=set_errors,
                                get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert "**1** / 1" in result[0]

    def test_word_fixed_in_retry_round_does_not_resurface_in_next_retry(self, gu):
        # End-to-end version of the live bug report: retry -> answer the
        # retried word correctly -> a second retry click must find nothing
        # left to retry (errors was cleared at this round's start, and a
        # correct answer never adds anything back).
        get_errors, set_errors, errors_box = _pair({"ἄγω": 2})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        state = self._state(words=[])
        self._call(gu, state, None, _pdform([]), self._meta(),
                  get_errors=get_errors, set_errors=set_errors,
                  get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt,
                  retry_btn=_FakeBtn(1))
        assert [w["form"] for w in state["words"][2][0]] == ["ἄγω"]
        assert errors_box[0] == {}
        with patch.object(gu, "check_verb_test", return_value=(True, "")):
            self._call(gu, state, self._VOCAB[1], _pdform(["ἄγω"]), self._meta(), check_v=1,
                      get_errors=get_errors, set_errors=set_errors,
                      get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {}

    def test_restart_clears_errors_when_error_tracking_provided(self, gu):
        get_errors, set_errors, errors_box = _pair({"λύω": 3})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        state = self._state(words=[self._VOCAB[0]])
        self._call(gu, state, self._VOCAB[0], _pdform([""]), self._meta(), restart_v=1,
                  get_errors=get_errors, set_errors=set_errors,
                  get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {}

    def test_done_state_shows_retry_button_when_errors_exist(self, gu):
        get_errors, set_errors, _ = _pair({"λύω": 1})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        state = self._state(words=[], hist=[self._VOCAB[0]])
        retry_btn = _FakeBtn(None, label="Retry mistakes")
        result = self._call(gu, state, None, _pdform([]), self._meta(),
                            get_errors=get_errors, set_errors=set_errors,
                            get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt,
                            retry_btn=retry_btn)
        assert result[1] == "❌ 1 / 1"  # 1 word had a mistake, out of 1 word this round
        assert retry_btn in result[2]

    def test_done_state_error_indicator_is_words_with_mistakes_over_round_size(self, gu):
        # REGRESSION: previously showed "total mistake count / word count"
        # (e.g. "5 / 2" for 5 attempts across 2 words) -- a ratio that can
        # exceed 1 and reads as broken. "words with a mistake / round size"
        # is a normal fraction, and (like the progress line) must use this
        # round's own size, not len(vocab), so it stays correct in a retry
        # round over a smaller subset too.
        get_errors, set_errors, _ = _pair({"λύω": 3})  # only λύω had mistakes
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        state = self._state(words=[], hist=list(self._VOCAB))  # both words done this round
        result = self._call(gu, state, None, _pdform([]), self._meta(),
                            get_errors=get_errors, set_errors=set_errors,
                            get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt,
                            retry_btn=_FakeBtn(None))
        assert result[1] == "❌ 1 / 2"  # 1 of the round's 2 words had a mistake

    def test_done_state_omits_retry_button_when_no_errors(self, gu):
        get_errors, set_errors, _ = _pair({})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        state = self._state(words=[])
        retry_btn = _FakeBtn(None, label="Retry mistakes")
        result = self._call(gu, state, None, _pdform([]), self._meta(),
                            get_errors=get_errors, set_errors=set_errors,
                            get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt,
                            retry_btn=retry_btn)
        assert retry_btn not in result

    # ─────────────────────────────── show_prev_when_done ──

    def test_done_state_prev_hidden_by_default(self, gu):
        state = self._state(words=[], hist=[self._VOCAB[0]])
        result = self._call(gu, state, None, _pdform([]), self._meta())
        assert len(result) == 2  # callout + bare restart_btn only
        assert not isinstance(result[-1], list)

    def test_done_state_shows_prev_when_opted_in_with_history(self, gu):
        state = self._state(words=[], hist=[self._VOCAB[0]])
        result = self._call(gu, state, None, _pdform([]), self._meta(), show_prev_when_done=True)
        assert isinstance(result[-1], list) and len(result[-1]) == 2  # [prev_btn, restart_btn]

    def test_done_state_hides_prev_when_opted_in_but_no_history(self, gu):
        # Empty vocab entirely -- words=[] and hist=[] both -- nothing to
        # review back into, so Prev stays hidden even with the flag on.
        state = self._state(words=[], hist=[])
        result = self._call(gu, state, None, _pdform([]), self._meta(), show_prev_when_done=True)
        assert not isinstance(result[-1], list)

    def test_done_state_prev_and_retry_both_shown_when_both_apply(self, gu):
        get_errors, set_errors, _ = _pair({"λύω": 1})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        state = self._state(words=[], hist=[self._VOCAB[0]])
        retry_btn = _FakeBtn(None, label="Retry mistakes")
        result = self._call(gu, state, None, _pdform([]), self._meta(),
                            get_errors=get_errors, set_errors=set_errors,
                            get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt,
                            retry_btn=retry_btn, show_prev_when_done=True)
        assert len(result[-1]) == 3  # [prev_btn, restart_btn, retry_btn]
        assert retry_btn in result[-1]

    def test_prev_click_from_done_restores_last_word(self, gu):
        # The done-screen's Prev handling isn't just about whether the
        # button is *shown* -- the click itself must work even though
        # `words` is empty, since the handler now runs before the
        # done-screen's own early return (see _paradigm_drill_form).
        state = self._state(words=[], hist=[self._VOCAB[0]])
        result = self._call(gu, state, None, _pdform([""]), self._meta(), prev_v=1)
        assert result == "*...*"
        assert state["words"][2][0] == [self._VOCAB[0]]
        assert state["hist"][2][0] == []


class TestNounParadigmDrillForm(_ParadigmDrillFormBase):
    _VOCAB = [{"form": "ὁ ἀγρός", "meaning": "field"}, {"form": "ἡ γυνή", "meaning": "woman"}]

    def _meta(self, active_cases=None, is_pt=False):
        import types
        return types.SimpleNamespace(
            active_cases=active_cases or [["sg", "nom"], ["sg", "gen"]],
            is_pluralia_tantum=is_pt,
        )

    def _call(self, gu, state, cv, form, noun_meta, **kwargs):
        return self._call_form(gu.noun_paradigm_drill_form, state, cv, form,
                               noun_meta=noun_meta, **kwargs)

    def test_done_shows_callout_and_restart(self, gu):
        state = self._state(words=[])
        result = self._call(gu, state, None, _pdform([]), self._meta())
        assert "callout" in str(result)

    def test_restart_click_resets_state(self, gu):
        state = self._state(
            words=[self._VOCAB[0]], hist=[self._VOCAB[1]], entered={"ὁ ἀγρός": ["x"]},
        )
        result = self._call(gu, state, self._VOCAB[0], _pdform([""]), self._meta(), restart_v=1)
        assert result == "*...*"
        self._assert_same_words(state["words"][2][0], self._VOCAB)
        assert state["hist"][2][0] == []
        assert state["entered"][2][0] == {}

    def test_correct_full_check_advances_and_saves(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_noun_test", return_value=(True, "")):
            result = self._call(gu, state, cv, _pdform(["ἀγρός", "ἀγροῦ"]), self._meta(), check_v=1)
        assert result == "*...*"
        assert cv not in state["words"][2][0]
        assert cv in state["hist"][2][0]
        assert state["entered"][2][0].get("ὁ ἀγρός") == ["ἀγρός", "ἀγροῦ"]

    def test_wrong_full_check_shows_feedback_no_advance(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_noun_test", return_value=(False, "❌ wrong")):
            result = self._call(gu, state, cv, _pdform(["asd", ""]), self._meta(), check_v=1)
        assert "❌ wrong" in str(result)
        assert cv in state["words"][2][0]

    def test_lang_reaches_check_noun_test(self, gu):
        # Same regression as verb_paradigm_drill_form -- noun_paradigm_drill_form
        # had no lang param at all before.
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_noun_test", return_value=(False, "")) as m:
            self._call(gu, state, cv, _pdform(["asd", ""]), self._meta(), check_v=1, lang="el")
        assert m.call_args.kwargs.get("lang") == "el"

    def test_nav_icons_hides_prev_with_no_history(self, gu):
        # nav_icons threads through to _paradigm_drill_form the same way as
        # verb -- see TestVerbParadigmDrillForm for the full row/hide battery.
        cv = self._VOCAB[0]
        state = self._state()
        result = self._call(gu, state, cv, _pdform(["", ""]), self._meta(), nav_icons=True)
        assert len(result[-2]) == 2

    def test_config_nav_icons_true_used_with_no_explicit_kwarg(self):
        gu = GreekUtils(_StubBackend(), _FormMo(), config=_NAV_ICONS_CONFIG)
        cv = self._VOCAB[0]
        state = self._state()
        result = self._call(gu, state, cv, _pdform(["", ""]), self._meta())
        assert len(result[-2]) == 2

    def test_show_prev_when_done_reaches_paradigm_drill_form(self, gu):
        # show_prev_when_done threads through the same way as nav_icons --
        # see TestVerbParadigmDrillForm for the full battery.
        state = self._state(words=[], hist=[self._VOCAB[0]])
        result = self._call(gu, state, None, _pdform([]), self._meta(), show_prev_when_done=True)
        assert isinstance(result[-1], list) and len(result[-1]) == 2

    def test_enter_on_correct_slot_advances_focus_using_active_cases(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["ἀγρός", ""], submit_count=1, enter_field_index=0)
        meta = self._meta(active_cases=[["sg", "nom"], ["sg", "gen"]])
        with patch.object(gu, "check_noun_slot", return_value=True) as mock_slot, \
             patch.object(gu, "check_noun_test", return_value=(False, "")):
            self._call(gu, state, cv, form, meta)
        assert form.widget.focus_request == {"request_id": 1, "advance_to": 1}
        mock_slot.assert_called_once_with(
            "ὁ ἀγρός", 0, "ἀγρός", article=True, active_cases=meta.active_cases, indefinite=False,
        )

    def test_noun_meta_omitted_falls_back_to_full_cases(self, gu):
        # REGRESSION: noun_meta used to be a required kwarg (and make_cap/
        # slot_ok used to additionally gate on `noun_meta is not None`,
        # unlike the sibling POS types) -- any caller that forgot to
        # compute/pass it crashed with TypeError. Omitting it now degrades
        # to the full, unfiltered config.noun_cells list instead, and
        # checking still works (not silently disabled).
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["ἀγρός", ""], submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_noun_slot", return_value=True) as mock_slot, \
             patch.object(gu, "check_noun_test", return_value=(False, "")):
            self._call_form(gu.noun_paradigm_drill_form, state, cv, form)
        assert form.widget.focus_request == {"request_id": 1, "advance_to": 1}
        mock_slot.assert_called_once_with(
            "ὁ ἀγρός", 0, "ἀγρός", article=True, active_cases=gu._cfg.noun_cells, indefinite=False,
        )

    def test_article_false_passed_to_check_noun_slot(self, gu):
        # article=False (e.g. a Modern Greek "simple" bare-noun mode toggle)
        # must reach check_noun_slot instead of the hardcoded True default.
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["ἀγρός", ""], submit_count=1, enter_field_index=0)
        meta = self._meta(active_cases=[["sg", "nom"], ["sg", "gen"]])
        with patch.object(gu, "check_noun_slot", return_value=True) as mock_slot, \
             patch.object(gu, "check_noun_test", return_value=(False, "")):
            self._call(gu, state, cv, form, meta, article=False)
        mock_slot.assert_called_once_with(
            "ὁ ἀγρός", 0, "ἀγρός", article=False, active_cases=meta.active_cases, indefinite=False,
        )

    def test_article_false_passed_to_check_noun_test(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_noun_test", return_value=(True, "")) as mock_test:
            self._call(gu, state, cv, _pdform(["ἀγρός", "ἀγροῦ"]), self._meta(), check_v=1, article=False)
        assert mock_test.call_args.kwargs.get("article") is False

    def test_indefinite_true_passed_to_check_noun_slot(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["ἀγρός", ""], submit_count=1, enter_field_index=0)
        meta = self._meta(active_cases=[["sg", "nom"], ["sg", "gen"]])
        with patch.object(gu, "check_noun_slot", return_value=True) as mock_slot, \
             patch.object(gu, "check_noun_test", return_value=(False, "")):
            self._call(gu, state, cv, form, meta, indefinite=True)
        mock_slot.assert_called_once_with(
            "ὁ ἀγρός", 0, "ἀγρός", article=True, active_cases=meta.active_cases, indefinite=True,
        )

    def test_indefinite_true_passed_to_check_noun_test(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_noun_test", return_value=(True, "")) as mock_test:
            self._call(gu, state, cv, _pdform(["ἀγρός", "ἀγροῦ"]), self._meta(), check_v=1, indefinite=True)
        assert mock_test.call_args.kwargs.get("indefinite") is True

    def test_indefinite_defaults_to_false(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_noun_test", return_value=(True, "")) as mock_test:
            self._call(gu, state, cv, _pdform(["ἀγρός", "ἀγροῦ"]), self._meta(), check_v=1)
        assert mock_test.call_args.kwargs.get("indefinite") is False

    def test_pluralia_tantum_snapshot_field_set(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["ἀγροί"], submit_count=1)
        meta = self._meta(active_cases=[["pl", "nom"]], is_pt=True)
        with patch.object(gu, "check_noun_test", return_value=(False, "")):
            self._call(gu, state, cv, form, meta)
        cap_snapshot = state["cap"][2][0]
        assert cap_snapshot.is_pluralia_tantum is True
        assert cap_snapshot.active_cases == [["pl", "nom"]]

    def test_next_button_persists_and_advances_regardless_of_correctness(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_noun_test", return_value=(False, "")):
            result = self._call(gu, state, cv, _pdform(["asd", ""]), self._meta(), nxt_v=1)
        assert result == "*...*"
        assert cv not in state["words"][2][0]
        assert cv in state["hist"][2][0]

    def test_prev_button_restores_previous_word(self, gu):
        prev_word = self._VOCAB[1]
        cv = self._VOCAB[0]
        state = self._state(hist=[prev_word])
        with patch.object(gu, "check_noun_test", return_value=(False, "")):
            result = self._call(gu, state, cv, _pdform(["", ""]), self._meta(), prev_v=1)
        assert result == "*...*"
        assert state["words"][2][0][0] == prev_word
        assert state["hist"][2][0] == []

    def test_custom_word_key(self, gu):
        cv = {"Word": "ὁ ἀγρός", "Translation": "field"}
        state = self._state(words=[cv])
        with patch.object(gu, "check_noun_test", return_value=(True, "")):
            result = self._call(
                gu, state, cv, _pdform(["ἀγρός", "ἀγροῦ"]), self._meta(),
                check_v=1, word_key="Word", meaning_key="Translation",
            )
        assert result == "*...*"
        assert state["entered"][2][0].get("ὁ ἀγρός") == ["ἀγρός", "ἀγροῦ"]


# ────────────────────────────────────────── rich marimo stub ──
#
# _StubMo.ui.array returns a plain list; plain lists reject attribute
# assignment, so create_noun/verb_test_ui fail on `noun_form.test_word = …`.
# _RichMo returns _RichForm — a SimpleNamespace-like object with a computed
# .value property — so attribute assignment works and .value reflects inputs.

class _RichText:
    def __init__(self, label=""):
        self.label = label
        self.value = ""


class _RichForm:
    """Attribute-settable container returned by _RichMo.ui.array."""
    def __init__(self, items):
        object.__setattr__(self, '_items', items)

    @property
    def value(self):
        return [t.value for t in object.__getattribute__(self, '_items')]

    def __setattr__(self, name, val):
        object.__setattr__(self, name, val)

    def __len__(self):
        return len(object.__getattribute__(self, '_items'))

    def __iter__(self):
        return iter(object.__getattribute__(self, '_items'))


class _RichMo:
    class ui:
        @staticmethod
        def text(label=""): return _RichText(label)
        @staticmethod
        def array(items): return _RichForm(items)
    @staticmethod
    def md(s): return s


# ────────────────────────────────────────── create_noun_test_ui ──

class TestCreateNounTestUi:
    _WORD = {"Word": "ὁ ἀγρός", "Translation": "field"}

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _RichMo(), config=ANCIENT_GREEK)

    @pytest.fixture
    def gu_mg(self):
        return GreekUtils(_StubBackend(), _RichMo())

    def test_empty_list_returns_all_none(self, gu):
        w, tr, form = gu.create_noun_test_ui([])
        assert w is None and tr is None and form is None

    def test_basic_form_created(self, gu):
        w, tr, form = gu.create_noun_test_ui([self._WORD])
        assert w == "ὁ ἀγρός"
        assert tr == "field"
        assert form is not None

    def test_test_word_attribute_set(self, gu):
        _, _, form = gu.create_noun_test_ui([self._WORD])
        assert form.test_word == "ὁ ἀγρός"

    def test_active_cases_attribute_set(self):
        # _StubBackend (this class's shared `gu` fixture) returns {} for
        # every word, so "ὁ ἀγρός" would look pluralia tantum via the
        # no-singular-data fallback -- but its article "ὁ" is a SINGULAR
        # one, not a genuine plural marker, so active_cases now correctly
        # comes back empty rather than trusting an unverified guess (same
        # principle as the 2026-08-18 pluralia-tantum fix). Use a backend
        # with real singular data instead, so this test verifies what it's
        # actually meant to: a normal, well-formed word gets a non-empty
        # active_cases via the ordinary (non-pluralia-tantum) path.
        class _RealSingularBackend:
            def paradigm(self, word, pos):
                return {"masc": {"sg": {"nom": {word}}}}
        gu = GreekUtils(_RealSingularBackend(), _RichMo(), config=ANCIENT_GREEK)
        _, _, form = gu.create_noun_test_ui([self._WORD])
        assert isinstance(form.active_cases, list)
        assert len(form.active_cases) > 0

    def test_value_initially_empty_strings(self, gu):
        _, _, form = gu.create_noun_test_ui([self._WORD])
        assert all(v == "" for v in form.value)
        assert len(form.value) == len(form.active_cases)

    def test_pluralia_tantum_detected_from_article(self, gu):
        # "οἱ" is a plural article in AG → is_pluralia_tantum=True
        # → active_cases contains only plural cells
        pt_word = {"Word": "οἱ νόμοι", "Translation": "laws"}
        _, _, form = gu.create_noun_test_ui([pt_word])
        assert form.is_pluralia_tantum is True
        assert all(c[0] == 'pl' for c in form.active_cases)

    def test_mode_full_adds_indefinite_labels_mg(self):
        # MG has indef_articles → mode='full' produces Def. + Ind. labels.
        # _StubBackend returns {} so every word looks like pluralia tantum (no sg
        # nom forms → is_pt=True → only pl cells → no Ind. labels).  Use a
        # backend stub that returns a form for sg nom so the noun is treated as
        # regular and sg cells are included. lang="en" pins the prefix text this
        # test checks -- create_noun_test_ui's own default is "ru" (see the
        # lang_ru sibling test below), matching the rest of this file.
        class _NounBackend:
            def paradigm(self, word, pos):
                # noun paradigm layout: {gender: {num: {case: set}}}
                return {"masc": {"sg": {"nom": {word}, "acc": {word}, "gen": {word}, "dat": {word}},
                                 "pl": {"nom": {word}, "acc": {word}, "gen": {word}, "dat": {word}}}}
        gu = GreekUtils(_NounBackend(), _RichMo())
        mg_word = {"Word": "λόγος", "Translation": "word"}
        _, _, form = gu.create_noun_test_ui([mg_word], mode='full', lang="en")
        labels = [t.label for t in form]
        assert any("Def." in l for l in labels)
        assert any("Ind." in l for l in labels)

    def test_mode_full_labels_default_to_ru(self):
        # Regression: create_noun_test_ui used to hardcode "Def."/"Ind." (and
        # noun_slot_labels' own "en" default for the case labels themselves)
        # regardless of what language the notebook was actually using.
        class _NounBackend:
            def paradigm(self, word, pos):
                return {"masc": {"sg": {"nom": {word}, "acc": {word}, "gen": {word}, "dat": {word}},
                                 "pl": {"nom": {word}, "acc": {word}, "gen": {word}, "dat": {word}}}}
        gu = GreekUtils(_NounBackend(), _RichMo())
        mg_word = {"Word": "λόγος", "Translation": "word"}
        _, _, form = gu.create_noun_test_ui([mg_word], mode='full')
        labels = [t.label for t in form]
        assert any("Опр." in l for l in labels)
        assert any("Неопр." in l for l in labels)
        assert not any("Def." in l or "Ind." in l for l in labels)

    def test_simple_mode_no_def_ind_prefix(self, gu):
        _, _, form = gu.create_noun_test_ui([self._WORD], mode='simple')
        labels = [t.label for t in form]
        assert not any("Def." in l or "Ind." in l for l in labels)


class TestNounDrillMeta:
    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _RichMo(), config=ANCIENT_GREEK)

    def test_matches_create_noun_test_ui_attributes(self, gu):
        _, _, form = gu.create_noun_test_ui([{"Word": "ὁ ἀγρός", "Translation": "field"}])
        meta = gu.noun_drill_meta("ὁ ἀγρός")
        assert meta.active_cases == form.active_cases
        assert meta.is_pluralia_tantum == form.is_pluralia_tantum

    def test_pluralia_tantum_from_plural_article(self, gu):
        meta = gu.noun_drill_meta("οἱ νόμοι")
        assert meta.is_pluralia_tantum is True
        assert all(c[0] == 'pl' for c in meta.active_cases)

    def test_pluralia_tantum_via_missing_data_but_non_plural_article_gets_no_cells(self, gu):
        # "ὁ ἀγρός" against a backend with NO data at all: is_pluralia_tantum
        # becomes True via the "no singular data" fallback, but "ὁ" is a
        # SINGULAR article, not a genuine plural marker -- there's no real
        # evidence nw is even shaped like a plural, so nothing is offered
        # rather than trusting an unverified guess (same principle as the
        # 2026-08-18 pluralia-tantum fix: never assert an answer that
        # wasn't actually confirmed).
        meta = gu.noun_drill_meta("ὁ ἀγρός")
        assert meta.is_pluralia_tantum is True
        assert meta.active_cases == []

    def test_excludes_cell_when_backend_form_is_blank(self):
        # A backend can return {''} for a cell it has no data for (a real,
        # deliberate sentinel -- e.g. modern-greek-inflexion-eee's
        # without_gen_pl exceptions), not just an empty set. That cell must
        # be excluded from active_cases the same way a truly empty set is.
        class _BlankGenPlBackend:
            def paradigm(self, word, pos):
                return {"fem": {"sg": {"nom": {word}, "acc": {word}, "gen": {word + "ς"}},
                                 "pl": {"nom": {word + "ες"}, "acc": {word + "ες"}, "gen": {''}}}}
        gu = GreekUtils(_BlankGenPlBackend(), _RichMo(), config=MODERN_GREEK)
        meta = gu.noun_drill_meta("η δοκιμή")
        assert ('pl', 'gen') not in meta.active_cases
        assert ('pl', 'nom') in meta.active_cases
        assert meta.is_pluralia_tantum is False


class TestPluraliaTantumNomPlUsesSurfaceForm:
    """REGRESSION (2026-08-18): a pluralia-tantum noun's own (pl, nom)
    check must use its TSV-given surface form directly, not re-derive it
    through the backend as if that surface form were a lemma.
    """

    @pytest.fixture
    def gu(self):
        # 'σκουπίδι' -> the real paradigm. 'σκουπίδια' -> what the real
        # backend actually does when handed the plural surface form as if
        # it were itself a lemma (found 2026-08-18, created_with_eee
        # chapter_07's "τα σκουπίδια"): matches its "-ία" ending like
        # "κυρία -> κυρίες" and "inflects" from there, fabricating a wrong
        # "plural of that".
        backend = _FakeParadigmBackend({
            ('σκουπίδι', 'noun'): {"neut": {"sg": {"nom": {"σκουπίδι"}},
                                             "pl": {"nom": {"σκουπίδια"}, "acc": {"σκουπίδια"}, "gen": {"σκουπιδιών"}}}},
            ('σκουπίδια', 'noun'): {"fem": {"sg": {"nom": {"σκουπίδια"}},
                                             "pl": {"nom": {"σκουπίδιες"}, "acc": {"σκουπίδιες"}, "gen": {"σκουπιδιών"}}}},
        })
        return GreekUtils(backend, _RichMo(), config=MODERN_GREEK)

    def test_active_cases_includes_neuter_acc_and_gen_plural(self, gu):
        # Nom is always answerable (nw itself). Acc joins for free (Modern
        # Greek neuter Nom = Acc = Voc always). Gen joins too because the
        # stub's "σκουπίδι" candidate round-trips AND has real gen-plural
        # data ("σκουπιδιών") -- see _noun_pt_genitive_plural.
        _, _, form = gu.create_noun_test_ui([{"Word": "τα σκουπίδια", "Translation": "garbage"}])
        assert form.is_pluralia_tantum is True
        assert form.active_cases == [('pl', 'nom'), ('pl', 'acc'), ('pl', 'gen')]

    def test_check_noun_test_accepts_all_three_correct_forms(self, gu):
        word = "τα σκουπίδια"
        _, _, form = gu.create_noun_test_ui([{"Word": word, "Translation": "garbage"}])
        nom, acc, gen = list(form)
        nom.value, acc.value, gen.value = "σκουπίδια", "σκουπίδια", "σκουπιδιών"
        ok, feedback = gu.check_noun_test(word, form)
        assert ok is True, feedback

    def test_check_noun_test_rejects_the_backends_fabricated_nom(self, gu):
        # Without the fix, "σκουπίδιες" (the backend's wrong guess) is what
        # gets accepted instead -- assert the corrected checker no longer
        # takes it, i.e. the real fabricated bug output is rejected too.
        # Acc/Gen filled in correctly so only the Nom slot is under test.
        word = "τα σκουπίδια"
        _, _, form = gu.create_noun_test_ui([{"Word": word, "Translation": "garbage"}])
        nom, acc, gen = list(form)
        nom.value, acc.value, gen.value = "σκουπίδιες", "σκουπίδια", "σκουπιδιών"
        ok, feedback = gu.check_noun_test(word, form, lang="en")
        assert ok is False
        assert "must be **σκουπίδια**" in feedback  # states the real correct answer

    def test_check_noun_slot_accepts_the_correct_surface_form(self, gu):
        word = "τα σκουπίδια"
        active_cases = [('pl', 'nom'), ('pl', 'acc'), ('pl', 'gen')]
        assert gu.check_noun_slot(word, 0, "σκουπίδια", active_cases=active_cases) is True
        assert gu.check_noun_slot(word, 1, "σκουπίδια", active_cases=active_cases) is True
        assert gu.check_noun_slot(word, 2, "σκουπιδιών", active_cases=active_cases) is True

    def test_check_noun_slot_rejects_the_backends_fabricated_form(self, gu):
        word = "τα σκουπίδια"
        active_cases = [('pl', 'nom'), ('pl', 'acc'), ('pl', 'gen')]
        assert gu.check_noun_slot(word, 0, "σκουπίδιες", active_cases=active_cases) is False


class TestPluraliaTantumMascFemNoGuessing:
    """A masculine/feminine pluralia-tantum noun (article "οι") must stay
    Nom-Pl-only -- its singular can't be safely recovered from the plural
    the way a neuter one's can (see _noun_pt_genitive_plural's docstring).
    """

    @pytest.fixture
    def gu(self):
        # "κανόνες" round-trips against both a masculine ("κανόνας") and a
        # feminine-shaped ("κανόνα") candidate singular, but the two
        # disagree on genitive plural -- exactly the real case (2026-08-18)
        # that rules out guessing a singular lemma for masculine/feminine
        # pluralia-tantum nouns, unlike neuter ones.
        backend = _FakeParadigmBackend({
            ('κανόνας', 'noun'): {"masc": {"sg": {"nom": {"κανόνας"}},
                                            "pl": {"nom": {"κανόνες"}, "acc": {"κανόνες"}, "gen": {"κανόνων"}}}},
            ('κανόνα', 'noun'): {"fem": {"sg": {"nom": {"κανόνα"}},
                                          "pl": {"nom": {"κανόνες"}, "acc": {"κανόνες"}, "gen": {"κανονών"}}}},
        })
        return GreekUtils(backend, _RichMo(), config=MODERN_GREEK)

    def test_active_cases_stays_nom_only(self, gu):
        _, _, form = gu.create_noun_test_ui([{"Word": "οι κανόνες", "Translation": "rules"}])
        assert form.is_pluralia_tantum is True
        assert form.active_cases == [('pl', 'nom')]


class TestPluraliaTantumNeuterAccGeneralizesToAncientGreek:
    """The (pl, acc) = (pl, nom) rule for neuter pluralia-tantum nouns
    isn't Modern-Greek-specific -- Nom = Acc = Voc holds for any Greek
    neuter noun, and _AG_ARTS's neuter table has the same article ("τά")
    for both nom and acc. The genitive-plural candidate-lemma guess
    (stripping a trailing vowel) IS Modern-Greek-shaped though, and
    correctly does NOT fire here -- "ὅπλα" strips to "ὅπλ", not the real
    singular "ὅπλον", so the round-trip check in _noun_pt_genitive_plural
    fails and genitive plural is correctly left untested rather than
    guessed wrong.
    """

    @pytest.fixture
    def gu(self):
        backend = _FakeParadigmBackend({
            ('ὅπλον', 'noun'): {"neut": {"sg": {"nom": {"ὅπλον"}},
                                          "pl": {"nom": {"ὅπλα"}, "acc": {"ὅπλα"}, "gen": {"ὅπλων"}}}},
        })
        return GreekUtils(backend, _RichMo(), config=ANCIENT_GREEK)

    def test_active_cases_includes_acc_but_not_gen(self, gu):
        _, _, form = gu.create_noun_test_ui([{"Word": "τά ὅπλα", "Translation": "weapons"}])
        assert form.is_pluralia_tantum is True
        assert form.active_cases == [('pl', 'nom'), ('pl', 'acc')]

    def test_check_noun_test_accepts_the_correct_surface_form_for_both(self, gu):
        word = "τά ὅπλα"
        _, _, form = gu.create_noun_test_ui([{"Word": word, "Translation": "weapons"}])
        nom, acc = list(form)
        nom.value, acc.value = "ὅπλα", "ὅπλα"
        ok, feedback = gu.check_noun_test(word, form)
        assert ok is True, feedback


class TestPluraliaTantumGuards:
    """The pluralia-tantum helpers must not guess a form they cannot vouch for."""

    @pytest.fixture
    def gu(self):
        # "άνθ" would validate as the singular of "άνθη" if a candidate were ever guessed for an -η ending
        backend = _FakeParadigmBackend({
            ('άνθ', 'noun'): {"neut": {"sg": {"nom": {"άνθ"}},
                                        "pl": {"nom": {"άνθη"}, "gen": {"άνθων"}}}},
        })
        return GreekUtils(backend, _StubMo(), config=MODERN_GREEK)

    def test_word_without_an_article_is_never_answered_verbatim(self, gu):
        # no plural article vouches that the word is itself the plural form
        assert gu.noun_drill_meta("σκουπίδια").active_cases == []

    def test_no_singular_candidate_unless_the_plural_ends_in_alpha(self, gu):
        assert gu._noun_pt_candidate_lemma("άνθη") is None
        assert gu._noun_pt_candidate_lemma("α") is None

    def test_neuter_plural_without_a_candidate_singular_gets_no_genitive(self, gu):
        assert gu.noun_drill_meta("τα άνθη").active_cases == [('pl', 'nom'), ('pl', 'acc')]


class TestNounSlotLabels:
    def test_formats_number_and_case(self):
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.noun_slot_labels([("sg", "nom"), ("pl", "gen")]) == ["Nom. Sg.:", "Gen. Pl.:"]

    def test_unknown_keys_pass_through(self):
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.noun_slot_labels([("du", "abl")]) == ["abl Du.:"]

    def _gu(self):
        from modern_greek_backend_eee import ModernGreekBackend
        be = ModernGreekBackend()
        return GreekUtils(be, mo_module=_StubMo(), eee_module=be, config=MODERN_GREEK)

    def test_lang_en_matches_default_fallback_order(self):
        # real get_slot_templates path (not the no-eee_module fallback), lang="en"
        gu = self._gu()
        assert gu.noun_slot_labels([("sg", "nom"), ("pl", "gen")]) == ["Nom. Sg.:", "Gen. Pl.:"]

    def test_lang_ru(self):
        gu = self._gu()
        assert gu.noun_slot_labels([("sg", "nom"), ("pl", "gen")], lang="ru") == ["Именит. ед.:", "Родит. мн.:"]

    def test_lang_el(self):
        gu = self._gu()
        assert gu.noun_slot_labels([("sg", "nom"), ("pl", "gen")], lang="el") == ["Ονομ. εν.:", "Γεν. πλ.:"]


class TestAdjectiveSlotLabelsLang:
    """lang= localization specifically -- see TestAdjectiveSlotLabels below
    for structural coverage (count/order) against a stub backend."""

    def _gu(self):
        from modern_greek_backend_eee import ModernGreekBackend
        be = ModernGreekBackend()
        return GreekUtils(be, mo_module=_StubMo(), eee_module=be, config=MODERN_GREEK)

    def test_simple_mode_lang_en(self):
        gu = self._gu()
        labels = gu.adjective_slot_labels("simple")
        assert labels[0] == "Nom. Sg. m.:"
        assert labels[3] == "Nom. Pl. m.:"

    def test_simple_mode_lang_ru(self):
        gu = self._gu()
        labels = gu.adjective_slot_labels("simple", lang="ru")
        assert labels[0] == "Именит. ед. м.:"

    def test_simple_mode_lang_el(self):
        gu = self._gu()
        labels = gu.adjective_slot_labels("simple", lang="el")
        assert labels[0] == "Ονομ. εν. αρ.:"

    def test_no_eee_module_falls_back_unchanged(self):
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.adjective_slot_labels("simple")[0] == "m. Sg:"

    def test_backend_without_real_labels_falls_back_not_raw_tag(self):
        # REGRESSION: ancient_greek_backend_eee's get_slot_templates() never
        # resolves terms_lang (label == tag by its own docstring/contract) --
        # confirmed live once in examples/greek_exercise_notebook.py, where
        # this produced ".NSM:" etc. instead of a real label. noun_slot_labels
        # never hit this (its 2-key Case+Number lookup never matches this
        # backend's always-3-key Case+Number+Gender features, so it always
        # fell through to the dict fallback by accident) -- only the
        # adjective path's 3-key lookup actually matched and leaked the tag.
        from ancient_greek_backend_eee import AncientGreekBackend
        be = AncientGreekBackend()
        gu = GreekUtils(be, mo_module=_StubMo(), eee_module=be, config=ANCIENT_GREEK)
        labels = gu.adjective_slot_labels("simple")
        assert labels[0] == "m. Sg:"
        assert not any(lbl.startswith(".") for lbl in labels)


class TestNounIndefCells:
    """Unit tests for GreekUtils.noun_indef_cells — the shared singular-only
    filter used by create_noun_test_ui, check_noun_test, check_noun_slot,
    and notebooks building an indefinite=True label list."""

    def test_filters_to_singular_only(self):
        gu = GreekUtils(mo_module=_StubMo())  # default config is MODERN_GREEK
        cells = [("sg", "nom"), ("sg", "acc"), ("pl", "nom"), ("pl", "acc")]
        assert gu.noun_indef_cells(cells) == [("sg", "nom"), ("sg", "acc")]

    def test_empty_input_returns_empty(self):
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.noun_indef_cells([]) == []

    def test_no_op_without_config_indef_articles(self):
        # ANCIENT_GREEK has indef_articles=None -- no indefinite article
        # exists, so no cells qualify, singular or not.
        gu = GreekUtils(mo_module=_StubMo(), config=ANCIENT_GREEK)
        cells = [("sg", "nom"), ("sg", "acc"), ("pl", "nom")]
        assert gu.noun_indef_cells(cells) == []


class TestVerbSlotLabels:
    def test_labels_from_config_with_colons(self):
        gu = GreekUtils(mo_module=_StubMo(), config=ANCIENT_GREEK)
        labels = gu.verb_slot_labels()
        assert labels == [f"{lbl}:" for lbl in ANCIENT_GREEK.verb_labels]
        assert len(labels) == len(ANCIENT_GREEK.verb_slots)

    def test_active_slots_restricts_and_reorders(self):
        gu = GreekUtils(mo_module=_StubMo(), config=ANCIENT_GREEK)
        by_slot = dict(zip(ANCIENT_GREEK.verb_slots, ANCIENT_GREEK.verb_labels))
        active = [ANCIENT_GREEK.verb_slots[2], ANCIENT_GREEK.verb_slots[0]]
        assert gu.verb_slot_labels(active) == [f"{by_slot[s]}:" for s in active]


class TestVerbDrillMeta:
    @staticmethod
    def _paradigm_fn(word, pos):
        if pos != "verb":
            return {}
        # sg.ter ("λύει") deliberately blank -- same {''} sentinel a real
        # backend can return for a slot it has no data for.
        return {"present": {"active": {"ind": {
            "sg": {"pri": {"λύω"}, "sec": {"λύεις"}, "ter": {''}},
            "pl": {"pri": {"λύομεν"}, "sec": {"λύετε"}, "ter": {"λύουσι"}},
        }}}}

    def test_excludes_slot_when_backend_form_is_blank(self):
        gu = GreekUtils(_StubBackend(self._paradigm_fn), _StubMo(), config=ANCIENT_GREEK)
        meta = gu.verb_drill_meta("λύω", "present")
        assert ("sg", "ter") not in meta.active_slots
        assert ("sg", "pri") in meta.active_slots

    def test_falls_back_to_full_slots_when_backend_has_no_data(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)  # always {}
        meta = gu.verb_drill_meta("ἄγνωστον", "present")
        assert meta.active_slots == ANCIENT_GREEK.verb_slots


class TestVerbDrillMetaDefectiveFallback:
    """A verb with no perfective/aorist stem at all (είμαι-class: no distinct
    "future"/"subjunctive_simple"/"conditional_simple") must fall back to its
    continuous-tense (present-based) forms across every person, not
    verb_drill_meta's blind "no data anywhere -> show every slot unfiltered"
    fallback -- that fallback produces an unanswerable test, since the
    backend still has nothing to compare a submitted answer against. See
    GreekConfig.defective_fallback / _MG_DEFECTIVE_FALLBACK."""

    @staticmethod
    def _eimai_paradigm_fn(word, pos):
        if pos != "verb":
            return {}
        # deliberately no "conjunctive" key at all -- είμαι genuinely has none
        return {"present": {"active": {"ind": {
            "sg": {"pri": {"είμαι"}, "sec": {"είσαι"}, "ter": {"είναι"}},
            "pl": {"pri": {"είμαστε"}, "sec": {"είστε", "είσαστε"}, "ter": {"είναι"}},
        }}}}

    def test_future_falls_back_to_all_persons_with_present_based_forms(self):
        gu = GreekUtils(_StubBackend(self._eimai_paradigm_fn), _StubMo(), config=MODERN_GREEK)
        meta = gu.verb_drill_meta("είμαι", "future")
        assert meta.active_slots == MODERN_GREEK.verb_slots
        assert gu._verb_forms("είμαι", "future", "pri", "sg") == {"είμαι"}
        assert gu._verb_forms("είμαι", "future", "ter", "pl") == {"είναι"}

    def test_check_verb_slot_accepts_continuous_based_answer(self):
        gu = GreekUtils(_StubBackend(self._eimai_paradigm_fn), _StubMo(), config=MODERN_GREEK)
        meta = gu.verb_drill_meta("είμαι", "future")
        assert gu.check_verb_slot("είμαι", "future", 0, "θα είμαι", active_slots=meta.active_slots)
        assert not gu.check_verb_slot("είμαι", "future", 0, "θα ήμουν", active_slots=meta.active_slots)

    def test_non_defective_verb_unaffected(self):
        """A verb WITH real conjunctive data must never hit the fallback --
        confirms defective_fallback only engages when a tense is genuinely
        empty, not merely because one caller asked before the other."""
        def paradigm_fn(word, pos):
            if pos != "verb":
                return {}
            return {"conjunctive": {"active": {"ind": {
                "sg": {"pri": {"τρέξω"}, "sec": {"τρέξεις"}, "ter": {"τρέξει"}},
                "pl": {"pri": {"τρέξουμε"}, "sec": {"τρέξετε"}, "ter": {"τρέξουν"}},
            }}}}
        gu = GreekUtils(_StubBackend(paradigm_fn), _StubMo(), config=MODERN_GREEK)
        assert gu._verb_forms("τρέχω", "future", "pri", "sg") == {"τρέξω"}


# ────────────────────────────────────────── create_verb_test_ui ──

class TestCreateVerbTestUi:
    _VERB = {"Word": "λύω", "Translation": "I loosen"}
    _WORDS = [{"Word": "λύω", "Translation": "I loosen"}]

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _RichMo(), config=ANCIENT_GREEK)

    def test_no_current_verb_returns_none_form(self, gu):
        form, md = gu.create_verb_test_ui("Test", self._WORDS, self._WORDS, None, "present")
        assert form is None

    def test_basic_form_created(self, gu):
        form, md = gu.create_verb_test_ui("Test", self._WORDS, self._WORDS, self._VERB, "present")
        assert form is not None

    def test_verb_word_attribute_set(self, gu):
        form, _ = gu.create_verb_test_ui("Test", self._WORDS, self._WORDS, self._VERB, "present")
        assert form.verb_word == "λύω"

    def test_form_has_six_slots(self, gu):
        # _StubBackend has no data at all -- verb_drill_meta falls back to
        # the full slot list rather than showing an empty form.
        form, _ = gu.create_verb_test_ui("Test", self._WORDS, self._WORDS, self._VERB, "present")
        assert len(form.value) == 6  # 3 sg + 3 pl slots

    def test_value_initially_empty(self, gu):
        form, _ = gu.create_verb_test_ui("Test", self._WORDS, self._WORDS, self._VERB, "present")
        assert all(v == "" for v in form.value)

    def test_empty_words4test_shows_default_message(self, gu):
        form, md = gu.create_verb_test_ui("Test", self._WORDS, [], self._VERB, "present")
        # form still created but md_view is the empty-list message
        assert form is not None
        assert "Test" in md   # title appears in default message

    def test_words4test_given_md_contains_translation(self, gu):
        _, md = gu.create_verb_test_ui("Test", self._WORDS, self._WORDS, self._VERB, "present")
        assert "I loosen" in md

    def test_excludes_slot_with_blank_backend_form(self):
        gu = GreekUtils(_StubBackend(TestVerbDrillMeta._paradigm_fn), _RichMo(), config=ANCIENT_GREEK)
        form, _ = gu.create_verb_test_ui("Test", self._WORDS, self._WORDS, self._VERB, "present")
        assert len(form.value) == 5  # sg.ter excluded
        assert ("sg", "ter") not in form.active_slots

    def test_snapshot_of_excluded_slot_form_does_not_crash_check(self):
        # Regression: make_snapshot used to drop active_slots (missing from
        # its attribute allowlist), so a snapshot of a form with a genuinely
        # excluded slot fell back to the full slot list in check_verb_test,
        # indexing form.value (5 entries) with an index meant for 6 slots --
        # IndexError. The full create_verb_test_ui -> make_snapshot ->
        # check_verb_test pipeline, not just make_snapshot in isolation.
        gu = GreekUtils(_StubBackend(TestVerbDrillMeta._paradigm_fn), _RichMo(), config=ANCIENT_GREEK)
        form, _ = gu.create_verb_test_ui("Test", self._WORDS, self._WORDS, self._VERB, "present")
        for item, val in zip(form, ["λύω", "λύεις", "λύομεν", "λύετε", "λύουσι"]):
            item.value = val
        snap = gu.make_snapshot(form, verb_word="λύω", tense="present")
        ok, _ = gu.check_verb_test("λύω", snap, "present")
        assert ok is True


# ────────────────────────────────────────── paste fix in ESM strings ──

@pytest.mark.parametrize("esm", [_DIA_ESM, _PARA_ESM], ids=["dia", "para"])
class TestDiacriticsEsmPasteFix:
    """Both diacritics ESM templates must allow only insertText/insertCompositionText."""

    def test_has_paste_guard(self, esm):
        assert "insertText" in esm
        assert "insertCompositionText" in esm

    def test_has_mobile_form_submit_fallback(self, esm):
        """Both widgets must wrap their input(s) in a <form> with a submit
        listener — desktop Enter fires via keydown, but mobile virtual
        keyboards' "Go"/"Enter" action only fires a form submit event, not
        a keydown."""
        assert "createElement('form')" in esm
        assert "addEventListener('submit'" in esm

# ──────────────────────────────── ConfigStore additions ──

class TestConfigStoreAdditional:
    def test_from_url_github_host_rewrites_fetch_url(self, monkeypatch):
        # Verify ConfigStore.from_url() benefits from host-rewriting: when served from
        # GitHub, a Codeberg-shaped index URL is rewritten to GitHub before fetch.
        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.github.io")
        seen = []

        def fake_urlopen(url, timeout=None):
            seen.append(url)
            return _make_resp(b"nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            cfg = ConfigStore.from_url(
                "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main/index.tsv"
            )
        assert cfg.lessons() == []  # No lessons (empty TSV after header)
        # Verify the URL was rewritten from Codeberg to raw.githubusercontent.com before fetching
        assert len(seen) == 1
        assert "raw.githubusercontent.com" in seen[0]
        assert "EEE-project/created_with_eee" in seen[0]
        assert "codeberg.org" not in seen[0]

    def test_from_url_exception_empties_lessons(self):
        with patch("urllib.request.urlopen", side_effect=Exception("timeout")):
            cfg = ConfigStore.from_url("https://example.com/index.tsv")
        assert cfg.lessons() == []
        assert cfg.ga_config() is None
        assert cfg.raw_base == "https://example.com"

    def test_raw_base_none_from_dict(self):
        cfg = ConfigStore.from_dict(_SAMPLE_LESSONS)
        assert cfg.raw_base is None

    def test_nb_remote_raises_without_raw_base(self):
        cfg = ConfigStore.from_dict(_SAMPLE_LESSONS)
        with pytest.raises(RuntimeError, match="no remote base"):
            cfg.nb_remote("2026_06_09")

    def test_nb_remote_plain_name(self):
        _tsv = "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
        with patch("urllib.request.urlopen", return_value=_make_resp(_tsv.encode())):
            cfg = ConfigStore.from_url("https://raw.example.com/repo/main/index.tsv")
        assert cfg.nb_remote("2026_06_09") == "https://raw.example.com/repo/main/2026_06_09"

    def test_nb_remote_file_path(self, tmp_path):
        _tsv = "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
        with patch("urllib.request.urlopen", return_value=_make_resp(_tsv.encode())):
            cfg = ConfigStore.from_url("https://raw.example.com/repo/main/index.tsv")
        nb = str(tmp_path / "2026_06_09" / "notebook.py")
        assert cfg.nb_remote(nb) == "https://raw.example.com/repo/main/2026_06_09"

    def test_parse_tsv_preserves_extra_columns(self):
        _tsv = (
            "nb_id\ticon\tgreek\tlabel_ru\tlabel_el\ttitle_ru\tdesc_ru\n"
            "nb_AAA\tΑ\tΔίδαγμα α'\tЗанятие 1\tΜάθημα 1\tАлфавит\tБуквы\n"
        )
        with patch("urllib.request.urlopen", return_value=_make_resp(_tsv.encode("utf-8"))):
            cfg = ConfigStore.from_url("https://example.com/index.tsv")
        row = cfg.lessons()[0]
        assert row["label_ru"] == "Занятие 1"
        assert row["label_el"] == "Μάθημα 1"
        assert row["title_ru"] == "Алфавит"

    def test_from_file_or_url_prefers_local(self, tmp_path):
        (tmp_path / "index.tsv").write_text(
            "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
            "nb_LOCAL\tΑ\t\t\t\t\thttps://example.com/\n",
            encoding="utf-8",
        )
        with patch("urllib.request.urlopen", side_effect=AssertionError("should not hit network")):
            cfg = ConfigStore.from_file_or_url(tmp_path, "https://example.com/index.tsv")
        assert len(cfg.lessons()) == 1
        assert cfg.lessons()[0]["nb_id"] == "nb_LOCAL"

    def test_from_file_or_url_falls_back_to_remote(self, tmp_path):
        _tsv = (
            "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
            "nb_REMOTE\tΑ\t\t\t\t\thttps://example.com/\n"
        )
        with patch("urllib.request.urlopen", return_value=_make_resp(_tsv.encode("utf-8"))):
            cfg = ConfigStore.from_file_or_url(tmp_path, "https://example.com/index.tsv")
        assert len(cfg.lessons()) == 1
        assert cfg.lessons()[0]["nb_id"] == "nb_REMOTE"

    def test_from_file_or_url_raw_base_from_url_even_when_local(self, tmp_path):
        (tmp_path / "index.tsv").write_text(
            "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n", encoding="utf-8"
        )
        with patch("urllib.request.urlopen", side_effect=AssertionError("should not hit network")):
            cfg = ConfigStore.from_file_or_url(tmp_path, "https://raw.example.com/repo/main/index.tsv")
        assert cfg.raw_base == "https://raw.example.com/repo/main"
        assert cfg.nb_remote("2026_06_09") == "https://raw.example.com/repo/main/2026_06_09"

    def test_from_file_or_url_preserves_extra_columns_locally(self, tmp_path):
        (tmp_path / "index.tsv").write_text(
            "nb_id\ticon\tgreek\tlabel_ru\tlabel_el\ttitle_ru\tdesc_ru\n"
            "nb_AAA\tΑ\tΔίδαγμα α'\tЗанятие 1\tΜάθημα 1\tАлфавит\tБуквы\n",
            encoding="utf-8",
        )
        with patch("urllib.request.urlopen", side_effect=AssertionError("should not hit network")):
            cfg = ConfigStore.from_file_or_url(tmp_path, "https://example.com/index.tsv")
        row = cfg.lessons()[0]
        assert row["label_ru"] == "Занятие 1"
        assert row["title_ru"] == "Алфавит"

    def test_from_file_or_url_parent_lookup(self, tmp_path):
        subdir = tmp_path / "2026_06_09"
        subdir.mkdir()
        (tmp_path / "index.tsv").write_text(
            "nb_id\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
            "nb_AAA\tΑ\t\t\t\t\thttps://example.com/\n",
            encoding="utf-8",
        )
        nb_file = subdir / "notebook.py"
        nb_file.write_text("")
        with patch("urllib.request.urlopen", side_effect=AssertionError("should not hit network")):
            cfg = ConfigStore.from_file_or_url(nb_file, "https://example.com/index.tsv")
        assert cfg.index_url() == "https://example.com/"


_CHAPTER_LESSONS = [
    {"url": "chapter_01/", "index_url": "/course/"},
    {"url": "chapter_02/", "index_url": "/course/"},
    {"url": "chapter_04/", "index_url": "/course/"},  # chapter_03 is skipped
]


class TestConfigStoreAdjacentUrls:
    def test_middle_row_has_both_neighbors(self):
        # Also covers the gap: no row for chapter_03, so chapter_02's next
        # must be chapter_04, never a naively-incremented "chapter_03".
        cfg = ConfigStore.from_dict(_CHAPTER_LESSONS)
        prev_url, next_url = cfg.adjacent_urls("chapter_02/")
        assert prev_url == "/course/chapter_01/"
        assert next_url == "/course/chapter_04/"

    def test_first_row_has_no_prev(self):
        cfg = ConfigStore.from_dict(_CHAPTER_LESSONS)
        prev_url, next_url = cfg.adjacent_urls("chapter_01/")
        assert prev_url is None
        assert next_url == "/course/chapter_02/"

    def test_last_row_has_no_next(self):
        cfg = ConfigStore.from_dict(_CHAPTER_LESSONS)
        prev_url, next_url = cfg.adjacent_urls("chapter_04/")
        assert prev_url == "/course/chapter_02/"
        assert next_url is None

    def test_trailing_slash_optional_on_own_url(self):
        cfg = ConfigStore.from_dict(_CHAPTER_LESSONS)
        assert cfg.adjacent_urls("chapter_02") == cfg.adjacent_urls("chapter_02/")

    def test_unknown_own_url_returns_none_none(self):
        cfg = ConfigStore.from_dict(_CHAPTER_LESSONS)
        assert cfg.adjacent_urls("chapter_99/") == (None, None)

    def test_empty_lessons_returns_none_none(self):
        cfg = ConfigStore.from_dict([])
        assert cfg.adjacent_urls("chapter_01/") == (None, None)


# ──────────────────────────────── eee_topbar style="index" ──

class TestEeeTopbarIndex:
    def test_style_index_with_back_url(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://example.com",
                            lang="en", titles="Index", style="index")
        assert isinstance(result, _StubHtmlMo.Html)
        assert "href" in result.s
        # no parent_titles given — falls back to titles, and always ◀ (not the self-badge icon)
        assert "◀ Index" in result.s

    def test_style_index_no_back_url(self):
        result = eee_topbar(_StubHtmlMo(), back_url="",
                            lang="en", titles="Index", style="index")
        assert isinstance(result, _StubHtmlMo.Html)
        assert "<span" in result.s
        assert "Index" in result.s

    def test_style_index_with_back_url_uses_parent_titles(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://example.com", lang="en",
                            titles="Zorba", parent_titles="B1", style="index")
        assert "◀ B1" in result.s
        assert "Zorba" not in result.s

    def test_style_index_with_back_url_parent_titles_dict_lang_lookup(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://example.com", lang="el",
                            titles="Zorba", parent_titles={"en": "B1", "el": "Β1"}, style="index")
        assert "◀ Β1" in result.s

    def test_style_index_with_back_url_ignores_custom_icon(self):
        result = eee_topbar(_StubHtmlMo(), back_url="https://example.com", lang="en",
                            titles="Index", icon="★", style="index")
        assert "★" not in result.s
        assert "◀" in result.s


# ──────────────────────────────── diacritics_text / _DiacriticsElement ──

from eee_project.notebook_utils import diacritics_text as _diacritics_text_fn, _DiacriticsElement


class TestDiacriticsText:
    def test_fallback_when_no_anywidget(self):
        import eee_project.notebook_utils as _nu
        orig = _nu._ANYWIDGET_OK
        try:
            _nu._ANYWIDGET_OK = False
            result = _diacritics_text_fn(_FormMo(), placeholder="test")
            assert hasattr(result, "value")
        finally:
            _nu._ANYWIDGET_OK = orig

    def test_anywidget_path_returns_element(self):
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        result = _diacritics_text_fn(_FormMo())
        assert isinstance(result, _DiacriticsElement)

    def test_value_preset_when_given(self):
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        result = _diacritics_text_fn(_FormMo(), value="hello")
        assert result._ui.value == "hello"

    def test_polytonic_defaults_true(self):
        # Matches this function's original Ancient-Greek-only behavior --
        # existing callers that don't pass polytonic= see no change.
        # _FormMo.ui.anywidget() is a no-op passthrough (unlike real marimo's
        # wrapping UIElement), so ._ui is the raw widget instance itself here.
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        result = _diacritics_text_fn(_FormMo())
        assert result._ui.polytonic is True

    def test_polytonic_false_settable(self):
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        result = _diacritics_text_fn(_FormMo(), polytonic=False)
        assert result._ui.polytonic is False

    def test_placeholder_and_label_are_synced_traits(self):
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        result = _diacritics_text_fn(_FormMo(), placeholder="γράψε", label="Απάντηση:")
        assert result._ui.placeholder == "γράψε"
        assert result._ui.label == "Απάντηση:"
        assert result._ui.trait_metadata("label", "sync") is True
        assert result._ui.trait_metadata("placeholder", "sync") is True

    def test_same_esm_for_any_label(self):
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        a = _diacritics_text_fn(_FormMo(), label="a", placeholder="x")
        b = _diacritics_text_fn(_FormMo(), label="b", placeholder="y")
        assert isinstance(a._ui, _nu._DiacriticsTextWidget)
        assert a._ui._esm == b._ui._esm == _DIA_ESM

    def test_esm_reads_label_and_placeholder_from_model(self):
        assert "EEE_" not in _DIA_ESM
        assert "model.on('change:label'" in _DIA_ESM
        assert "model.on('change:placeholder'" in _DIA_ESM


class TestDiacriticsElement:
    def _fake_ui(self, val="text", enter_pressed=0):
        class _W:
            value = val
        _W.enter_pressed = enter_pressed
        class _UI:
            widget = _W()
            def _mime_(self): return ("text/html", "<div/>")
        return _UI()

    def test_label_and_placeholder_setters_update_widget(self):
        ui = self._fake_ui()
        el = _DiacriticsElement(ui)
        el.label = "Νέο:"
        el.placeholder = "πληκτρολόγησε"
        assert (ui.widget.label, ui.widget.placeholder) == ("Νέο:", "πληκτρολόγησε")
        assert (el.label, el.placeholder) == ("Νέο:", "πληκτρολόγησε")

    def test_value_property(self):
        el = _DiacriticsElement(self._fake_ui("hello"))
        assert el.value == "hello"

    def test_enter_pressed_property(self):
        el = _DiacriticsElement(self._fake_ui(enter_pressed=3))
        assert el.enter_pressed == 3

    def test_mime_delegates(self):
        el = _DiacriticsElement(self._fake_ui())
        result = el._mime_()
        assert result[0] == "text/html"


# ──────────────────────────────── interactive_text (clickable poem words) ──

class TestInteractiveText:
    """interactive_text: clickable-word anywidget for the poem-text panel (section-02)."""

    def _mo(self):
        return _FormMo()

    def test_no_anywidget_raises(self):
        import eee_project.notebook_utils as _nu
        orig = _nu._ANYWIDGET_OK
        try:
            _nu._ANYWIDGET_OK = False
            with pytest.raises(ImportError, match="anywidget"):
                interactive_text(self._mo(), lines=["a"], clickable=set())
        finally:
            _nu._ANYWIDGET_OK = orig

    def test_returns_mo_ui_anywidget_result_not_bare_instance(self):
        # _FormMo.ui.anywidget is an identity passthrough (returns its arg
        # unchanged), so it can't tell "returned mo.ui.anywidget(w)" apart
        # from a regression to "returned w directly" -- exactly the mistake
        # that would silently break marimo reactivity (mo.ui.anywidget(inst)
        # IS the reactive UIElement; a bare widget instance is NOT). Use a
        # tagged wrapper instead so the two cases are distinguishable.
        calls = []

        class _TaggedMo:
            class ui:
                @staticmethod
                def anywidget(inst):
                    calls.append(inst)
                    return ("WRAPPED", inst)

        result = interactive_text(_TaggedMo(), lines=["a"], clickable=set())
        assert result == ("WRAPPED", calls[0])
        assert isinstance(calls[0], _InteractiveTextWidget)

    def test_trait_defaults_selected_word_and_click_seq(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable={"ανδρα"})
        assert w.selected_word == ""
        assert w.click_seq == 0

    def test_lines_stored(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα μοι"], clickable=set())
        assert w.lines == ["ἄνδρα μοι"]

    def test_clickable_stored_as_list_not_set(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable={"ανδρα", "μοι"})
        assert isinstance(w.clickable, list)
        assert set(w.clickable) == {"ανδρα", "μοι"}

    def test_word_classes_defaults_empty_dict(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set())
        assert w.word_classes == {}

    def test_homer_words_becomes_homer_word_class(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(), homer_words={"ανδρα", "μοι"})
        assert isinstance(w.word_classes["homer"], list)
        assert set(w.word_classes["homer"]) == {"ανδρα", "μοι"}

    def test_word_classes_stored_as_lists(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(),
                             word_classes={"lxx": {"ανδρα"}, "rare": ["μοι"]})
        assert w.word_classes == {"lxx": ["ανδρα"], "rare": ["μοι"]}

    def test_word_classes_merges_with_homer_words_and_overrides(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(),
                             homer_words={"a"}, word_classes={"lxx": {"b"}})
        assert w.word_classes == {"homer": ["a"], "lxx": ["b"]}
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(),
                             homer_words={"a"}, word_classes={"homer": {"c"}})
        assert w.word_classes == {"homer": ["c"]}

    def test_word_classes_rejects_bad_or_reserved_names(self):
        for bad in ("active", "gk-word", "a b", "1x", ""):
            with pytest.raises(ValueError):
                interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(), word_classes={bad: {"x"}})

    def test_word_classes_validates_names_even_when_the_set_is_empty(self):
        # the `X if SHOW.value else set()` toggle pattern must fail on the
        # first call, not only once the toggle is switched on
        for bad in ("active", "gk-word", "a b", "1x", ""):
            with pytest.raises(ValueError):
                interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(), word_classes={bad: set()})

    def test_css_defaults_to_the_widget_stylesheet(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set())
        assert w._css == _ITEXT_CSS

    def test_default_stylesheet_ends_with_the_selected_word_rule(self):
        assert _ITEXT_CSS.rstrip().splitlines()[-1].startswith(".eee-itext .gk-word.active")

    def test_css_is_inserted_before_the_selected_word_rule(self):
        # equal specificity, so source order decides: the caller's rule must
        # follow `.homer` (it may override it) yet precede `.active`, or a
        # clicked word in a custom set would lose its selection highlight
        rule = ".eee-itext .gk-word.lxx{background:#e3f0e3}"
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(), css=rule)
        assert w._css.count(rule) == 1
        assert w._css.index(".gk-word.homer") < w._css.index(rule) < w._css.index(".gk-word.active")
        assert w._css.replace(rule + "\n", "") == _ITEXT_CSS

    def test_css_does_not_leak_into_other_widgets(self):
        interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(), css=".x{color:red}")
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set())
        assert w._css == _ITEXT_CSS
        assert _InteractiveTextWidget._css == _ITEXT_CSS

    def test_show_ictus_defaults_true(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set())
        assert w.show_ictus is True

    def test_show_ictus_explicit_false(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(), show_ictus=False)
        assert w.show_ictus is False

    def test_ictus_html_defaults_empty_dict_when_none(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(), ictus_html=None)
        assert w.ictus_html == {}

    def test_ictus_html_stored_when_given(self):
        rhythm = {"ἄνδρα": "<b>ἄ</b>νδρα"}
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(), ictus_html=rhythm)
        assert w.ictus_html == rhythm

    def test_lines_are_independent_copies(self):
        lines = ["ἄνδρα", "μοι"]
        w = interactive_text(self._mo(), lines=lines, clickable=set())
        lines.append("ἔννεπε")
        assert len(w.lines) == 2


class TestInteractiveTextEsm:
    """Static _ITEXT_ESM guards — the click/keydown JS can't run headlessly
    (see [[feedback_marimo_reactivity_testing]]); marimo-pair + a human browser
    verifies actual click/keyboard behaviour (section-08)."""

    def test_delegates_single_click_listener(self):
        assert _ITEXT_ESM.count("addEventListener('click'") == 1
        assert "closest('.gk-word')" in _ITEXT_ESM

    def test_keydown_handles_enter_and_space(self):
        assert "addEventListener('keydown'" in _ITEXT_ESM
        assert "'Enter'" in _ITEXT_ESM
        assert "' '" in _ITEXT_ESM

    def test_clickable_spans_have_role_and_tabindex(self):
        assert 'role="button"' in _ITEXT_ESM
        assert 'tabindex="0"' in _ITEXT_ESM

    def test_activation_sets_traits_and_saves(self):
        assert "model.set('selected_word'" in _ITEXT_ESM
        assert "model.set('click_seq'" in _ITEXT_ESM
        assert "model.save_changes()" in _ITEXT_ESM

    def test_escapes_html_text(self):
        assert "function escapeHtml" in _ITEXT_ESM
        _after_def = _ITEXT_ESM.split("function escapeHtml", 1)[1]
        assert "escapeHtml(bare)" in _after_def  # data-w attribute
        assert "escapeHtml(tok)" in _after_def   # plain-line display text

    def test_active_class_from_selected_word(self):
        assert "gk-word" in _ITEXT_ESM and "active" in _ITEXT_ESM
        assert "selected_word" in _ITEXT_ESM

    def test_defensive_empty_fallbacks(self):
        assert "model.get('lines') || []" in _ITEXT_ESM
        assert "model.get('clickable') || []" in _ITEXT_ESM
        assert "model.get('ictus_html') || {}" in _ITEXT_ESM

    def test_word_classes_read_with_fallback_and_redraw_listener(self):
        assert "model.get('word_classes') || {}" in _ITEXT_ESM
        assert "model.on('change:word_classes', draw)" in _ITEXT_ESM
        assert "homer_words" not in _ITEXT_ESM

    def test_normalizes_like_norm_grc_surface(self):
        # Mirrors eee_project.notebook_utils.norm_grc_surface's algorithm so a
        # rendered token's key matches a `clickable` set built by that function
        # (e.g. via the public grc_coverage_words(..., mode="none", ...)). Checks
        # the exact contiguous character class (not individual chars like "," or
        # "." — those would trivially match anywhere in a 90-line JS file).
        assert r"̀-ͯ" in _ITEXT_ESM  # strip_diacritics equivalent
        assert "[',.··᾽᾿ʼ]" in _ITEXT_ESM  # norm_grc_surface's exact edge-punct set

    def test_redraws_on_python_trait_changes(self):
        for trait in ("lines", "clickable", "show_ictus", "ictus_html"):
            assert f"change:{trait}" in _ITEXT_ESM


# ──────────────────────────────── GreekUtils internals ──

class TestGreekUtilsInternals:
    def test_paradigm_exception_returns_empty(self):
        class _BadBackend:
            def paradigm(self, w, p): raise ValueError("backend error")
        gu = GreekUtils(_BadBackend(), _StubMo(), config=ANCIENT_GREEK)
        assert gu._paradigm("θεός", "noun") == {}

    def test_eee_forms_none_when_no_eee(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)
        assert gu._eee_forms("λύω", "verb", {"Tense": "Pres"}) is None

    def test_eee_forms_returns_forms(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "inflect_slot", return_value={"λύω"}):
            result = gu._eee_forms("λύω", "verb", {"Tense": "Pres"})
        assert result == {"λύω"}

    def test_eee_forms_exception_returns_empty_set(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "inflect_slot", side_effect=Exception("err")):
            result = gu._eee_forms("λύω", "verb", {"Tense": "Pres"})
        assert result == set()

    def test_noun_forms_uses_eee(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "inflect_slot", return_value={"θεόν"}):
            result = gu._noun_forms("θεός", "sg", "acc")
        assert result == {"θεόν"}

    def test_noun_forms_gender_uses_eee(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "inflect_slot", return_value={"θεοῦ"}):
            result = gu._noun_forms_gender("θεός", "sg", "gen", "masc")
        assert result == {"θεοῦ"}

    def test_verb_forms_unknown_tense_returns_empty(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)
        assert gu._verb_forms("λύω", "nonexistent_tense", "1", "sg") == set()

    def test_verb_forms_uses_eee(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "inflect_slot", return_value={"λύω"}):
            result = gu._verb_forms("λύω", "present", "pri", "sg")
        assert result == {"λύω"}

    def test_adj_forms_uses_eee(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "inflect_slot", return_value={"καλόν"}):
            result = gu._adj_forms("καλός", "sg", "neut", "nom")
        assert result == {"καλόν"}

    def test_adv_forms_no_eee_returns_empty(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)
        assert gu._adv_forms("καλός") == set()

    def test_adv_forms_no_ag_paradigm_slot_returns_empty(self):
        import types
        other_slot = types.SimpleNamespace(tag=".NSM", tag_type="ud", features={"Case": "Nom"})
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "get_slot_templates", return_value=[other_slot]):
            assert gu._adv_forms("καλός") == set()

    def test_adv_forms_finds_ag_paradigm_slot(self):
        import types
        adv_slot = types.SimpleNamespace(tag="ADV", tag_type="ag-paradigm", features=None)
        other_slot = types.SimpleNamespace(tag=".NSM", tag_type="ud", features={"Case": "Nom"})
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "get_slot_templates", return_value=[other_slot, adv_slot]), \
             patch.object(_eee, "inflect_slot", return_value={"καλῶς"}) as mock_inflect:
            result = gu._adv_forms("καλός")
        assert result == {"καλῶς"}
        mock_inflect.assert_called_once_with("καλός", adv_slot, "adjective", language="grc")

    def test_adv_forms_exception_returns_empty(self):
        import types
        adv_slot = types.SimpleNamespace(tag="ADV", tag_type="ag-paradigm", features=None)
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "get_slot_templates", return_value=[adv_slot]), \
             patch.object(_eee, "inflect_slot", side_effect=Exception("err")):
            result = gu._adv_forms("καλός")
        assert result == set()

    def test_clean_word_row_empty_returns_none(self):
        assert GreekUtils._clean_word_row({"Word": "", "Translation": "t"}) is None
        assert GreekUtils._clean_word_row({"Word": "  ", "Translation": "t"}) is None
        assert GreekUtils._clean_word_row({"Translation": "t"}) is None

    def test_clean_word_row_strips_whitespace(self):
        r = GreekUtils._clean_word_row({"Word": "  λύω  ", "Translation": " loosen "})
        assert r == {"Word": "λύω", "Translation": "loosen"}


# ──────────────────────────────── adverb_vocab ──

class TestAdverbVocab:
    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK, eee_module=_eee)

    def test_skips_adjectives_with_no_adverb(self, gu):
        with patch.object(gu, "_adv_forms", return_value=set()):
            result = gu.adverb_vocab([{"form": "μέγας", "meaning": "big"}])
        assert result == []

    def test_builds_entry_from_single_form(self, gu):
        with patch.object(gu, "_adv_forms", return_value={"καλῶς"}):
            result = gu.adverb_vocab([{"form": "καλός", "meaning": "beautiful"}])
        assert result == [{"form": "καλῶς", "meaning": "beautiful"}]

    def test_picks_first_in_sorted_order_of_multiple_forms(self, gu):
        with patch.object(gu, "_adv_forms", return_value={"ζωρῶς", "βωρῶς"}):
            result = gu.adverb_vocab([{"form": "x", "meaning": "y"}])
        assert result == [{"form": "βωρῶς", "meaning": "y"}]

    def test_custom_word_and_meaning_keys(self, gu):
        with patch.object(gu, "_adv_forms", return_value={"καλῶς"}):
            result = gu.adverb_vocab(
                [{"Word": "καλός", "Translation": "beautiful"}],
                word_key="Word", meaning_key="Translation",
            )
        assert result == [{"Word": "καλῶς", "Translation": "beautiful"}]

    def test_missing_meaning_defaults_to_empty_string(self, gu):
        with patch.object(gu, "_adv_forms", return_value={"καλῶς"}):
            result = gu.adverb_vocab([{"form": "καλός"}])
        assert result == [{"form": "καλῶς", "meaning": ""}]

    def test_multiple_adjectives_mixed_coverage(self, gu):
        def _fake_adv(word):
            return {"καλῶς"} if word == "καλός" else set()
        with patch.object(gu, "_adv_forms", side_effect=_fake_adv):
            result = gu.adverb_vocab([
                {"form": "καλός", "meaning": "beautiful"},
                {"form": "μέγας", "meaning": "big"},
            ])
        assert result == [{"form": "καλῶς", "meaning": "beautiful"}]


# ──────────────────────────────── GreekUtils data I/O ──

class TestGreekUtilsDataIO:
    def test_load_slot_drill_basic(self, tmp_path):
        tsv = tmp_path / "verbs.tsv"
        tsv.write_text("Word\tTranslation\nλύω\tloosen\n", encoding="utf-8")
        gu = GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "inflect", return_value={"λύε"}):
            rows = gu.load_slot_drill(tsv, {"verb": None, "sg": {"Person": "2", "Number": "Sing"}}, "verb")
        assert len(rows) == 1
        assert rows[0]["verb"] == "λύω"
        assert rows[0]["sg"] == "λύε"
        assert rows[0]["meaning"] == "loosen"

    def test_load_slot_drill_skips_empty_words(self, tmp_path):
        tsv = tmp_path / "verbs.tsv"
        tsv.write_text("Word\tTranslation\nλύω\tloosen\n\t\n", encoding="utf-8")
        gu = GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK, eee_module=_eee)
        with patch.object(_eee, "inflect", return_value=set()):
            rows = gu.load_slot_drill(tsv, {"verb": None}, "verb")
        assert len(rows) == 1

    def test_load_data_with_upload(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK)
        tsv_bytes = "Word\tTranslation\nλύω\tloosen\n".encode("utf-8")
        contents = type("_C", (), {"contents": tsv_bytes})()
        upload = type("_U", (), {"value": [contents]})()
        df = gu.load_data(upload)
        assert df is not None
        assert "Word" in df.columns

    def test_load_data_no_upload_returns_none(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK)
        upload = type("_U", (), {"value": []})()
        assert gu.load_data(upload) is None

    def test_get_words_none_returns_empty(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK)
        assert gu.get_words(None) == []

    def test_get_words_value_none_returns_empty(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK)
        assert gu.get_words(type("_T", (), {"value": None})()) == []

    def test_get_words_from_dataframe(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK)
        df = _pd.DataFrame([{"Word": "λύω", "Translation": "loosen"}, {"Word": "", "Translation": "x"}])
        result = gu.get_words(type("_T", (), {"value": df})())
        assert len(result) == 1
        assert result[0]["Word"] == "λύω"

    def test_get_words_empty_dataframe(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK)
        assert gu.get_words(type("_T", (), {"value": _pd.DataFrame()})()) == []

    def test_get_words_from_list(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK)
        rows = [{"Word": "λύω", "Translation": "loosen"}, {"Word": "", "Translation": "x"}]
        result = gu.get_words(type("_T", (), {"value": rows})())
        assert len(result) == 1

    def test_get_words_empty_list(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), _pd, config=ANCIENT_GREEK)
        assert gu.get_words(type("_T", (), {"value": []})()) == []

    def test_make_snapshot_copies_attrs(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)
        form = type("_F", (), {"value": ["a", "b"], "test_word": "θεός", "is_pluralia_tantum": False})()
        snap = gu.make_snapshot(form)
        assert snap.value == ["a", "b"]
        assert snap.test_word == "θεός"

    def test_make_snapshot_none_form(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)
        snap = gu.make_snapshot(None, extra="val")
        assert snap.value == []
        assert snap.extra == "val"

    def test_make_snapshot_skips_missing_attrs(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)
        form = type("_F", (), {"value": ["x"]})()
        snap = gu.make_snapshot(form)
        assert snap.value == ["x"]
        assert not hasattr(snap, "test_word")

    def test_make_snapshot_copies_active_slots(self):
        # Regression: create_verb_test_ui sets form.active_slots (the verb
        # sibling of the noun form's active_cases, already covered above) --
        # without copying it, check_verb_test falls back to the full,
        # unfiltered slot list against a snapshot.value shorter than that,
        # raising IndexError for any verb with an actually-excluded slot.
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)
        slots = [("sg", "pri"), ("sg", "sec")]
        form = type("_F", (), {"value": ["a", "b"], "verb_word": "λύω", "active_slots": slots})()
        snap = gu.make_snapshot(form)
        assert snap.active_slots == slots


# ──────────────────────────────── resolve_word_grammar exception ──

class TestResolveWordGrammarException:
    def test_exception_gives_empty_label(self):
        class _BrokenBackend:
            def paradigm(self, lemma, pos): raise RuntimeError("db error")
            def get_slot_templates(self, lang, pos, terms_lang="en"): return []
        gu = GreekUtils(mo_module=_StubMo())
        words = [{"form": "θεός", "lemma": "θεός", "pos": "noun"}]
        result = gu.resolve_word_grammar(words, _BrokenBackend(), "en")
        assert result[0]["grammar_label"] == ""


# ──────────────────────────────── adjective_drill_meta / pronoun_drill_meta ──

class TestAdjectiveDrillMeta:
    def test_defective_word_excludes_empty_slots(self):
        # A word with only 3 (of 6) real forms -- mirrors κανένας's real
        # shape when mistakenly routed through the adjective path (it isn't,
        # after the modern-greek-inflexion-eee guard, but the mechanism
        # must hold for any genuinely defective adjective too).
        def _paradigm_fn(word, pos):
            if pos != "adjective":
                return {}
            return {"adj": {"sg": {"masc": {"nom": {"x"}}, "fem": {"nom": {"y"}}, "neut": {"nom": {"z"}}}}}
        gu = GreekUtils(_StubBackend(_paradigm_fn), _StubMo(), config=ANCIENT_GREEK)
        meta = gu.adjective_drill_meta("test", "simple")
        assert len(meta.active_slots) == 3
        assert all(n == "sg" for _, n, _ in meta.active_slots)

    def test_fully_regular_word_keeps_all_slots(self):
        def _paradigm_fn(word, pos):
            if pos != "adjective":
                return {}
            full = {"nom": {"x"}}
            return {"adj": {n: {g: full for g in ("masc", "fem", "neut")} for n in ("sg", "pl")}}
        gu = GreekUtils(_StubBackend(_paradigm_fn), _StubMo(), config=ANCIENT_GREEK)
        meta = gu.adjective_drill_meta("test", "simple")
        assert len(meta.active_slots) == 6

    def test_totally_unknown_word_falls_back_to_full_list(self):
        # StubBackend's default paradigm_fn returns {} for everything --
        # every slot is empty, so active_slots must fall back to the full
        # static list rather than leaving the form with zero fields.
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)
        meta = gu.adjective_drill_meta("test", "simple")
        assert len(meta.active_slots) == 6


class TestPronounDrillMeta:
    def test_singular_only_word_excludes_plural_slots(self):
        # κανένας's real shape: Pronoun.all() has no "pl" key at all.
        def _paradigm_fn(word, pos):
            if pos != "pronoun":
                return {}
            return {"sg": {"masc": {"nom": {"κανένας"}}, "fem": {"nom": {"καμία"}}, "neut": {"nom": {"κανένα"}}}}
        gu = GreekUtils(_StubBackend(_paradigm_fn), _StubMo(), config=ANCIENT_GREEK)
        meta = gu.pronoun_drill_meta("κανένας", "simple")
        assert len(meta.active_slots) == 3
        assert all(n == "sg" for _, n, _ in meta.active_slots)

    def test_fully_regular_pronoun_keeps_all_slots(self):
        def _paradigm_fn(word, pos):
            if pos != "pronoun":
                return {}
            full = {"nom": {"x"}}
            return {n: {g: full for g in ("masc", "fem", "neut")} for n in ("sg", "pl")}
        gu = GreekUtils(_StubBackend(_paradigm_fn), _StubMo(), config=ANCIENT_GREEK)
        meta = gu.pronoun_drill_meta("ίδιος", "simple")
        assert len(meta.active_slots) == 6

    def test_totally_unknown_word_falls_back_to_full_list(self):
        gu = GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)
        meta = gu.pronoun_drill_meta("test", "simple")
        assert len(meta.active_slots) == 6

    def test_check_pronoun_test_passes_when_only_active_slots_filled(self):
        # The whole point of the fix: a singular-only word's full-form check
        # must be achievable (ok=True) when the 3 real slots are correct --
        # not permanently stuck at ok=False because 3 nonexistent plural
        # slots are still part of the static list. Mirrors the live check
        # already confirmed against the real Modern Greek backend.
        def _paradigm_fn(word, pos):
            if pos != "pronoun":
                return {}
            return {"sg": {"masc": {"nom": {"κανένας"}}, "fem": {"nom": {"καμία"}}, "neut": {"nom": {"κανένα"}}}}
        gu = GreekUtils(_StubBackend(_paradigm_fn), _RichMo(), config=ANCIENT_GREEK)
        active_slots = gu.pronoun_drill_meta("κανένας", "simple").active_slots
        form = type("_F", (), {
            "value": ["κανένας", "καμία", "κανένα"],
            "pron_word": "κανένας", "pron_mode": "simple", "active_slots": active_slots,
        })()
        ok, fb = gu.check_pronoun_test("κανένας", form)
        assert ok is True
        assert fb == ""


# ──────────────────────────────── create_adjective_test_ui / check_adjective_test ──

class TestCreateAdjectiveTestUi:
    _WORD = {"Word": "καλός", "Translation": "beautiful"}

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _RichMo(), config=ANCIENT_GREEK)

    def test_no_current_adj_returns_none_form(self, gu):
        form, md = gu.create_adjective_test_ui([], [], None)
        assert form is None

    def test_basic_form_created(self, gu):
        form, md = gu.create_adjective_test_ui([self._WORD], [self._WORD], self._WORD)
        assert form is not None
        assert form.adj_word == "καλός"
        assert form.adj_mode == "simple"

    def test_full_mode_more_inputs(self, gu):
        form_s, _ = gu.create_adjective_test_ui([self._WORD], [self._WORD], self._WORD, mode="simple")
        form_f, _ = gu.create_adjective_test_ui([self._WORD], [self._WORD], self._WORD, mode="full")
        assert len(form_f.value) > len(form_s.value)

    def test_empty_words4test_shows_empty_message(self, gu):
        form, md = gu.create_adjective_test_ui([self._WORD], [], self._WORD, lang="en")
        assert form is not None
        assert "empty" in md.lower()

    def test_words4test_md_contains_translation(self, gu):
        _, md = gu.create_adjective_test_ui([self._WORD], [self._WORD], self._WORD)
        assert "beautiful" in md


class TestCheckAdjectiveTest:
    _WORD = "καλός"

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _RichMo(), config=ANCIENT_GREEK)

    def test_none_form_returns_false(self, gu):
        ok, fb = gu.check_adjective_test(self._WORD, None)
        assert ok is False and fb == ""

    def test_empty_value_returns_false(self, gu):
        form = type("_F", (), {"value": []})()
        ok, fb = gu.check_adjective_test(self._WORD, form)
        assert ok is False and fb == ""

    def test_adj_word_mismatch_returns_false(self, gu):
        form = type("_F", (), {"value": ["x", "y"], "adj_word": "ἄλλος"})()
        ok, fb = gu.check_adjective_test(self._WORD, form)
        assert ok is False and fb == ""

    def test_all_empty_returns_please_fill(self, gu):
        form = type("_F", (), {"value": ["", "", "", "", "", ""]})()
        ok, fb = gu.check_adjective_test(self._WORD, form, lang="en")
        assert ok is False
        assert "fill" in fb.lower()


# ──────────────────────────────── check_adjective_slot / adjective_slot_labels ──

class TestCheckAdjectiveSlot:
    _WORD = "καλός"

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    def test_simple_mode_has_six_slots(self, gu):
        # slot 6 is out of range for 'simple' (0-5) -> False, not an exception
        assert gu.check_adjective_slot(self._WORD, "simple", 6, "x") is False

    def test_negative_index_returns_false(self, gu):
        assert gu.check_adjective_slot(self._WORD, "simple", -1, "x") is False

    def test_no_backend_data_never_passes_even_for_the_base_word_itself(self, gu):
        # _StubBackend returns {} -> _adj_forms empty -> no correct answer
        # exists, so nothing passes -- not even the base word typed back
        # verbatim (the old fallback silently accepted exactly that, which
        # turns "we have no data" into "anything is right" for every slot
        # of a mis-tested word; see the real κανένας incident this guards
        # against: an irregular pronoun wrongly listed as an adjective
        # would have "passed" for its actual base form on every field).
        assert gu.check_adjective_slot(self._WORD, "simple", 0, "καλός") is False
        assert gu.check_adjective_slot(self._WORD, "simple", 0, "wrong") is False

    def test_blank_backend_form_sentinel_never_passes(self):
        # A backend can return {''} for a slot it has no data for (a real,
        # deliberate sentinel, not just an empty set) -- any(correct) is
        # False for {''} same as for set(), so this must not pass either.
        def _paradigm_fn(word, pos):
            if pos != "adjective":
                return {}
            return {"adj": {"sg": {"masc": {"nom": {''}}}}}
        gu = GreekUtils(_StubBackend(_paradigm_fn), _StubMo(), config=ANCIENT_GREEK)
        assert gu.check_adjective_slot(self._WORD, "simple", 0, "καλός") is False
        assert gu.check_adjective_slot(self._WORD, "simple", 0, "wrong") is False

    def test_full_mode_has_more_slots_than_simple(self, gu):
        # full mode covers every case in config.adj_cases x 3 genders x 2 numbers;
        # simple mode only has 6 (nominative). A slot index valid in 'full' but
        # out of range in 'simple' proves the two modes use different slot counts.
        simple_slots = gu._adj_slot_list("simple")
        full_slots = gu._adj_slot_list("full")
        assert len(full_slots) > len(simple_slots)


class TestAdjectiveSlotLabels:
    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    def test_simple_mode_has_six_labels(self, gu):
        labels = gu.adjective_slot_labels("simple")
        assert len(labels) == 6

    def test_full_mode_has_more_labels(self, gu):
        assert len(gu.adjective_slot_labels("full")) > len(gu.adjective_slot_labels("simple"))

    def test_labels_match_slot_list_order(self, gu):
        labels = gu.adjective_slot_labels("simple")
        slots = gu._adj_slot_list("simple")
        assert len(labels) == len(slots)


class TestCheckPronounTest:
    _WORD = "κανένας"

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _RichMo(), config=ANCIENT_GREEK)

    def test_none_form_returns_false(self, gu):
        ok, fb = gu.check_pronoun_test(self._WORD, None)
        assert ok is False and fb == ""

    def test_empty_value_returns_false(self, gu):
        form = type("_F", (), {"value": []})()
        ok, fb = gu.check_pronoun_test(self._WORD, form)
        assert ok is False and fb == ""

    def test_pron_word_mismatch_returns_false(self, gu):
        form = type("_F", (), {"value": ["x", "y"], "pron_word": "ίδιος"})()
        ok, fb = gu.check_pronoun_test(self._WORD, form)
        assert ok is False and fb == ""

    def test_all_empty_returns_please_fill(self, gu):
        form = type("_F", (), {"value": ["", "", "", "", "", ""]})()
        ok, fb = gu.check_pronoun_test(self._WORD, form, lang="en")
        assert ok is False
        assert "fill" in fb.lower()

    def test_correct_singular_forms_pass_via_paradigm_fallback(self):
        # κανένας's real (singular-only) paradigm shape: {num: {gender: {case: forms}}}.
        # check_pronoun_test (mirroring check_adjective_test) requires every
        # slot non-blank to report ok=True for the WHOLE form -- a genuinely
        # singular-only word can never satisfy that through this 6-slot
        # widget (the 3 plural slots have no correct answer at all), so this
        # checks the 3 real (singular) slots individually via
        # check_pronoun_slot instead -- that's where "does a correct answer
        # actually pass" is meaningfully testable for this word shape.
        def _paradigm_fn(word, pos):
            if pos != "pronoun":
                return {}
            return {"sg": {
                "masc": {"nom": {"κανένας"}}, "fem": {"nom": {"καμία", "καμιά"}},
                "neut": {"nom": {"κανένα"}},
            }}
        gu = GreekUtils(_StubBackend(_paradigm_fn), _RichMo(), config=ANCIENT_GREEK)
        assert gu.check_pronoun_slot(self._WORD, "simple", 0, "κανένας") is True   # masc sg nom
        assert gu.check_pronoun_slot(self._WORD, "simple", 1, "καμία") is True     # fem sg nom
        assert gu.check_pronoun_slot(self._WORD, "simple", 2, "κανένα") is True    # neut sg nom
        assert gu.check_pronoun_slot(self._WORD, "simple", 3, "anything") is False  # masc pl nom -- no data

    def test_no_backend_data_never_passes_even_for_the_base_word_itself(self, gu):
        # Same "no fallback to input-as-correct" contract as
        # test_no_backend_data_never_passes_even_for_the_base_word_itself
        # in TestCheckAdjectiveSlot -- StubBackend returns {} -> _pronoun_forms
        # empty -> nothing passes, not even the base word typed back verbatim.
        form = type("_F", (), {"value": ["κανένας", "", "", "", "", ""]})()
        ok, fb = gu.check_pronoun_test(self._WORD, form)
        assert ok is False
        assert "?" in fb


# ──────────────────────────────── check_pronoun_slot / pronoun_slot_labels ──

class TestCheckPronounSlot:
    _WORD = "κανένας"

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    def test_simple_mode_has_six_slots(self, gu):
        assert gu.check_pronoun_slot(self._WORD, "simple", 6, "x") is False

    def test_negative_index_returns_false(self, gu):
        assert gu.check_pronoun_slot(self._WORD, "simple", -1, "x") is False

    def test_no_backend_data_never_passes_even_for_the_base_word_itself(self, gu):
        # Mirrors TestCheckAdjectiveSlot's identically-named test -- the same
        # "show real forms or nothing, never a free pass" contract this
        # whole pronoun feature exists to uphold (see check_adjective_slot's
        # own docstring / the real κανένας incident it guards against).
        assert gu.check_pronoun_slot(self._WORD, "simple", 0, "κανένας") is False
        assert gu.check_pronoun_slot(self._WORD, "simple", 0, "wrong") is False

    def test_blank_backend_form_sentinel_never_passes(self):
        def _paradigm_fn(word, pos):
            if pos != "pronoun":
                return {}
            return {"sg": {"masc": {"nom": {''}}}}
        gu = GreekUtils(_StubBackend(_paradigm_fn), _StubMo(), config=ANCIENT_GREEK)
        assert gu.check_pronoun_slot(self._WORD, "simple", 0, "κανένας") is False
        assert gu.check_pronoun_slot(self._WORD, "simple", 0, "wrong") is False

    def test_no_vocative_in_full_mode(self, gu):
        # No pronoun has a vocative form (verified against every entry in
        # modern_greek_inflexion_eee/resources/pronouns.py) -- 'full' mode's
        # case list must be nom/gen/acc only, unlike adjective's 4 cases.
        full_slots = gu._pronoun_slot_list("full")
        cases = {c for _, _, c in full_slots}
        assert cases == {"nom", "gen", "acc"}

    def test_full_mode_has_more_slots_than_simple(self, gu):
        simple_slots = gu._pronoun_slot_list("simple")
        full_slots = gu._pronoun_slot_list("full")
        assert len(full_slots) > len(simple_slots)


class TestPronounSlotLabels:
    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _StubMo(), config=ANCIENT_GREEK)

    def test_simple_mode_has_six_labels(self, gu):
        labels = gu.pronoun_slot_labels("simple")
        assert len(labels) == 6

    def test_full_mode_has_more_labels(self, gu):
        assert len(gu.pronoun_slot_labels("full")) > len(gu.pronoun_slot_labels("simple"))

    def test_labels_match_slot_list_order(self, gu):
        labels = gu.pronoun_slot_labels("simple")
        slots = gu._pronoun_slot_list("simple")
        assert len(labels) == len(slots)


class TestPronounSlotLabelsLang:
    """lang= localization specifically -- see TestAdjectiveSlotLabelsLang
    above for the identical adjective-side pattern this mirrors.

    REGRESSION: pronoun-{en,ru,el}.tsv did not exist at all until this
    class was added -- adj-*.tsv/noun-*.tsv/verb-*.tsv/tense-*.tsv/ui-*.tsv
    were all present, but pronoun's own label file was simply never
    created, so every _slot_label_index("pronoun", lang) lookup missed
    for every language (including "en") and silently fell through to
    eee-project's own English-only _QUIZ_ADJ_GENDER/_QUIZ_ADJ_NUM dict --
    identical labels in all three languages, caught live in the
    ellinika_b/chapter_03 pronoun drill.
    """

    def _gu(self):
        from modern_greek_backend_eee import ModernGreekBackend
        be = ModernGreekBackend()
        # eee_module=_eee (the eee_project module), not eee_module=be (the
        # raw backend): get_slot_templates() -- all this class needed until
        # the two active-slots tests below -- resolves on either, but
        # _eee_forms()'s self._eee.inflect_slot(...) call only exists on
        # the module. With eee_module=be that call raised AttributeError on
        # every slot (caught, cached as an empty set), which pronoun_drill_
        # meta's "no data at all" fallback then silently read as "every
        # slot is real" -- always the full 6-slot static list regardless of
        # word, masking the very narrowing test_single_active_slot_
        # collapses_to_all_forms_label / test_multiple_active_slots_
        # unaffected exist to check.
        return GreekUtils(be, mo_module=_StubMo(), eee_module=_eee, config=MODERN_GREEK)

    def test_simple_mode_lang_en(self):
        gu = self._gu()
        labels = gu.pronoun_slot_labels("simple")
        assert labels[0] == "Nom. Sg. m.:"
        assert labels[3] == "Nom. Pl. m.:"

    def test_simple_mode_lang_ru(self):
        gu = self._gu()
        labels = gu.pronoun_slot_labels("simple", lang="ru")
        assert labels[0] == "Именит. ед. м.:"

    def test_simple_mode_lang_el(self):
        gu = self._gu()
        labels = gu.pronoun_slot_labels("simple", lang="el")
        assert labels[0] == "Ονομ. εν. αρ.:"

    def test_no_eee_module_falls_back_unchanged(self):
        gu = GreekUtils(mo_module=_StubMo())
        assert gu.pronoun_slot_labels("simple")[0] == "m. Sg:"

    def test_backend_without_real_labels_falls_back_not_raw_tag(self):
        from ancient_greek_backend_eee import AncientGreekBackend
        be = AncientGreekBackend()
        gu = GreekUtils(be, mo_module=_StubMo(), eee_module=be, config=ANCIENT_GREEK)
        labels = gu.pronoun_slot_labels("simple")
        assert labels[0] == "m. Sg:"
        assert not any(lbl.startswith(".") for lbl in labels)

    def test_single_active_slot_collapses_to_all_forms_label(self):
        # κάτι/τίποτα-shaped indeclinables reduce to exactly one active
        # slot (neut/sg/nom) -- labeling that one field with its specific
        # case/gender implies a fuller paradigm exists just off-screen,
        # which isn't true for a word with only ever one form. All three
        # languages should show the generic all_forms_label instead.
        gu = self._gu()
        meta = gu.pronoun_drill_meta("κάτι", "simple")
        assert meta.active_slots == [("neut", "sg", "nom")]
        assert gu.pronoun_slot_labels("simple", lang="en", active_slots=meta.active_slots) == ["All forms:"]
        assert gu.pronoun_slot_labels("simple", lang="ru", active_slots=meta.active_slots) == ["Все формы:"]
        assert gu.pronoun_slot_labels("simple", lang="el", active_slots=meta.active_slots) == ["Όλοι οι τύποι:"]

    def test_multiple_active_slots_unaffected(self):
        # κανένας has 3 genuinely distinct forms (masc/fem/neut) -- must
        # keep showing per-slot labels, not collapse.
        gu = self._gu()
        meta = gu.pronoun_drill_meta("κανένας", "simple")
        labels = gu.pronoun_slot_labels("simple", lang="en", active_slots=meta.active_slots)
        assert labels == ["Nom. Sg. m.:", "Nom. Sg. f.:", "Nom. Sg. n.:"]


# ──────────────────────────────── adjective_paradigm_drill_form ──

class TestAdjectiveParadigmDrillForm(_ParadigmDrillFormBase):
    _VOCAB = [{"form": "καλός", "meaning": "beautiful"}, {"form": "ἀγαθός", "meaning": "good"}]

    def _meta(self, active_slots=None):
        import types
        return types.SimpleNamespace(
            active_slots=active_slots or [(g, 'sg', 'nom') for g in ('masc', 'fem', 'neut')] +
                                          [(g, 'pl', 'nom') for g in ('masc', 'fem', 'neut')],
        )

    def _call(self, gu, state, cv, form, adj_meta=None, **kwargs):
        return self._call_form(gu.adjective_paradigm_drill_form, state, cv, form,
                               adj_meta=adj_meta or self._meta(), **kwargs)

    def test_done_shows_callout_and_restart(self, gu):
        state = self._state(words=[])
        result = self._call(gu, state, None, _pdform([]))
        assert "callout" in str(result)

    def test_restart_click_resets_state(self, gu):
        state = self._state(
            words=[self._VOCAB[0]], hist=[self._VOCAB[1]], entered={"καλός": ["x"]},
        )
        result = self._call(gu, state, self._VOCAB[0], _pdform([""]), restart_v=1)
        assert result == "*...*"
        self._assert_same_words(state["words"][2][0], self._VOCAB)
        assert state["hist"][2][0] == []
        assert state["entered"][2][0] == {}

    def test_correct_full_check_advances_and_saves(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_adjective_test", return_value=(True, "")):
            result = self._call(gu, state, cv, _pdform(["καλός"] * 6), check_v=1)
        assert result == "*...*"
        assert cv not in state["words"][2][0]
        assert cv in state["hist"][2][0]
        assert state["entered"][2][0].get("καλός") == ["καλός"] * 6

    def test_wrong_full_check_shows_feedback_no_advance(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_adjective_test", return_value=(False, "❌ wrong")):
            result = self._call(gu, state, cv, _pdform(["asd"] * 6), check_v=1)
        assert "❌ wrong" in str(result)
        assert cv in state["words"][2][0]

    def test_lang_reaches_check_adjective_test(self, gu):
        # Same regression as verb_paradigm_drill_form -- adjective_paradigm_drill_form
        # had no lang param at all before.
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_adjective_test", return_value=(False, "")) as m:
            self._call(gu, state, cv, _pdform(["asd"] * 6), check_v=1, lang="el")
        assert m.call_args.kwargs.get("lang") == "el"

    def test_nav_icons_hides_prev_with_no_history(self, gu):
        # nav_icons threads through to _paradigm_drill_form the same way as
        # verb -- see TestVerbParadigmDrillForm for the full row/hide battery.
        cv = self._VOCAB[0]
        state = self._state()
        result = self._call(gu, state, cv, _pdform(["", "", "", "", "", ""]), nav_icons=True)
        assert len(result[-2]) == 2

    def test_config_nav_icons_true_used_with_no_explicit_kwarg(self):
        gu = GreekUtils(_StubBackend(), _FormMo(), config=_NAV_ICONS_CONFIG)
        cv = self._VOCAB[0]
        state = self._state()
        result = self._call(gu, state, cv, _pdform(["", "", "", "", "", ""]))
        assert len(result[-2]) == 2

    def test_show_prev_when_done_reaches_paradigm_drill_form(self, gu):
        # show_prev_when_done threads through the same way as nav_icons --
        # see TestVerbParadigmDrillForm for the full battery.
        state = self._state(words=[], hist=[self._VOCAB[0]])
        result = self._call(gu, state, None, _pdform([]), show_prev_when_done=True)
        assert isinstance(result[-1], list) and len(result[-1]) == 2

    def test_enter_on_correct_slot_advances_focus(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["καλός"] + [""] * 5, submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_adjective_slot", return_value=True), \
             patch.object(gu, "check_adjective_test", return_value=(False, "")):
            self._call(gu, state, cv, form)
        assert form.widget.focus_request == {"request_id": 1, "advance_to": 1}

    def test_adj_meta_omitted_falls_back_to_full_slots(self, gu):
        # REGRESSION: adj_meta used to be a required kwarg -- any caller
        # that forgot to compute/pass it crashed with TypeError the moment
        # a student picked a word. Omitting it now degrades to the full,
        # unfiltered per-mode slot list instead.
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["καλός"] + [""] * 5, submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_adjective_slot", return_value=True) as mock_slot, \
             patch.object(gu, "check_adjective_test", return_value=(False, "")):
            self._call_form(gu.adjective_paradigm_drill_form, state, cv, form)
        assert form.widget.focus_request == {"request_id": 1, "advance_to": 1}
        mock_slot.assert_called_with(cv["form"], "simple", 0, "καλός", active_slots=gu._adj_slot_list("simple"))

    def test_next_button_persists_and_advances_regardless_of_correctness(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        with patch.object(gu, "check_adjective_test", return_value=(False, "")):
            result = self._call(gu, state, cv, _pdform(["asd"] * 6), nxt_v=1)
        assert result == "*...*"
        assert cv not in state["words"][2][0]
        assert cv in state["hist"][2][0]

    def test_prev_button_restores_previous_word(self, gu):
        prev_word = self._VOCAB[1]
        cv = self._VOCAB[0]
        state = self._state(hist=[prev_word])
        with patch.object(gu, "check_adjective_test", return_value=(False, "")):
            result = self._call(gu, state, cv, _pdform([""] * 6), prev_v=1)
        assert result == "*...*"
        assert state["words"][2][0][0] == prev_word
        assert state["hist"][2][0] == []


# ──────────────────────────────── pronoun_paradigm_drill_form ──

class TestPronounParadigmDrillForm(_ParadigmDrillFormBase):
    """Minimal coverage for the pron_meta=None fallback specifically --
    the full Enter/check/next/prev/restart behavior is exercised in depth
    by the verb/noun/adjective siblings above (all four share the same
    _paradigm_drill_form engine); no need to re-duplicate that here.
    """
    _VOCAB = [{"form": "κανένας", "meaning": "no one"}, {"form": "ίδιος", "meaning": "same"}]

    def test_pron_meta_omitted_falls_back_to_full_slots(self, gu):
        # REGRESSION: pron_meta used to be a required kwarg -- any caller
        # that forgot to compute/pass it crashed with TypeError the moment
        # a student picked a word. Omitting it now degrades to the full,
        # unfiltered per-mode slot list instead.
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["κανένας"] + [""] * 5, submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_pronoun_slot", return_value=True) as mock_slot, \
             patch.object(gu, "check_pronoun_test", return_value=(False, "")):
            self._call_form(gu.pronoun_paradigm_drill_form, state, cv, form)
        assert form.widget.focus_request == {"request_id": 1, "advance_to": 1}
        mock_slot.assert_called_with(cv["form"], "simple", 0, "κανένας", active_slots=gu._pronoun_slot_list("simple"))

    def test_error_tracking_wiring_reaches_pronoun(self, gu):
        # Confirms get_errors/set_errors/get_retry_cnt/set_retry_cnt reach
        # this sibling's own _pack_paradigm_state/_paradigm_drill_form call
        # -- the full behavior (increment-on-wrong, retry-filters-words,
        # restart-clears) is exercised in depth on the verb sibling above.
        cv = self._VOCAB[0]
        state = self._state()
        get_errors, set_errors, errors_box = _pair({})
        get_retry_cnt, set_retry_cnt, _ = _pair(0)
        form = _pdform(["κανένας"] + [""] * 5)
        with patch.object(gu, "check_pronoun_test", return_value=(False, "")):
            self._call_form(gu.pronoun_paradigm_drill_form, state, cv, form, check_v=1,
                            get_errors=get_errors, set_errors=set_errors,
                            get_retry_cnt=get_retry_cnt, set_retry_cnt=set_retry_cnt)
        assert errors_box[0] == {"κανένας": 1}

    def test_lang_reaches_check_pronoun_test(self, gu):
        # Same regression as verb_paradigm_drill_form -- pronoun_paradigm_drill_form
        # had no lang param at all before.
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["asd"] * 6)
        with patch.object(gu, "check_pronoun_test", return_value=(False, "")) as m:
            self._call_form(gu.pronoun_paradigm_drill_form, state, cv, form, check_v=1, lang="el")
        assert m.call_args.kwargs.get("lang") == "el"

    def test_nav_icons_hides_prev_with_no_history(self, gu):
        # nav_icons threads through to _paradigm_drill_form the same way as
        # verb -- see TestVerbParadigmDrillForm for the full row/hide battery.
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform([""] * 6)
        result = self._call_form(gu.pronoun_paradigm_drill_form, state, cv, form, nav_icons=True)
        assert len(result[-2]) == 2

    def test_config_nav_icons_true_used_with_no_explicit_kwarg(self):
        gu = GreekUtils(_StubBackend(), _FormMo(), config=_NAV_ICONS_CONFIG)
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform([""] * 6)
        result = self._call_form(gu.pronoun_paradigm_drill_form, state, cv, form)
        assert len(result[-2]) == 2

    def test_show_prev_when_done_reaches_paradigm_drill_form(self, gu):
        # show_prev_when_done threads through the same way as nav_icons --
        # see TestVerbParadigmDrillForm for the full battery.
        state = self._state(words=[], hist=[self._VOCAB[0]])
        result = self._call_form(gu.pronoun_paradigm_drill_form, state, None, _pdform([]),
                                 show_prev_when_done=True)
        assert isinstance(result[-1], list) and len(result[-1]) == 2


# ──────────────────────────────── make_item_drill_rows use_diacritics ──

class TestMakeItemDrillRowsDiacritics:
    def test_use_diacritics_creates_diacritics_widgets(self):
        gu = GreekUtils(_StubBackend(), _DrillMo())
        items = [{"meaning": "write", "sg": "γράφε"}]
        fake_widget = MagicMock()
        fake_widget.value = ""
        with patch("eee_project.notebook_utils.diacritics_text", return_value=fake_widget) as mock_dt:
            inputs_2d, _ = gu.make_item_drill_rows(items, ["sg"], use_diacritics=True)
        mock_dt.assert_called()
        assert inputs_2d[0][0] is fake_widget


# ──────────────────────────────── word_drill_display branches ──

class TestWordDrillDisplay:
    def test_done_shows_callout_and_next_btn(self, gu_form):
        btn = _FakeBtn(value=0, label="Пройти снова")
        with pytest.raises(StopIteration) as exc_info:
            gu_form.word_drill_display(
                None, [], {"correct": 2, "total": 3}, None,
                _FakeWI(""), _FakeWI("")._ui, _FakeBtn(None), _FakeBtn(None), btn,
                vocab=[{"meaning": "write", "form": "γράφε"}],
            )
        content = exc_info.value.args[0]
        assert "callout" in str(content)
        assert content[-1] is btn

    def test_done_with_show_prev_when_done_includes_prev(self, gu_form):
        next_btn = _FakeBtn(value=0, label="↺")
        prev_btn = _FakeBtn(value=0, label="◀")
        with pytest.raises(StopIteration) as exc_info:
            gu_form.word_drill_display(
                None, [], {"correct": 2, "total": 3}, None,
                _FakeWI(""), _FakeWI("")._ui, _FakeBtn(None), prev_btn, next_btn,
                vocab=[{"meaning": "write", "form": "γράφε"}],
                show_prev_when_done=True,
            )
        content = exc_info.value.args[0]
        assert content[-1] == [prev_btn, next_btn]

    def test_done_without_show_prev_when_done_keeps_next_btn_bare(self, gu_form):
        # Default False -- every existing caller keeps today's exact shape
        # (a bare next_btn, not wrapped in an hstack with anything).
        next_btn = _FakeBtn(value=0, label="↺")
        with pytest.raises(StopIteration) as exc_info:
            gu_form.word_drill_display(
                None, [], {"correct": 2, "total": 3}, None,
                _FakeWI(""), _FakeWI("")._ui, _FakeBtn(None), _FakeBtn(None), next_btn,
                vocab=[{"meaning": "write", "form": "γράφε"}],
            )
        content = exc_info.value.args[0]
        assert content[-1] is next_btn

    def test_check_branch_gives_feedback(self, gu_form):
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("γράφε")
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, _FakeBtn(1), _FakeBtn(None), _FakeBtn(None),
            vocab=[cv],
        )
        assert "✓" in str(result)

    def test_restore_entry_branch(self, gu_form):
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("")
        result = gu_form.word_drill_display(
            cv, [], {"correct": 1, "total": 1}, {"correct": True},
            wi, wi._ui, _FakeBtn(None), _FakeBtn(None), _FakeBtn(None),
            vocab=[cv],
        )
        assert "✓" in str(result)

    def test_title_included(self, gu_form):
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("")
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, _FakeBtn(None), _FakeBtn(None), _FakeBtn(None),
            vocab=[cv], title="## My Exercise",
        )
        assert "My Exercise" in str(result)

    def test_comment_included(self, gu_form):
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("")
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, _FakeBtn(None), _FakeBtn(None), _FakeBtn(None),
            vocab=[cv], comment="Note: hard",
        )
        assert "Note" in str(result)

    def test_default_lang_is_russian(self, gu_form):
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("")
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, _FakeBtn(None), _FakeBtn(None), _FakeBtn(None),
            vocab=[cv],
        )
        assert "правильно" in str(result)

    def test_lang_en_changes_progress_label(self, gu_form):
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("")
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, _FakeBtn(None), _FakeBtn(None), _FakeBtn(None),
            vocab=[cv], lang="en",
        )
        assert "correct" in str(result)
        assert "правильно" not in str(result)

    def test_default_button_row_order_unchanged(self, gu_form):
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("")
        check_btn, prev_btn, next_btn = _FakeBtn(None), _FakeBtn(None), _FakeBtn(None)
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, check_btn, prev_btn, next_btn,
            vocab=[cv],
        )
        assert result[-1] == [check_btn, prev_btn, next_btn]

    def test_nav_icons_reorders_prev_check_next(self, gu_form):
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("")
        check_btn, prev_btn, next_btn = _FakeBtn(None), _FakeBtn(None), _FakeBtn(None)
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, check_btn, prev_btn, next_btn,
            vocab=[cv], nav_icons=True,
        )
        assert result[-1] == [prev_btn, check_btn, next_btn]

    def test_nav_icons_hides_disabled_prev(self, gu_form):
        # A real mo.ui.button has no readable .disabled after construction
        # (only an internal frontend arg) -- word_drill_display can't
        # introspect the passed-in button for this, it needs the explicit
        # prev_disabled flag the caller already knows.
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("")
        check_btn, prev_btn, next_btn = _FakeBtn(None), _FakeBtn(None), _FakeBtn(None)
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, check_btn, prev_btn, next_btn,
            vocab=[cv], nav_icons=True, prev_disabled=True,
        )
        assert result[-1] == [check_btn, next_btn]

    def test_default_mode_keeps_disabled_button_visible(self, gu_form):
        # Without nav_icons, prev_disabled=True is ignored -- Prev stays
        # visible (real marimo still greys it out client-side via its own
        # disabled arg on the button itself), as before this fix. Only the
        # icon mode hides it, matching eee_footer's own ◀/▶ convention.
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("")
        check_btn, prev_btn, next_btn = _FakeBtn(None), _FakeBtn(None), _FakeBtn(None)
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, check_btn, prev_btn, next_btn,
            vocab=[cv], prev_disabled=True,
        )
        assert result[-1] == [check_btn, prev_btn, next_btn]

    # `checked`: needed because a check_btn built via word_drill_check_button
    # rebuilds (resetting its own transient click value) the instant a check
    # attempt updates the "checked" state it's colored from -- without this,
    # the very re-render that update triggers would show plain meaning text
    # instead of feedback, since check_btn.value has already reset to falsy
    # by the time it re-renders. Confirmed live: a real Check click on a
    # wrong answer showed no feedback at all until this was added.

    def test_checked_matching_typed_shows_feedback_even_when_check_btn_falsy(self, gu_form):
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("wrong")
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, _FakeBtn(None), _FakeBtn(None), _FakeBtn(None),
            vocab=[cv], checked="wrong",
        )
        assert "✗" in str(result)

    def test_checked_not_matching_typed_shows_plain_meaning(self, gu_form):
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("wrong")
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, _FakeBtn(None), _FakeBtn(None), _FakeBtn(None),
            vocab=[cv], checked="something else entirely",
        )
        assert "write" in str(result)
        assert "✗" not in str(result)

    def test_checked_none_default_unaffected(self, gu_form):
        # Odyssey and any other existing caller never passes `checked` --
        # must behave exactly as before this fix (no feedback from typing
        # alone, with no check_btn/_enter signal either).
        cv = {"meaning": "write", "form": "γράφε"}
        wi = _FakeWI("wrong")
        result = gu_form.word_drill_display(
            cv, [], {"correct": 0, "total": 0}, None,
            wi, wi._ui, _FakeBtn(None), _FakeBtn(None), _FakeBtn(None),
            vocab=[cv],
        )
        assert "✗" not in str(result)
        assert "✓" not in str(result)


# ──────────────────────────────── _drill_done_content ──

class TestDrillDoneContent:
    def test_message_only(self, gu_form):
        result = gu_form._drill_done_content("All done!")
        assert result == [("callout", "success", "All done!")]

    def test_message_and_score_line(self, gu_form):
        result = gu_form._drill_done_content("All done!", score_line="❌ 1 / 2")
        assert result[1] == "❌ 1 / 2"

    def test_falsy_score_line_omitted(self, gu_form):
        result = gu_form._drill_done_content("All done!", score_line="")
        assert len(result) == 1

    def test_no_buttons_omits_row_entirely(self, gu_form):
        result = gu_form._drill_done_content("All done!")
        assert len(result) == 1

    def test_none_buttons_list_same_as_no_buttons(self, gu_form):
        result = gu_form._drill_done_content("All done!", buttons=[None, None])
        assert len(result) == 1

    def test_single_button_rendered_bare(self, gu_form):
        btn = _FakeBtn(label="Start over")
        result = gu_form._drill_done_content("All done!", buttons=[btn])
        assert result[-1] is btn

    def test_none_entries_filtered_before_bare_check(self, gu_form):
        # A single real button survives filtering alongside Nones and still
        # renders bare, not wrapped in a one-item hstack.
        btn = _FakeBtn(label="Start over")
        result = gu_form._drill_done_content("All done!", buttons=[None, btn, None])
        assert result[-1] is btn

    def test_multiple_buttons_hstacked_in_order(self, gu_form):
        a, b = _FakeBtn(label="a"), _FakeBtn(label="b")
        result = gu_form._drill_done_content("All done!", buttons=[a, b])
        assert result[-1] == [a, b]

    def test_three_buttons_with_none_hstacks_remaining_two(self, gu_form):
        prev, main, extra = _FakeBtn(label="prev"), _FakeBtn(label="main"), _FakeBtn(label="extra")
        result = gu_form._drill_done_content("All done!", buttons=[None, main, extra])
        assert result[-1] == [main, extra]
        result2 = gu_form._drill_done_content("All done!", buttons=[prev, main, None])
        assert result2[-1] == [prev, main]


# ──────────────────────────────── _quiz_done_stop ──

class TestQuizDoneStop:
    def test_calls_mo_stop(self, gu_form):
        with pytest.raises(StopIteration):
            gu_form._quiz_done_stop({"correct": 3, "total": 5}, "ru")

    def test_no_next_btn_omits_it_from_content(self, gu_form):
        with pytest.raises(StopIteration) as exc_info:
            gu_form._quiz_done_stop({"correct": 3, "total": 5}, "ru")
        assert len(exc_info.value.args[0]) == 2

    def test_next_btn_appended_to_content(self, gu_form):
        btn = _FakeBtn(value=0, label="Следующий")
        with pytest.raises(StopIteration) as exc_info:
            gu_form._quiz_done_stop({"correct": 3, "total": 5}, "ru", next_btn=btn)
        content = exc_info.value.args[0]
        assert len(content) == 3
        assert content[2] is btn

    def test_prev_btn_alone_without_next_btn_is_ignored(self, gu_form):
        # prev_btn only makes sense alongside a restart action -- passing it
        # with no next_btn (shouldn't happen from a real caller, but must
        # not silently show a lone Prev with nothing else) omits it too.
        prev = _FakeBtn(value=0, label="◀")
        with pytest.raises(StopIteration) as exc_info:
            gu_form._quiz_done_stop({"correct": 3, "total": 5}, "ru", prev_btn=prev)
        assert len(exc_info.value.args[0]) == 2

    def test_prev_and_next_btn_hstacked_together(self, gu_form):
        prev = _FakeBtn(value=0, label="◀")
        next_ = _FakeBtn(value=0, label="↺")
        with pytest.raises(StopIteration) as exc_info:
            gu_form._quiz_done_stop({"correct": 3, "total": 5}, "ru", next_btn=next_, prev_btn=prev)
        content = exc_info.value.args[0]
        assert len(content) == 3
        assert content[2] == [prev, next_]

    def test_done_message_names_the_actual_restart_button(self, gu_form):
        # The done screen's restart button is always labeled _NAV_AGAIN
        # ("Пройти снова"), never _NAV_NEXT -- the message must say so,
        # not reference a different button's label.
        with pytest.raises(StopIteration) as exc_info:
            gu_form._quiz_done_stop({"correct": 3, "total": 5}, "ru")
        text = str(exc_info.value.args[0][0])
        assert "Пройти снова" in text
        assert "Следующее" not in text


# ──────────────────────────────── word_quiz_question ──

class TestWordQuizQuestion:
    def test_word_none_calls_stop(self, gu_form):
        with pytest.raises(StopIteration):
            gu_form.word_quiz_question(None, _WQ_VOCAB, "ru", __import__("random"))

    def test_builds_radio_with_choices(self, gu_form):
        import random
        radio, word = gu_form.word_quiz_question(_WQ_VOCAB[0], _WQ_VOCAB, "ru", random)
        assert word == _WQ_VOCAB[0]
        assert _WQ_VOCAB[0]["form"] in radio.options
        assert len(radio.options) > 1

    def test_initial_value_set_when_in_choices(self, gu_form):
        import random
        w = _WQ_VOCAB[0]
        radio, _ = gu_form.word_quiz_question(w, _WQ_VOCAB, "ru", random, initial_value=w["form"])
        assert radio.value == w["form"]

    def test_initial_value_ignored_when_not_in_choices(self, gu_form):
        import random
        radio, _ = gu_form.word_quiz_question(_WQ_VOCAB[0], _WQ_VOCAB, "ru", random,
                                          initial_value="NOT_IN_OPTIONS")
        assert radio.value is None

    def test_context_in_label(self, gu_form):
        import random
        w = {"meaning": "say", "form": "λέγω", "lemma": "λέγω", "context": "Homer"}
        radio, _ = gu_form.word_quiz_question(w, [w], "ru", random)
        assert radio is not None  # exercises the context branch (label not stored by stub)


# ──────────────────────────────── word_quiz_feedback ──

class TestWordQuizFeedback:
    def test_word_none_total_zero_returns_empty(self, gu_form):
        result = gu_form.word_quiz_feedback(None, None, {"correct": 0, "total": 0}, "ru")
        assert result == ""

    def test_word_none_total_nonzero_calls_stop(self, gu_form):
        with pytest.raises(StopIteration):
            gu_form.word_quiz_feedback(None, None, {"correct": 3, "total": 5}, "ru")

    def test_answer_none_returns_empty(self, gu_form):
        w = {"form": "λέγω", "lemma": "λέγω", "pos": "verb", "grammar": ""}
        result = gu_form.word_quiz_feedback(w, None, {"correct": 0, "total": 0}, "ru")
        assert result == ""

    def test_correct_answer_success_callout(self, gu_form):
        w = {"form": "λέγω", "lemma": "λέγω", "pos": "verb", "grammar": ""}
        result = gu_form.word_quiz_feedback(w, "λέγω", {"correct": 0, "total": 1}, "ru")
        assert "success" in str(result)

    def test_wrong_answer_danger_callout(self, gu_form):
        w = {"form": "λέγω", "lemma": "λέγω", "pos": "verb", "grammar": ""}
        result = gu_form.word_quiz_feedback(w, "ἀκούω", {"correct": 0, "total": 1}, "ru")
        assert "danger" in str(result)

    def test_form_ne_lemma_shows_arrow(self, gu_form):
        w = {"form": "λέγει", "lemma": "λέγω", "pos": "verb", "grammar": ""}
        result = gu_form.word_quiz_feedback(w, "λέγει", {"correct": 0, "total": 0}, "ru")
        assert "→" in str(result)

    def test_canonical_ancient_greek_inflected_form(self, gu_form):
        """ἔγνω → γιγνώσκω: the real Odyssey case motivating the form/lemma
        contract (surface aorist form, distinct dictionary present-tense lemma).
        Canonical regression fixture for any future form/lemma refactoring."""
        w = {"form": "ἔγνω", "lemma": "γιγνώσκω", "pos": "verb", "grammar": ""}
        result = gu_form.word_quiz_feedback(w, "ἔγνω", {"correct": 0, "total": 0}, "ru")
        assert "ἔγνω" in str(result)
        assert "γιγνώσκω" in str(result)
        assert "→" in str(result)

    def test_missing_lemma_falls_back_to_form_no_arrow(self, gu_form):
        w = {"form": "λέγω", "pos": "verb", "grammar": ""}
        result = gu_form.word_quiz_feedback(w, "λέγω", {"correct": 0, "total": 0}, "ru")
        assert "→" not in str(result)
        assert "λέγω" in str(result)

    def test_paradigm_table_called_on_correct(self, gu_form):
        w = {"form": "λέγω", "lemma": "λέγω", "pos": "verb", "grammar": ""}
        called = [False]
        def _pt(word, lang="ru"):
            called[0] = True
            return "<table/>'"
        gu_form.word_quiz_feedback(w, "λέγω", {"correct": 0, "total": 0}, "ru", build_paradigm_table=_pt)
        assert called[0]

    def test_paradigm_table_none_result_ignored(self, gu_form):
        w = {"form": "λέγω", "lemma": "λέγω", "pos": "verb", "grammar": ""}
        result = gu_form.word_quiz_feedback(w, "λέγω", {"correct": 0, "total": 0}, "ru",
                                        build_paradigm_table=lambda w, lang="ru": None)
        assert "success" in str(result)

    def test_paradigm_table_exception_renders_error(self, gu_form):
        w = {"form": "λέγω", "lemma": "λέγω", "pos": "verb", "grammar": ""}
        def _bad(word, lang="ru"): raise ValueError("boom")
        result = gu_form.word_quiz_feedback(w, "λέγω", {"correct": 0, "total": 0}, "ru",
                                        build_paradigm_table=_bad)
        assert "boom" in str(result)


# ──────────────────────────────── load_vocab_tsv ──

class TestLoadVocabTsv:
    def test_basic_load(self, gu_marimo, tmp_path):
        tsv = tmp_path / "vocab.tsv"
        tsv.write_text("Word\tTranslation\nλύω\tloosen\nθεός\tgod\n", encoding="utf-8")
        result = gu_marimo.load_vocab_tsv("vocab.tsv", nb_dir=tmp_path)
        assert len(result) == 2
        assert result[0]["form"] == "λύω"
        assert result[0]["meaning"] == "loosen"
        assert result[1]["form"] == "θεός"

    def test_no_lemma_or_context_keys(self, gu_marimo, tmp_path):
        tsv = tmp_path / "vocab.tsv"
        tsv.write_text("Word\tTranslation\nλύω\tloosen\n", encoding="utf-8")
        result = gu_marimo.load_vocab_tsv("vocab.tsv", nb_dir=tmp_path)
        assert "lemma" not in result[0]
        assert "context" not in result[0]

    def test_multiple_files(self, gu_marimo, tmp_path):
        (tmp_path / "a.tsv").write_text("Word\tTranslation\nλύω\tloosen\n", encoding="utf-8")
        (tmp_path / "b.tsv").write_text("Word\tTranslation\nθεός\tgod\n", encoding="utf-8")
        result = gu_marimo.load_vocab_tsv("a.tsv", "b.tsv", nb_dir=tmp_path)
        assert len(result) == 2

    def test_missing_no_remote_raises(self, gu_marimo, tmp_path):
        with pytest.raises(FileNotFoundError):
            gu_marimo.load_vocab_tsv("missing.tsv", nb_dir=tmp_path)

    def test_missing_remote_fetch_fails_raises(self, gu_marimo, tmp_path):
        with patch("urllib.request.urlopen", side_effect=Exception("net")):
            with pytest.raises(FileNotFoundError):
                gu_marimo.load_vocab_tsv("missing.tsv", nb_dir=tmp_path,
                                   remote_base="https://example.com")

    def test_load_vocab_tsv_skips_blank_words(self, gu_marimo, tmp_path):
        tsv = tmp_path / "vocab.tsv"
        tsv.write_text("Word\tTranslation\n   \tloosen\n" + "θεός\tgod\n", encoding="utf-8")
        result = gu_marimo.load_vocab_tsv("vocab.tsv", nb_dir=tmp_path)
        assert len(result) == 1
        assert result[0]["form"] == "θεός"

    def test_load_vocab_tsv_remote_fetch_success(self, gu_marimo, tmp_path):
        content = "Word\tTranslation\nλύω\tloosen\n"
        with patch("urllib.request.urlopen", return_value=_make_resp(content.encode("utf-8"))):
            result = gu_marimo.load_vocab_tsv("remote.tsv", nb_dir=tmp_path,
                                        remote_base="https://example.com")
        assert len(result) == 1


# ──────────────────────────────────────── vocab_table ──

class TestVocabTable:
    def test_none_df_returns_none(self, gu_marimo):
        assert gu_marimo.vocab_table(None) is None

    def test_page_size_matches_row_count(self, gu_marimo):
        import pandas as pd
        df = pd.DataFrame({"Word": ["a", "b", "c"], "Translation": ["x", "y", "z"]})
        table = gu_marimo.vocab_table(df)
        assert table._component_args["page-size"] == 3

    def test_no_select_state_no_initial_selection_selects_nothing(self, gu_marimo):
        import pandas as pd
        df = pd.DataFrame({"Word": ["a", "b"], "Translation": ["x", "y"]})
        table = gu_marimo.vocab_table(df)
        assert table.value.empty

    def test_select_state_returning_none_selects_every_row(self, gu_marimo):
        import pandas as pd
        df = pd.DataFrame({"Word": ["a", "b", "c"], "Translation": ["x", "y", "z"]})
        table = gu_marimo.vocab_table(df, select_state=lambda: None)
        assert len(table.value) == 3

    def test_select_state_returning_a_selection_is_used_as_is(self, gu_marimo):
        import pandas as pd
        df = pd.DataFrame({"Word": ["a", "b", "c"], "Translation": ["x", "y", "z"]})
        table = gu_marimo.vocab_table(df, select_state=lambda: [1])
        assert list(table.value["Word"]) == ["b"]

    def test_initial_selection_passthrough_when_no_select_state(self, gu_marimo):
        import pandas as pd
        df = pd.DataFrame({"Word": ["a", "b", "c"], "Translation": ["x", "y", "z"]})
        table = gu_marimo.vocab_table(df, initial_selection=[0, 2])
        assert list(table.value["Word"]) == ["a", "c"]

    def test_wraps_all_columns_not_just_word_translation(self, gu_marimo):
        # A long phrase (e.g. a "Useful Phrases" quiz row) must wrap instead
        # of being cut off mid-word -- derived from df.columns, not a
        # hardcoded ["Word", "Translation"], since mo.ui.table raises if a
        # named column doesn't exist (e.g. Kapodistrias's extra "Type" col).
        import pandas as pd
        df = pd.DataFrame({"Word": ["a"], "Translation": ["b"], "Type": ["noun"]})
        table = gu_marimo.vocab_table(df)
        assert set(table._component_args["wrapped-columns"]) == {"Word", "Translation", "Type"}


# ──────────────────────────────────── load_vocab_table ──

class TestLoadVocabTable:
    def test_basic_load(self, gu_marimo, tmp_path):
        (tmp_path / "nouns.tsv").write_text("Word\tTranslation\nλύω\tloosen\n", encoding="utf-8")
        df = gu_marimo.load_vocab_table("nouns.tsv", nb_dir=tmp_path)
        assert list(df["Word"]) == ["λύω"]

    def test_missing_no_remote_returns_none(self, gu_marimo, tmp_path):
        assert gu_marimo.load_vocab_table("missing.tsv", nb_dir=tmp_path) is None

    def test_missing_remote_fetch_fails_returns_none(self, gu_marimo, tmp_path):
        with patch("urllib.request.urlopen", side_effect=Exception("net")):
            result = gu_marimo.load_vocab_table("missing.tsv", nb_dir=tmp_path,
                                                 remote_base="https://example.com")
        assert result is None

    def test_ru_variant_prefers_ru_file_when_language_ru(self, gu_marimo, tmp_path):
        (tmp_path / "nouns.tsv").write_text("Word\tTranslation\nλύω\tloosen\n", encoding="utf-8")
        (tmp_path / "nouns_ru.tsv").write_text("Word\tTranslation\nслово\tслово-en\n", encoding="utf-8")
        df = gu_marimo.load_vocab_table("nouns.tsv", nb_dir=tmp_path, ru_variant=True, language="ru")
        assert list(df["Word"]) == ["слово"]

    def test_ru_variant_ignored_when_language_not_ru(self, gu_marimo, tmp_path):
        (tmp_path / "nouns.tsv").write_text("Word\tTranslation\nλύω\tloosen\n", encoding="utf-8")
        (tmp_path / "nouns_ru.tsv").write_text("Word\tTranslation\nслово\tслово-en\n", encoding="utf-8")
        df = gu_marimo.load_vocab_table("nouns.tsv", nb_dir=tmp_path, ru_variant=True, language="en")
        assert list(df["Word"]) == ["λύω"]

    def test_ru_variant_falls_back_to_plain_when_ru_file_absent(self, gu_marimo, tmp_path):
        (tmp_path / "nouns.tsv").write_text("Word\tTranslation\nλύω\tloosen\n", encoding="utf-8")
        df = gu_marimo.load_vocab_table("nouns.tsv", nb_dir=tmp_path, ru_variant=True, language="ru")
        assert list(df["Word"]) == ["λύω"]

    def test_file_upload_overrides_bundled_file(self, tmp_path):
        # load_data (called on the upload path) needs pd_module set, unlike
        # the bundled-file path which imports pandas locally -- gu_marimo
        # doesn't pass one, so this test builds its own instance.
        import pandas as pd
        gu = GreekUtils(mo_module=mo, pd_module=pd, config=ANCIENT_GREEK)
        (tmp_path / "nouns.tsv").write_text("Word\tTranslation\nλύω\tloosen\n", encoding="utf-8")
        upload = MagicMock()
        upload.value = [MagicMock(contents="Word\tTranslation\nθεός\tgod\n".encode("utf-8"))]
        df = gu.load_vocab_table("nouns.tsv", nb_dir=tmp_path, file_upload=upload)
        assert list(df["Word"]) == ["θεός"]

    def test_no_file_upload_value_uses_bundled_file(self, gu_marimo, tmp_path):
        (tmp_path / "nouns.tsv").write_text("Word\tTranslation\nλύω\tloosen\n", encoding="utf-8")
        upload = MagicMock()
        upload.value = None
        df = gu_marimo.load_vocab_table("nouns.tsv", nb_dir=tmp_path, file_upload=upload)
        assert list(df["Word"]) == ["λύω"]


# ──────────────────────────────── load_inflected_vocab_tsv ──

class TestLoadInflectedVocabTsv:
    def test_basic_load(self, gu_marimo, tmp_path):
        tsv = tmp_path / "vocab.tsv"
        tsv.write_text(
            "form\tlemma\tpos\tcontext\tmeaning\n"
            "Ἄνδρα\tἀνήρ\tnoun\tI.1: Ἄνδρα μοι ἔννεπε\tмужа\n",
            encoding="utf-8",
        )
        result = gu_marimo.load_inflected_vocab_tsv("vocab.tsv", nb_dir=tmp_path)
        assert len(result) == 1
        assert result[0]["form"] == "Ἄνδρα"
        assert result[0]["lemma"] == "ἀνήρ"
        assert result[0]["pos"] == "noun"
        assert result[0]["context"] == "I.1: Ἄνδρα μοι ἔννεπε"
        assert result[0]["meaning"] == "мужа"

    def test_form_can_differ_from_lemma(self, gu_marimo, tmp_path):
        tsv = tmp_path / "vocab.tsv"
        tsv.write_text(
            "form\tlemma\tpos\tcontext\tmeaning\nἔγνω\tγιγνώσκω\tverb\t...\tузнал\n",
            encoding="utf-8",
        )
        result = gu_marimo.load_inflected_vocab_tsv("vocab.tsv", nb_dir=tmp_path)
        assert result[0]["form"] != result[0]["lemma"]

    def test_multiple_files(self, gu_marimo, tmp_path):
        (tmp_path / "a.tsv").write_text(
            "form\tlemma\tpos\tcontext\tmeaning\nἔγνω\tγιγνώσκω\tverb\t...\tузнал\n", encoding="utf-8")
        (tmp_path / "b.tsv").write_text(
            "form\tlemma\tpos\tcontext\tmeaning\nθεός\tθεός\tnoun\t...\tбог\n", encoding="utf-8")
        result = gu_marimo.load_inflected_vocab_tsv("a.tsv", "b.tsv", nb_dir=tmp_path)
        assert len(result) == 2

    def test_missing_no_remote_raises(self, gu_marimo, tmp_path):
        with pytest.raises(FileNotFoundError):
            gu_marimo.load_inflected_vocab_tsv("missing.tsv", nb_dir=tmp_path)

    def test_missing_remote_fetch_fails_raises(self, gu_marimo, tmp_path):
        with patch("urllib.request.urlopen", side_effect=Exception("net")):
            with pytest.raises(FileNotFoundError):
                gu_marimo.load_inflected_vocab_tsv("missing.tsv", nb_dir=tmp_path,
                                   remote_base="https://example.com")

    def test_remote_fetch_success(self, gu_marimo, tmp_path):
        content = "form\tlemma\tpos\tcontext\tmeaning\nἔγνω\tγιγνώσκω\tverb\t...\tузнал\n"
        with patch("urllib.request.urlopen", return_value=_make_resp(content.encode("utf-8"))):
            result = gu_marimo.load_inflected_vocab_tsv("remote.tsv", nb_dir=tmp_path,
                                        remote_base="https://example.com")
        assert len(result) == 1


# ──────────────────────────────── word_write_question ──

class TestWordWriteQuestion:
    def test_word_none_calls_stop(self, gu_form):
        with pytest.raises(StopIteration):
            gu_form.word_write_question(None, "ru")

    def test_returns_widget(self, gu_form):
        fake_w = MagicMock()
        with patch("eee_project.notebook_utils.diacritics_text", return_value=fake_w):
            widget = gu_form.word_write_question({"form": "λύω", "meaning": "loosen"}, "ru")
        assert widget is fake_w

    def test_passes_config_polytonic(self, gu_form):
        # gu_form defaults to MODERN_GREEK (polytonic=False) -- must reach
        # the underlying widget, not silently stay at the module function's
        # own polytonic=True default (the original Ancient-Greek-only bug:
        # a Modern Greek phrase drill showed the full breathing/circumflex
        # mark set, confusing for post-1982 monotonic orthography).
        with patch("eee_project.notebook_utils.diacritics_text", return_value=MagicMock()) as mock_fn:
            gu_form.word_write_question({"form": "λύω", "meaning": "loosen"}, "ru")
        assert mock_fn.call_args.kwargs["polytonic"] is False


# ──────────────────────────────── GreekUtils.diacritics_text method ──

class TestGreekUtilsDiacriticsTextMethod:
    def test_delegates_to_module_function(self, gu_form):
        with patch("eee_project.notebook_utils.diacritics_text", return_value="widget") as mock_fn:
            result = gu_form.diacritics_text(placeholder="test", label="lbl", value="v")
        assert result == "widget"
        mock_fn.assert_called_once()

    def test_defaults_to_config_polytonic(self, gu_form):
        # gu_form defaults to MODERN_GREEK (polytonic=False).
        with patch("eee_project.notebook_utils.diacritics_text", return_value="widget") as mock_fn:
            gu_form.diacritics_text()
        assert mock_fn.call_args.kwargs["polytonic"] is False

    def test_explicit_polytonic_overrides_config(self, gu_form):
        with patch("eee_project.notebook_utils.diacritics_text", return_value="widget") as mock_fn:
            gu_form.diacritics_text(polytonic=True)
        assert mock_fn.call_args.kwargs["polytonic"] is True


# ────────────────────────────────────────── stanza-match quiz (5a) ──

_SM_STANZAS = [
    {
        "ref": "I.1-2",
        "lines": ["Ἄνδρα μοι ἔννεπε, Μοῦσα, πολύτροπον, ὃς μάλα πολλὰ"],
        "interlinear": "",
        "translations": {
            "подстрочник": "Мужа мне назови, Муза, многообразного, который очень много",
            "Жуковский": "Муза, скажи мне о том многоопытном муже, который",
            "Вересаев": "О многоопытном муже мне, Муза, поведай, скиталец",
        },
    },
    {
        "ref": "I.3-4",
        "lines": ["πλάγχθη, ἐπεὶ Τροίης ἱερὸν πτολίεθρον ἔπερσε·"],
        "interlinear": "",
        "translations": {
            "подстрочник": "скитался, после того как Трои священный город разрушил",
            "Жуковский": "Странствуя долго со дня, как разрушил священную Трою",
            "Вересаев": "Много городов посетил он, разрушив священную Трою",
        },
    },
    {
        "ref": "I.5-6",
        "lines": ["πολλῶν δ᾽ ἀνθρώπων ἴδεν ἄστεα καὶ νόον ἔγνω,"],
        "interlinear": "",
        "translations": {
            "подстрочник": "многих людей увидел города и разум узнал",
            "Жуковский": "Многих людей города посетил и обычаи видел",
            "Вересаев": "—",
        },
    },
    {
        "ref": "I.7-9",
        "lines": ["πολλὰ δ᾽ ὅ γ᾽ ἐν πόντῳ πάθεν ἄλγεα ὃν κατὰ θυμόν,"],
        "interlinear": "",
        "translations": {
            "Жуковский": "X",  # deliberately tiny — must never pass the length veto
        },
    },
]


class TestStanzaMatchPickTranslation:
    def test_single_candidate_returned(self, gu_form):
        s = {"ref": "S.1", "lines": ["x"], "translations": {"Т": "text"}}
        assert gu_form._stanza_match_pick_translation(s) == ("Т", "text")

    def test_placeholder_only_returns_none(self, gu_form):
        s = {"ref": "S.1", "lines": ["x"], "translations": {"Т": "—"}}
        assert gu_form._stanza_match_pick_translation(s) is None

    def test_empty_translations_returns_none(self, gu_form):
        s = {"ref": "S.1", "lines": ["x"], "translations": {}}
        assert gu_form._stanza_match_pick_translation(s) is None

    def test_deterministic_across_repeated_calls(self, gu_form):
        s = _SM_STANZAS[0]
        assert (gu_form._stanza_match_pick_translation(s)
                == gu_form._stanza_match_pick_translation(s))

    def test_picks_are_balanced_across_translators(self, gu_form):
        # Same two translators, same dict order, on many differently-ref'd
        # stanzas -- dict-order-first would always return "A"; a balanced
        # pick must surface "B" for at least one of them.
        stanzas = [
            {"ref": f"BAL.{i}", "lines": ["x"],
             "translations": {"A": f"a{i}", "B": f"b{i}"}}
            for i in range(20)
        ]
        picked = {gu_form._stanza_match_pick_translation(s)[0] for s in stanzas}
        assert picked == {"A", "B"}

    def test_three_translators_all_represented(self, gu_form):
        # The real fixture shape (подстрочник/Жуковский/Вересаев) -- must not
        # always resolve to whichever sorts first in the dict.
        stanzas = [
            {"ref": f"TRI.{i}", "lines": ["x"],
             "translations": {"подстрочник": f"p{i}", "Жуковский": f"z{i}", "Вересаев": f"v{i}"}}
            for i in range(30)
        ]
        picked = {gu_form._stanza_match_pick_translation(s)[0] for s in stanzas}
        assert picked == {"подстрочник", "Жуковский", "Вересаев"}

    def test_valid_translators_filters_candidates(self, gu_form):
        stanzas = [
            {"ref": f"VLD.{i}", "lines": ["x"],
             "translations": {"A": f"a{i}", "B": f"b{i}", "C": f"c{i}"}}
            for i in range(20)
        ]
        picked = {gu_form._stanza_match_pick_translation(s, valid_translators=["A", "B"])[0]
                  for s in stanzas}
        assert picked == {"A", "B"}

    def test_valid_translators_none_means_all_allowed(self, gu_form):
        s = _SM_STANZAS[0]
        assert (gu_form._stanza_match_pick_translation(s, valid_translators=None)
                == gu_form._stanza_match_pick_translation(s))

    def test_valid_translators_excluding_all_returns_none(self, gu_form):
        s = {"ref": "S.1", "lines": ["x"], "translations": {"Т": "text"}}
        assert gu_form._stanza_match_pick_translation(s, valid_translators=["Other"]) is None


class TestStanzaMatchPromptAndCorrect:
    def test_grc_to_tr_prompt_is_greek_correct_is_translation(self, gu_form):
        prompt, correct = gu_form._stanza_match_prompt_and_correct(_SM_STANZAS[0], "grc_to_tr")
        assert prompt == "Ἄνδρα μοι ἔννεπε, Μοῦσα, πολύτροπον, ὃς μάλα πολλὰ"
        assert correct == "Мужа мне назови, Муза, многообразного, который очень много — подстрочник"

    def test_tr_to_grc_prompt_is_translation_correct_is_greek(self, gu_form):
        prompt, correct = gu_form._stanza_match_prompt_and_correct(_SM_STANZAS[0], "tr_to_grc")
        assert prompt == "> Мужа мне назови, Муза, многообразного, который очень много\n> — подстрочник"
        assert correct == "Ἄνδρα μοι ἔννεπε, Μοῦσα, πολύτροπον, ὃς μάλα πολλὰ"

    def test_deterministic_across_repeated_calls(self, gu_form):
        # No randomness involved — same stanza+direction always yields the same
        # pair, so widgets and form cells agree without sharing state.
        first = gu_form._stanza_match_prompt_and_correct(_SM_STANZAS[1], "grc_to_tr")
        second = gu_form._stanza_match_prompt_and_correct(_SM_STANZAS[1], "grc_to_tr")
        assert first == second

    def test_placeholder_translation_skipped(self, gu_form):
        # I.5-6's Вересаев entry is "—" — must fall through to Жуковский.
        _, correct = gu_form._stanza_match_prompt_and_correct(_SM_STANZAS[2], "grc_to_tr")
        assert correct == "Многих людей города посетил и обычаи видел — Жуковский"

    def test_no_translations_does_not_raise(self, gu_form):
        s = {"ref": "X.1", "lines": ["λόγος"], "translations": {}}
        prompt, correct = gu_form._stanza_match_prompt_and_correct(s, "grc_to_tr")
        assert prompt == "λόγος"
        assert correct == ""

    def test_tr_to_grc_without_translation_has_an_empty_prompt(self, gu_form):
        s = {"ref": "X.1", "lines": ["λόγος"], "translations": {}}
        prompt, correct = gu_form._stanza_match_prompt_and_correct(s, "tr_to_grc")
        assert prompt == ""
        assert correct == "λόγος"

    def test_valid_translators_restricts_pick(self, gu_form):
        _, correct = gu_form._stanza_match_prompt_and_correct(
            _SM_STANZAS[0], "grc_to_tr", valid_translators=["подстрочник"],
        )
        assert correct == "Мужа мне назови, Муза, многообразного, который очень много — подстрочник"


class TestStanzaMatchDistractorPool:
    def test_excludes_own_stanza(self, gu_form):
        pool = gu_form._stanza_match_distractor_pool(_SM_STANZAS[0], _SM_STANZAS, "grc_to_tr")
        assert all(ref != "I.1-2" for ref, _, _ in pool)

    def test_grc_to_tr_pool_is_translations(self, gu_form):
        pool = gu_form._stanza_match_distractor_pool(_SM_STANZAS[0], _SM_STANZAS, "grc_to_tr")
        texts = [t for _, _, t in pool]
        assert "Странствуя долго со дня, как разрушил священную Трою" in texts
        assert "—" not in texts  # placeholder translations excluded

    def test_grc_to_tr_pool_carries_each_candidate_own_translator(self, gu_form):
        pool = gu_form._stanza_match_distractor_pool(_SM_STANZAS[0], _SM_STANZAS, "grc_to_tr")
        by_text = {t: tr for _, tr, t in pool}
        assert by_text["Странствуя долго со дня, как разрушил священную Трою"] == "Жуковский"
        assert by_text["Много городов посетил он, разрушив священную Трою"] == "Вересаев"

    def test_tr_to_grc_pool_is_greek_lines(self, gu_form):
        pool = gu_form._stanza_match_distractor_pool(_SM_STANZAS[0], _SM_STANZAS, "tr_to_grc")
        texts = [t for _, _, t in pool]
        assert "πλάγχθη, ἐπεὶ Τροίης ἱερὸν πτολίεθρον ἔπερσε·" in texts

    def test_tr_to_grc_pool_has_no_translator(self, gu_form):
        pool = gu_form._stanza_match_distractor_pool(_SM_STANZAS[0], _SM_STANZAS, "tr_to_grc")
        assert all(tr is None for _, tr, _ in pool)

    def test_multiple_translators_all_included(self, gu_form):
        # I.3-4 has three live translators — all should appear in the grc_to_tr pool.
        pool = gu_form._stanza_match_distractor_pool(_SM_STANZAS[0], _SM_STANZAS, "grc_to_tr")
        refs_34 = [t for ref, _, t in pool if ref == "I.3-4"]
        assert len(refs_34) == 3

    def test_valid_translators_filters_grc_to_tr_pool(self, gu_form):
        pool = gu_form._stanza_match_distractor_pool(
            _SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", valid_translators=["Жуковский"],
        )
        translators = {tr for _, tr, _ in pool}
        assert translators == {"Жуковский"}

    def test_valid_translators_does_not_affect_tr_to_grc_pool(self, gu_form):
        # tr_to_grc distractors are plain Greek text, translator-agnostic --
        # filtering by translator must not remove any of them.
        pool_all = gu_form._stanza_match_distractor_pool(_SM_STANZAS[0], _SM_STANZAS, "tr_to_grc")
        pool_filtered = gu_form._stanza_match_distractor_pool(
            _SM_STANZAS[0], _SM_STANZAS, "tr_to_grc", valid_translators=["Жуковский"],
        )
        assert pool_all == pool_filtered


class TestStanzaMatchRound:
    def test_correct_always_among_options(self, gu_form):
        import random
        round_ = gu_form._stanza_match_round(_SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", random)
        assert round_["correct"] in round_["options"]

    def test_n_options_respected(self, gu_form):
        import random
        round_ = gu_form._stanza_match_round(_SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", random,
                                              n_options=3)
        assert len(round_["options"]) <= 3

    def test_distractors_never_equal_correct_by_normalized_text(self, gu_form):
        # Veto 1: even run many times (random sampling), no distractor should
        # normalize to the same text as the correct answer.
        import random
        for _ in range(20):
            round_ = gu_form._stanza_match_round(_SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", random)
            _norm = lambda t: " ".join(t.split()).strip().lower()
            _correct_norm = _norm(round_["correct"])
            others = [o for o in round_["options"] if o != round_["correct"]]
            assert all(_norm(o) != _correct_norm for o in others)

    def test_grc_to_tr_options_have_distinct_translators(self, gu_form):
        # Every option in a grc_to_tr round is attributed to a different
        # translator than every other option -- no translator repeats, even
        # though I.3-4 alone could supply a candidate for any of the three.
        import random
        for _ in range(20):
            round_ = gu_form._stanza_match_round(_SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", random)
            translators = [o.rsplit(" — ", 1)[-1] for o in round_["options"]]
            assert len(translators) == len(set(translators))

    def test_grc_to_tr_all_translators_represented(self, gu_form):
        # I.1-2 has all three translators live, and the default n_options=3
        # matches the translator count exactly -- every round must show
        # подстрочник, Жуковский, and Вересаев, not just whichever translator
        # happens to be listed first across the other stanzas.
        import random
        for _ in range(20):
            round_ = gu_form._stanza_match_round(_SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", random)
            translators = {o.rsplit(" — ", 1)[-1] for o in round_["options"]}
            assert translators == {"подстрочник", "Жуковский", "Вересаев"}

    def test_length_veto_excludes_tiny_outlier(self, gu_form):
        # I.7-9's "X" (1 char) is wildly shorter than I.1-2's ~60-char correct
        # answer and must never surface as a distractor, even though it's the
        # only Жуковский candidate available from that stanza -- I.3-4 and
        # I.5-6 both offer a length-comparable Жуковский alternative.
        import random
        for _ in range(20):
            round_ = gu_form._stanza_match_round(_SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", random)
            assert "X — Жуковский" not in round_["options"]

    def test_tr_to_grc_direction(self, gu_form):
        import random
        round_ = gu_form._stanza_match_round(_SM_STANZAS[0], _SM_STANZAS, "tr_to_grc", random)
        assert round_["correct"] == "Ἄνδρα μοι ἔννεπε, Μοῦσα, πολύτροπον, ὃς μάλα πολλὰ"
        assert round_["correct"] in round_["options"]

    def test_tr_to_grc_never_offers_a_normalized_duplicate_of_the_correct_text(self, gu_form):
        import random
        target = {"ref": "T.1", "lines": ["aaaa bbbb cccc"]}
        dup = {"ref": "T.2", "lines": ["  AAAA   bbbb cccc "]}
        other = {"ref": "T.3", "lines": ["dddd eeee ffff"]}
        round_ = gu_form._stanza_match_round(target, [target, dup, other], "tr_to_grc", random, n_options=10)
        assert sorted(round_["options"]) == ["aaaa bbbb cccc", "dddd eeee ffff"]

    def test_tr_to_grc_offers_at_most_one_option_per_stanza_ref(self, gu_form):
        import random
        target = {"ref": "T.1", "lines": ["aaaa bbbb cccc"]}
        twin_a = {"ref": "T.2", "lines": ["dddd eeee ffff"]}
        twin_b = {"ref": "T.2", "lines": ["gggg hhhh iiii"]}
        round_ = gu_form._stanza_match_round(target, [target, twin_a, twin_b], "tr_to_grc", random, n_options=10)
        twins = [o for o in round_["options"] if o in ("dddd eeee ffff", "gggg hhhh iiii")]
        assert len(twins) == 1

    def test_veto1_explicitly_excludes_normalized_duplicate(self, gu_form):
        # A different stanza whose translation differs from the correct answer
        # only by whitespace/case must never surface as a distractor — this is
        # the precise Veto-1 case (synonymy is out of scope, string-identity
        # after normalization is not).
        dup_stanza = {
            "ref": "DUP.1", "lines": ["δῆλον"],
            "translations": {"Т": "  МУЖА МНЕ назови, Муза,   многообразного, который очень много  "},
        }
        stanzas = _SM_STANZAS + [dup_stanza]
        import random
        for _ in range(20):
            round_ = gu_form._stanza_match_round(_SM_STANZAS[0], stanzas, "grc_to_tr", random)
            assert dup_stanza["translations"]["Т"] + " — Т" not in round_["options"]

    def test_valid_translators_restricts_whole_round(self, gu_form):
        import random
        for _ in range(20):
            round_ = gu_form._stanza_match_round(
                _SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", random,
                valid_translators=["Жуковский", "Вересаев"],
            )
            translators = {o.rsplit(" — ", 1)[-1] for o in round_["options"]}
            assert translators <= {"Жуковский", "Вересаев"}


class TestStanzaMatchQuestion:
    def test_stanza_none_calls_stop(self, gu_form):
        import random
        with pytest.raises(StopIteration):
            gu_form.stanza_match_question(None, _SM_STANZAS, "grc_to_tr", "ru", random)

    def test_builds_radio_with_options(self, gu_form):
        import random
        radio, stanza = gu_form.stanza_match_question(
            _SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", "ru", random
        )
        assert stanza == _SM_STANZAS[0]
        assert len(radio.options) > 1

    def test_label_uses_lang(self, gu_form):
        import random
        radio, _ = gu_form.stanza_match_question(
            _SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", "en", random
        )
        assert "Choose the translation" in radio.label

    def test_initial_value_set_when_in_options(self, gu_form):
        import random
        radio, _ = gu_form.stanza_match_question(
            _SM_STANZAS[0], _SM_STANZAS, "tr_to_grc", "ru", random,
            initial_value="Ἄνδρα μοι ἔννεπε, Μοῦσα, πολύτροπον, ὃς μάλα πολλὰ",
        )
        assert radio.value == "Ἄνδρα μοι ἔννεπε, Μοῦσα, πολύτροπον, ὃς μάλα πολλὰ"

    def test_valid_translators_threaded_through(self, gu_form):
        import random
        for _ in range(20):
            radio, _ = gu_form.stanza_match_question(
                _SM_STANZAS[0], _SM_STANZAS, "grc_to_tr", "ru", random,
                valid_translators=["подстрочник"],
            )
            assert all(o.endswith("— подстрочник") for o in radio.options)


class TestStanzaMatchWidgets:
    def test_no_cv_placeholder_radio(self, gu_form):
        radio, _, _ = gu_form.stanza_match_widgets(cv=None, remaining=[], stanzas=_SM_STANZAS)
        assert radio.options == [""]

    def test_cv_gives_multiple_options(self, gu_form):
        radio, _, _ = gu_form.stanza_match_widgets(cv=_SM_STANZAS[0], remaining=_SM_STANZAS[1:], stanzas=_SM_STANZAS)
        assert len(radio.options) > 1

    def test_valid_translators_threaded_through(self, gu_form):
        radio, _, _ = gu_form.stanza_match_widgets(
            cv=_SM_STANZAS[0], remaining=_SM_STANZAS[1:], stanzas=_SM_STANZAS,
            valid_translators=["подстрочник"],
        )
        assert all(o.endswith("— подстрочник") for o in radio.options)

    def test_done_flag_changes_next_label(self, gu_form):
        _, next_btn, _ = gu_form.stanza_match_widgets(cv=None, remaining=[], stanzas=_SM_STANZAS)
        assert "снова" in next_btn.label

    def test_restore_entry_sets_radio_value(self, gu_form):
        radio, _, _ = gu_form.stanza_match_widgets(
            cv=_SM_STANZAS[0], remaining=_SM_STANZAS[1:], stanzas=_SM_STANZAS,
            restore_entry={"answer": "Мужа мне назови, Муза, многообразного, который очень много — подстрочник"},
        )
        assert radio.value == "Мужа мне назови, Муза, многообразного, который очень много — подстрочник"


class TestStanzaMatchForm:
    def _state(self, cv=None, rem=None, sc=None, rst=None, hist=None, fut=None):
        return _form_state(cv, rem, sc, rst, hist, fut)

    def _call(self, gu, state, radio=None, next_v=None, prev_v=None, stanzas=None,
              direction="grc_to_tr", lang="ru", renew_btn=None, valid_translators=None):
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, _, fut_g, fut_s = state
        return gu.stanza_match_form(
            cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
            hist_g, hist_s, fut_g, fut_s,
            radio or _FakeRadio(), _FakeBtn(next_v), _FakeBtn(prev_v),
            stanzas=stanzas or _SM_STANZAS,
            direction=direction,
            lang=lang,
            renew_btn=renew_btn,
            valid_translators=valid_translators,
        )

    def test_uninit_initializes(self, gu_form):
        state = self._state(rem=None)
        cv_b = state[2]; rem_b = state[5]
        result = self._call(gu_form, state)
        assert result == "*...*"
        assert cv_b[0] is not None
        assert rem_b[0] is not None

    def test_renew_btn_included_in_nav_row(self, gu_form):
        s = _SM_STANZAS[0]
        state = self._state(cv=s, rem=_SM_STANZAS[1:])
        renew = _FakeBtn(label="renew")
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1, renew_btn=renew)
        assert renew in result[-1]

    def test_no_renew_btn_omitted_from_nav_row(self, gu_form):
        s = _SM_STANZAS[0]
        state = self._state(cv=s, rem=_SM_STANZAS[1:])
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1)
        assert len(result[-1]) == 2

    def test_grc_to_tr_correct_answer_scores(self, gu_form):
        s = _SM_STANZAS[0]
        state = self._state(cv=s, rem=_SM_STANZAS[1:])
        sc_b = state[8]
        correct = gu_form._stanza_match_prompt_and_correct(s, "grc_to_tr")[1]
        result = self._call(gu_form, state, radio=_FakeRadio(value=correct),
                            next_v=1, direction="grc_to_tr")
        assert result == "*...*"
        assert sc_b[0]["total"] == 1
        assert sc_b[0]["correct"] == 1

    def test_grc_to_tr_wrong_answer_scores_incorrect(self, gu_form):
        s = _SM_STANZAS[0]
        state = self._state(cv=s, rem=_SM_STANZAS[1:])
        sc_b = state[8]
        result = self._call(gu_form, state, radio=_FakeRadio(value="not the answer"),
                            next_v=1, direction="grc_to_tr")
        assert result == "*...*"
        assert sc_b[0]["total"] == 1
        assert sc_b[0]["correct"] == 0

    def test_tr_to_grc_correct_answer_scores(self, gu_form):
        s = _SM_STANZAS[0]
        state = self._state(cv=s, rem=_SM_STANZAS[1:])
        sc_b = state[8]
        correct = gu_form._stanza_match_prompt_and_correct(s, "tr_to_grc")[1]
        result = self._call(gu_form, state, radio=_FakeRadio(value=correct),
                            next_v=1, direction="tr_to_grc")
        assert result == "*...*"
        assert sc_b[0]["correct"] == 1

    def test_next_without_answer_rerenders(self, gu_form):
        s = _SM_STANZAS[0]
        state = self._state(cv=s, rem=_SM_STANZAS[1:])
        sc_b = state[8]
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1)
        assert result != "*...*"
        assert sc_b[0]["total"] == 0

    def test_done_shows_callout(self, gu_form):
        state = self._state(cv=None, rem=[], sc={"correct": 2, "total": 4})
        with pytest.raises(StopIteration) as exc_info:
            self._call(gu_form, state)
        assert "callout" in str(exc_info.value.args[0])

    def test_next_restart_after_done_resets_score(self, gu_form):
        state = self._state(cv=None, rem=[], sc={"correct": 2, "total": 4})
        cv_b = state[2]; sc_b = state[8]
        result = self._call(gu_form, state, next_v=1)
        assert result == "*...*"
        assert cv_b[0] is not None
        assert sc_b[0]["total"] == 0

    def test_prev_goes_back(self, gu_form):
        past = {"word": _SM_STANZAS[1], "answer": "x", "correct": False}
        state = self._state(cv=_SM_STANZAS[0], rem=_SM_STANZAS[2:],
                            sc={"correct": 0, "total": 1}, hist=[past])
        cv_b = state[2]; sc_b = state[8]; hist_b = state[13]
        result = self._call(gu_form, state, prev_v=1)
        assert result == "*...*"
        assert cv_b[0] == _SM_STANZAS[1]
        assert sc_b[0]["total"] == 0
        assert hist_b[0] == []

    def test_wrong_answer_reveals_correct_text(self, gu_form):
        s = _SM_STANZAS[0]
        state = self._state(cv=s, rem=_SM_STANZAS[1:])
        correct = gu_form._stanza_match_prompt_and_correct(s, "grc_to_tr")[1]
        result = self._call(gu_form, state, radio=_FakeRadio(value="not the answer"))
        text = str(result)
        assert "✗" in text
        assert "Неверно" in text
        assert correct in text

    def test_correct_answer_shows_check_without_reveal_duplication(self, gu_form):
        s = _SM_STANZAS[0]
        state = self._state(cv=s, rem=_SM_STANZAS[1:])
        correct = gu_form._stanza_match_prompt_and_correct(s, "grc_to_tr")[1]
        result = self._call(gu_form, state, radio=_FakeRadio(value=correct))
        text = str(result)
        assert "✓" in text
        assert "Верно" in text
        assert "✗" not in text

    def test_default_lang_is_russian(self, gu_form):
        state = self._state(cv=_SM_STANZAS[0], rem=_SM_STANZAS[1:])
        result = self._call(gu_form, state, radio=_FakeRadio(value=None))
        assert "правильно" in str(result)

    def test_valid_translators_threaded_through_grading(self, gu_form):
        # Widgets and grading must agree on the same valid_translators-filtered
        # pick -- same setup as test_valid_translators_restricts_pick.
        s = _SM_STANZAS[0]
        correct = "Мужа мне назови, Муза, многообразного, который очень много — подстрочник"
        state = self._state(cv=s, rem=_SM_STANZAS[1:])
        sc_b = state[8]
        self._call(
            gu_form, state, radio=_FakeRadio(value=correct), next_v=1,
            valid_translators=["подстрочник"],
        )
        assert sc_b[0]["correct"] == 1

    _FWD_CORRECT = "Мужа мне назови, Муза, многообразного, который очень много — подстрочник"

    def _next_forward(self, gu_form, answer, *, restore=None, ahead=None):
        """Press Next on the first stanza while a saved future entry exists (i.e. after Prev)."""
        import types
        ahead = ahead or {"word": _SM_STANZAS[1], "answer": "saved", "correct": True}
        state = self._state(cv=_SM_STANZAS[0], rem=_SM_STANZAS[2:], fut=[ahead], rst=restore)
        result = self._call(gu_form, state, radio=_FakeRadio(value=answer), next_v=1,
                            valid_translators=["подстрочник"])
        return types.SimpleNamespace(result=result, cv=state[0], score=state[6], restore=state[9],
                                     history=state[11], future=state[14])

    def test_next_forward_grades_the_stanza_it_leaves(self, gu_form):
        out = self._next_forward(gu_form, self._FWD_CORRECT)
        assert out.result == "*...*"
        assert out.history() == [{"word": _SM_STANZAS[0], "answer": self._FWD_CORRECT, "correct": True}]
        assert out.score() == {"correct": 1, "total": 1}
        assert out.cv() == _SM_STANZAS[1]
        assert out.future() == []  # the future entry is consumed
        assert out.restore() == {"answer": "saved", "correct": True}  # restored for the stanza moved to

    def test_next_forward_grades_the_restored_answer_when_nothing_is_reselected(self, gu_form):
        out = self._next_forward(gu_form, None, restore={"answer": self._FWD_CORRECT, "correct": True})
        assert out.history() == [{"word": _SM_STANZAS[0], "answer": self._FWD_CORRECT, "correct": True}]
        assert out.score() == {"correct": 1, "total": 1}

    def test_next_forward_without_any_answer_logs_the_stanza_as_wrong(self, gu_form):
        out = self._next_forward(gu_form, None)
        assert out.history() == [{"word": _SM_STANZAS[0], "answer": None, "correct": False}]
        assert out.score() == {"correct": 0, "total": 1}

    def test_next_forward_onto_an_unanswered_stanza_clears_the_restore(self, gu_form):
        unanswered = {"word": _SM_STANZAS[1], "answer": None, "correct": None}
        out = self._next_forward(gu_form, self._FWD_CORRECT, ahead=unanswered,
                                 restore={"answer": "stale", "correct": False})
        assert out.restore() is None


# ────────────────────────────────────────── translation-presence quiz (5b) ──

_TP_VOCAB = [
    {"lemma": "ἀνήρ", "form": "Ἄνδρα", "meaning": "мужа"},
    {"lemma": "μοῦσα", "form": "Μοῦσα", "meaning": "муза"},
    {"lemma": "Τροία", "form": "Τροίης", "meaning": "Трои"},
]


class TestReadPresenceRows:
    def test_missing_file_returns_empty(self, gu_form, tmp_path):
        assert gu_form._read_presence_rows(tmp_path / "nope.tsv") == []

    def test_reads_rows_skipping_header(self, gu_form, tmp_path):
        p = tmp_path / "p.tsv"
        p.write_text(
            "lemma\tform\tstanza_ref\ttranslator\treflected\n"
            "ἀνήρ\tἌνδρα\tI.1-2\tЖуковский\tyes\n",
            encoding="utf-8",
        )
        rows = gu_form._read_presence_rows(p)
        assert rows == [["ἀνήρ", "Ἄνδρα", "I.1-2", "Жуковский", "yes"]]

    def test_preserves_comment_prefix(self, gu_form, tmp_path):
        p = tmp_path / "p.tsv"
        p.write_text(
            "lemma\tform\tstanza_ref\ttranslator\treflected\n"
            "#ἀνήρ\tἌνδρα\tI.1-2\tЖуковский\tyes\n",
            encoding="utf-8",
        )
        rows = gu_form._read_presence_rows(p)
        assert rows[0][0] == "#ἀνήρ"

    def test_skips_blank_lines(self, gu_form, tmp_path):
        p = tmp_path / "p.tsv"
        p.write_text(
            "lemma\tform\tstanza_ref\ttranslator\treflected\n"
            "\nἀνήρ\tἌνδρα\tI.1-2\tЖуковский\tyes\n",
            encoding="utf-8",
        )
        assert len(gu_form._read_presence_rows(p)) == 1

    def test_skips_rows_with_fewer_than_five_columns(self, gu_form, tmp_path):
        p = tmp_path / "p.tsv"
        p.write_text(
            "lemma\tform\tstanza_ref\ttranslator\treflected\n"
            "ἀνήρ\tἌνδρα\tI.1-2\n"
            "μοῦσα\tΜοῦσα\tI.1-2\tЖуковский\tyes\n",
            encoding="utf-8",
        )
        assert gu_form._read_presence_rows(p) == [["μοῦσα", "Μοῦσα", "I.1-2", "Жуковский", "yes"]]


class TestStanzaWordOccurrences:
    def test_single_occurrence(self, gu_form):
        assert gu_form.stanza_word_occurrences("Τροίης", _SM_STANZAS) == ["I.3-4"]

    def test_multiple_occurrences_across_stanzas(self, gu_form):
        # "πολλὰ" appears in both I.1-2 ("...μάλα πολλὰ") and I.7-9 ("πολλὰ δ'...")
        refs = gu_form.stanza_word_occurrences("πολλὰ", _SM_STANZAS)
        assert set(refs) == {"I.1-2", "I.7-9"}

    def test_no_occurrence_returns_empty(self, gu_form):
        assert gu_form.stanza_word_occurrences("οὐδέποτε", _SM_STANZAS) == []

    def test_prefix_of_longer_word_is_not_a_false_match(self, gu_form):
        # Guards the exact bug found live: "θεά" must not spuriously match
        # inside a longer word like "θεάων" that merely starts with it.
        s = [{"ref": "X.1", "lines": ["δῖα θεάων"]}]
        assert gu_form.stanza_word_occurrences("θεά", s) == []

    def test_trailing_punctuation_does_not_block_match(self, gu_form):
        # "πλάγχθη," in the source has a trailing comma; the bare form still matches.
        assert gu_form.stanza_word_occurrences("πλάγχθη", _SM_STANZAS) == ["I.3-4"]


class TestSyncTranslationPresenceTsv:
    def test_first_run_emits_all_starter_rows(self, gu_form, tmp_path):
        p = tmp_path / "presence.tsv"
        gu_form.sync_translation_presence_tsv(_TP_VOCAB, ["Жуковский", "Вересаев"], _SM_STANZAS, p)
        rows = gu_form._read_presence_rows(p)
        # each of the 3 words occurs in exactly 1 stanza x 2 translators = 6 rows
        assert len(rows) == 6
        assert all(r[4] == "" for r in rows)  # unreviewed starter default
        assert ("ἀνήρ", "Ἄνδρα", "I.1-2", "Жуковский") in {(r[0], r[1], r[2], r[3]) for r in rows}
        assert ("ἀνήρ", "Ἄνδρα", "I.1-2", "Вересаев") in {(r[0], r[1], r[2], r[3]) for r in rows}

    def test_word_occurring_in_two_stanzas_gets_a_row_per_stanza(self, gu_form, tmp_path):
        p = tmp_path / "presence.tsv"
        vocab = [{"lemma": "πολύς", "form": "πολλὰ", "meaning": "много"}]
        gu_form.sync_translation_presence_tsv(vocab, ["Жуковский"], _SM_STANZAS, p)
        rows = gu_form._read_presence_rows(p)
        assert {r[2] for r in rows} == {"I.1-2", "I.7-9"}
        assert len(rows) == 2

    def test_rerun_preserves_edited_row_byte_identical(self, gu_form, tmp_path):
        p = tmp_path / "presence.tsv"
        gu_form.sync_translation_presence_tsv(_TP_VOCAB, ["Жуковский"], _SM_STANZAS, p)

        # simulate the teacher editing one row's reflected value from "" to "yes"
        unedited_line = "ἀνήρ\tἌνδρα\tI.1-2\tЖуковский\t"
        edited_line = "ἀνήρ\tἌνδρα\tI.1-2\tЖуковский\tyes"
        text = p.read_text(encoding="utf-8")
        assert unedited_line in text  # sanity: the starter row looks as expected
        text = text.replace(unedited_line, edited_line)
        p.write_text(text, encoding="utf-8")

        gu_form.sync_translation_presence_tsv(_TP_VOCAB, ["Жуковский"], _SM_STANZAS, p)

        after_lines = p.read_text(encoding="utf-8").splitlines()
        assert edited_line in after_lines

    def test_new_vocab_word_adds_row_per_translator_existing_untouched(self, gu_form, tmp_path):
        p = tmp_path / "presence.tsv"
        gu_form.sync_translation_presence_tsv(_TP_VOCAB[:1], ["Жуковский", "Вересаев"], _SM_STANZAS, p)
        before = set(map(tuple, gu_form._read_presence_rows(p)))

        gu_form.sync_translation_presence_tsv(_TP_VOCAB, ["Жуковский", "Вересаев"], _SM_STANZAS, p)
        after = gu_form._read_presence_rows(p)

        assert before <= set(map(tuple, after))  # nothing already there was touched
        new_lemmas = {r[0] for r in after} - {"ἀνήρ"}
        assert new_lemmas == {"μοῦσα", "Τροία"}
        # exactly one new row per (new word, translator)
        assert sum(1 for r in after if r[0] == "μοῦσα") == 2

    def test_removed_word_is_commented_not_dropped(self, gu_form, tmp_path):
        p = tmp_path / "presence.tsv"
        gu_form.sync_translation_presence_tsv(_TP_VOCAB, ["Жуковский"], _SM_STANZAS, p)

        gu_form.sync_translation_presence_tsv(_TP_VOCAB[1:], ["Жуковский"], _SM_STANZAS, p)  # ἀνήρ removed

        rows = gu_form._read_presence_rows(p)
        assert any(r[0] == "#ἀνήρ" for r in rows)
        assert not any(r[0] == "ἀνήρ" for r in rows)  # not present un-commented

    def test_readded_word_is_uncommented(self, gu_form, tmp_path):
        p = tmp_path / "presence.tsv"
        gu_form.sync_translation_presence_tsv(_TP_VOCAB, ["Жуковский"], _SM_STANZAS, p)
        gu_form.sync_translation_presence_tsv(_TP_VOCAB[1:], ["Жуковский"], _SM_STANZAS, p)  # remove ἀνήρ

        gu_form.sync_translation_presence_tsv(_TP_VOCAB, ["Жуковский"], _SM_STANZAS, p)  # re-add it

        rows = gu_form._read_presence_rows(p)
        assert any(r[0] == "ἀνήρ" for r in rows)
        assert not any(r[0] == "#ἀνήρ" for r in rows)


class TestReadTranslationPresenceTsv:
    def test_drops_commented_rows(self, gu_form, tmp_path):
        p = tmp_path / "presence.tsv"
        p.write_text(
            "lemma\tform\tstanza_ref\ttranslator\treflected\n"
            "ἀνήρ\tἌνδρα\tI.1-2\tЖуковский\tyes\n"
            "#μοῦσα\tΜοῦσα\tI.1-2\tЖуковский\tno\n",
            encoding="utf-8",
        )
        rows = gu_form.read_translation_presence_tsv(p)
        assert len(rows) == 1
        assert rows[0] == {"lemma": "ἀνήρ", "form": "Ἄνδρα", "stanza_ref": "I.1-2",
                            "translator": "Жуковский", "reflected": "yes"}

    def test_missing_file_returns_empty(self, gu_form, tmp_path):
        assert gu_form.read_translation_presence_tsv(tmp_path / "nope.tsv") == []


class TestBuildTranslationPresenceItems:
    _ROWS = [
        {"lemma": "ἀνήρ", "form": "Ἄνδρα", "stanza_ref": "I.1-2",
         "translator": "Жуковский", "reflected": "yes"},
        {"lemma": "μοῦσα", "form": "Μοῦσα", "stanza_ref": "I.1-2",
         "translator": "Вересаев", "reflected": "no"},
    ]

    def test_resolves_passage_and_meaning(self, gu_form):
        items = gu_form.build_translation_presence_items(self._ROWS, _TP_VOCAB, _SM_STANZAS)
        assert len(items) == 2
        first = next(i for i in items if i["lemma"] == "ἀνήρ")
        assert first["meaning"] == "мужа"
        assert first["passage"] == _SM_STANZAS[0]["translations"]["Жуковский"]
        assert first["reflected"] == "yes"

    def test_word_not_in_vocab_skipped_no_crash(self, gu_form):
        rows = [{"lemma": "ἄγνωστος", "form": "ἄγνωστον", "stanza_ref": "I.1-2",
                 "translator": "Жуковский", "reflected": "yes"}]
        assert gu_form.build_translation_presence_items(rows, _TP_VOCAB, _SM_STANZAS) == []

    def test_unresolvable_stanza_ref_skipped(self, gu_form):
        rows = [{"lemma": "ἀνήρ", "form": "Ἄνδρα", "stanza_ref": "NOPE",
                 "translator": "Жуковский", "reflected": "yes"}]
        assert gu_form.build_translation_presence_items(rows, _TP_VOCAB, _SM_STANZAS) == []

    def test_translator_with_no_text_for_stanza_skipped(self, gu_form):
        rows = [{"lemma": "ἀνήρ", "form": "Ἄνδρα", "stanza_ref": "I.1-2",
                 "translator": "NoSuchTranslator", "reflected": "yes"}]
        assert gu_form.build_translation_presence_items(rows, _TP_VOCAB, _SM_STANZAS) == []

    def test_empty_rows_returns_empty(self, gu_form):
        assert gu_form.build_translation_presence_items([], _TP_VOCAB, _SM_STANZAS) == []

    def test_unreviewed_row_skipped_not_graded_as_no(self, gu_form):
        # A blank/unreviewed reflected value has no confident ground truth -- must
        # be excluded, not silently treated as "no" by the quiz's grading branch.
        rows = [{"lemma": "ἀνήρ", "form": "Ἄνδρα", "stanza_ref": "I.1-2",
                 "translator": "Жуковский", "reflected": ""}]
        assert gu_form.build_translation_presence_items(rows, _TP_VOCAB, _SM_STANZAS) == []

    def test_valid_translators_filters_items(self, gu_form):
        items = gu_form.build_translation_presence_items(
            self._ROWS, _TP_VOCAB, _SM_STANZAS, valid_translators=["Жуковский"]
        )
        assert len(items) == 1
        assert items[0]["translator"] == "Жуковский"

    def test_valid_translators_none_means_all_allowed(self, gu_form):
        items = gu_form.build_translation_presence_items(
            self._ROWS, _TP_VOCAB, _SM_STANZAS, valid_translators=None
        )
        assert len(items) == 2

    def test_valid_translators_excluding_all_returns_empty(self, gu_form):
        items = gu_form.build_translation_presence_items(
            self._ROWS, _TP_VOCAB, _SM_STANZAS, valid_translators=["NoSuchTranslator"]
        )
        assert items == []


class TestSampleSessionItems:
    def test_caps_to_n(self, gu_form):
        result = gu_form.sample_session_items(list(range(166)), 10)
        assert len(result) == 10

    def test_result_is_a_subset_of_input(self, gu_form):
        items = list(range(166))
        result = gu_form.sample_session_items(items, 10)
        assert set(result) <= set(items)

    def test_fewer_items_than_n_returns_all_unchanged(self, gu_form):
        items = list(range(4))
        assert sorted(gu_form.sample_session_items(items, 10)) == items

    def test_default_n_is_10(self, gu_form):
        assert len(gu_form.sample_session_items(list(range(166)))) == 10

    def test_empty_items_returns_empty(self, gu_form):
        assert gu_form.sample_session_items([], 10) == []

    def test_randomizes_across_calls(self, gu_form):
        items = list(range(166))
        samples = {tuple(sorted(gu_form.sample_session_items(items, 10))) for _ in range(10)}
        assert len(samples) > 1


class TestBalancePresenceItems:
    @staticmethod
    def _items(n_yes, n_no):
        yes = [{"lemma": f"yes{i}", "reflected": "yes"} for i in range(n_yes)]
        no = [{"lemma": f"no{i}", "reflected": "no"} for i in range(n_no)]
        return yes + no

    def test_default_caps_session_to_10_items(self, gu_form):
        # Real 2026_06_01 shape: 10 "no" rows against 166 "yes".
        items = self._items(n_yes=166, n_no=10)
        result = gu_form.balance_presence_items(items)
        assert sum(1 for it in result if it["reflected"] == "no") == 5
        assert sum(1 for it in result if it["reflected"] == "yes") == 5

    def test_n_none_keeps_every_no_item_uncapped(self, gu_form):
        items = self._items(n_yes=166, n_no=10)
        result = gu_form.balance_presence_items(items, n=None)
        result_nos = {it["lemma"] for it in result if it["reflected"] == "no"}
        assert result_nos == {f"no{i}" for i in range(10)}
        assert sum(1 for it in result if it["reflected"] == "yes") == 10

    def test_custom_ratio_uncapped(self, gu_form):
        # no_ratio=0.25, n=None -> "no" is a quarter of the (uncapped) session: 3 no + 9 yes.
        items = self._items(n_yes=166, n_no=3)
        result = gu_form.balance_presence_items(items, no_ratio=0.25, n=None)
        assert sum(1 for it in result if it["reflected"] == "no") == 3
        assert sum(1 for it in result if it["reflected"] == "yes") == 9

    def test_custom_n(self, gu_form):
        items = self._items(n_yes=166, n_no=10)
        result = gu_form.balance_presence_items(items, n=4)
        assert sum(1 for it in result if it["reflected"] == "no") == 2
        assert sum(1 for it in result if it["reflected"] == "yes") == 2

    def test_fewer_yes_than_target_uses_all_available(self, gu_form):
        items = self._items(n_yes=2, n_no=5)
        result = gu_form.balance_presence_items(items, n=None)
        assert sum(1 for it in result if it["reflected"] == "no") == 5
        assert sum(1 for it in result if it["reflected"] == "yes") == 2

    def test_sampled_yes_items_are_a_subset_of_input(self, gu_form):
        items = self._items(n_yes=166, n_no=10)
        result = gu_form.balance_presence_items(items)
        result_yes = {it["lemma"] for it in result if it["reflected"] == "yes"}
        all_yes = {it["lemma"] for it in items if it["reflected"] == "yes"}
        assert result_yes <= all_yes

    def test_sampled_no_items_are_a_subset_when_capped(self, gu_form):
        items = self._items(n_yes=166, n_no=20)
        result = gu_form.balance_presence_items(items)
        result_no = {it["lemma"] for it in result if it["reflected"] == "no"}
        all_no = {it["lemma"] for it in items if it["reflected"] == "no"}
        assert result_no <= all_no

    def test_no_no_items_returns_unchanged(self, gu_form):
        items = self._items(n_yes=5, n_no=0)
        assert gu_form.balance_presence_items(items) == items

    def test_no_yes_items_returns_unchanged(self, gu_form):
        items = self._items(n_yes=0, n_no=5)
        assert gu_form.balance_presence_items(items) == items

    def test_empty_items_returns_unchanged(self, gu_form):
        assert gu_form.balance_presence_items([]) == []

    def test_unreviewed_rows_are_dropped(self, gu_form):
        # reflected="" (not yet reviewed in the TSV) must land in neither
        # class, not be miscounted as "yes".
        items = self._items(n_yes=166, n_no=10)
        items += [{"lemma": f"unreviewed{i}", "reflected": ""} for i in range(5)]
        result = gu_form.balance_presence_items(items)
        assert all(it["reflected"] in ("yes", "no") for it in result)
        assert len(result) == 10


class TestTranslationPresenceQuestion:
    _ITEM = {"lemma": "ἀνήρ", "form": "Ἄνδρα", "meaning": "мужа", "translator": "Жуковский",
              "passage": "Муза, скажи…", "source": "Ἄνδρα μοι ἔννεπε…", "reflected": "yes"}

    def test_item_none_calls_stop(self, gu_form):
        with pytest.raises(StopIteration):
            gu_form.translation_presence_question(None, "ru")

    def test_builds_da_net_radio(self, gu_form):
        radio, item = gu_form.translation_presence_question(self._ITEM, "ru")
        assert item == self._ITEM
        assert set(radio.options) == {"да", "нет"}

    def test_lang_en_changes_options_and_label(self, gu_form):
        radio, _ = gu_form.translation_presence_question(self._ITEM, "en")
        assert set(radio.options) == {"yes", "no"}
        assert "Is the word reflected" in radio.label

    def test_label_is_just_the_prompt_not_the_passage(self, gu_form):
        # Passage/word rendering moved to _presence_passage_md, kept separate from
        # the radio's own label -- so toggling source/translation never needs to
        # rebuild (and so never risks resetting) this radio's selection.
        radio, _ = gu_form.translation_presence_question(self._ITEM, "ru")
        assert "Ἄνδρα" not in radio.label
        assert "Муза, скажи…" not in radio.label

    def test_initial_value_set_when_valid(self, gu_form):
        radio, _ = gu_form.translation_presence_question(self._ITEM, "ru", initial_value="да")
        assert radio.value == "да"


class TestPresencePassageMd:
    _ITEM = TestTranslationPresenceQuestion._ITEM

    def test_translation_view_shows_passage_and_translator(self, gu_form):
        md = gu_form._presence_passage_md(self._ITEM, False, "ru")
        assert "Муза, скажи…" in md
        assert "Жуковский" in md
        assert "Ἄνδρα" in md
        assert self._ITEM["source"] not in md

    def test_source_view_shows_source_and_generic_label(self, gu_form):
        md = gu_form._presence_passage_md(self._ITEM, True, "ru")
        assert "Ἄνδρα μοι ἔννεπε…" in md
        assert "оригинал" in md
        assert "Ἄνδρα" in md  # the word itself still shown
        assert self._ITEM["passage"] not in md
        assert "Жуковский" not in md

    def test_word_always_shown_in_both_views(self, gu_form):
        for show_source in (False, True):
            md = gu_form._presence_passage_md(self._ITEM, show_source, "ru")
            assert "**Ἄνδρα**" in md

    def test_lang_en_source_label(self, gu_form):
        md = gu_form._presence_passage_md(self._ITEM, True, "en")
        assert "original" in md


class TestTranslationPresenceWidgets:
    _ITEM = TestTranslationPresenceQuestion._ITEM

    def test_no_cv_placeholder_radio(self, gu_form):
        radio, _, _, _ = gu_form.translation_presence_widgets(cv=None, remaining=[], items=[self._ITEM])
        assert radio.options == [""]

    def test_cv_gives_da_net_options(self, gu_form):
        radio, _, _, _ = gu_form.translation_presence_widgets(cv=self._ITEM, remaining=[], items=[self._ITEM])
        assert set(radio.options) == {"да", "нет"}

    def test_done_flag_changes_next_label(self, gu_form):
        _, next_btn, _, _ = gu_form.translation_presence_widgets(cv=None, remaining=[], items=[self._ITEM])
        assert "снова" in next_btn.label

    def test_source_switch_starts_showing_translation(self, gu_form):
        # "On every step begin from translation" -- a fresh switch each round,
        # defaulting to False (translation view), never the original.
        _, _, _, source_switch = gu_form.translation_presence_widgets(cv=self._ITEM, remaining=[], items=[self._ITEM])
        assert source_switch.value is False


class TestTranslationPresenceForm:
    _ITEMS = [
        {"lemma": "ἀνήρ", "form": "Ἄνδρα", "meaning": "мужа", "translator": "Жуковский",
         "passage": "Муза, скажи…", "source": "Ἄνδρα μοι ἔννεπε…", "reflected": "yes"},
        {"lemma": "μοῦσα", "form": "Μοῦσα", "meaning": "муза", "translator": "Вересаев",
         "passage": "Долго скитался…", "source": "…μοῦσα…", "reflected": "no"},
    ]

    def _state(self, cv=None, rem=None, sc=None, rst=None, hist=None, fut=None):
        return _form_state(cv, rem, sc, rst, hist, fut)

    def _call(self, gu, state, radio=None, next_v=None, prev_v=None, items=None, lang="ru",
              show_source=False, renew_btn=None):
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, _, fut_g, fut_s = state
        return gu.translation_presence_form(
            cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
            hist_g, hist_s, fut_g, fut_s,
            radio or _FakeRadio(), _FakeBtn(next_v), _FakeBtn(prev_v), _FakeBtn(show_source),
            items=self._ITEMS if items is None else items,
            lang=lang,
            renew_btn=renew_btn,
        )

    def test_uninit_initializes(self, gu_form):
        state = self._state(rem=None)
        cv_b = state[2]; rem_b = state[5]
        result = self._call(gu_form, state)
        assert result == "*...*"
        assert cv_b[0] is not None
        assert rem_b[0] is not None

    def test_renew_btn_included_in_nav_row(self, gu_form):
        item = self._ITEMS[0]
        state = self._state(cv=item, rem=self._ITEMS[1:])
        renew = _FakeBtn(label="renew")
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1, renew_btn=renew)
        assert renew in result[-1]

    def test_no_renew_btn_omitted_from_nav_row(self, gu_form):
        item = self._ITEMS[0]
        state = self._state(cv=item, rem=self._ITEMS[1:])
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1)
        assert len(result[-1]) == 2

    def test_da_correct_for_reflected_yes(self, gu_form):
        item = self._ITEMS[0]  # reflected == "yes"
        state = self._state(cv=item, rem=self._ITEMS[1:])
        result = self._call(gu_form, state, radio=_FakeRadio(value="да"))
        assert "✓" in str(result)
        assert "✗" not in str(result)
        assert "Верно" in str(result)

    def test_net_correct_for_reflected_no(self, gu_form):
        item = self._ITEMS[1]  # reflected == "no"
        state = self._state(cv=item, rem=[])
        result = self._call(gu_form, state, radio=_FakeRadio(value="нет"))
        assert "✓" in str(result)
        assert "✗" not in str(result)
        assert "Верно" in str(result)

    def test_da_wrong_for_reflected_no(self, gu_form):
        item = self._ITEMS[1]  # reflected == "no"
        state = self._state(cv=item, rem=[])
        result = self._call(gu_form, state, radio=_FakeRadio(value="да"))
        assert "✗" in str(result)
        assert "✓" not in str(result)
        assert "Неверно" in str(result)
        assert "Правильно" in str(result)
        assert "нет" in str(result)  # the revealed correct да/нет value

    def test_source_switch_off_shows_translation(self, gu_form):
        item = self._ITEMS[0]
        state = self._state(cv=item, rem=self._ITEMS[1:])
        result = self._call(gu_form, state, show_source=False)
        text = str(result)
        assert item["passage"] in text
        assert item["source"] not in text

    def test_source_switch_on_shows_original(self, gu_form):
        item = self._ITEMS[0]
        state = self._state(cv=item, rem=self._ITEMS[1:])
        result = self._call(gu_form, state, show_source=True)
        text = str(result)
        assert item["source"] in text
        assert item["passage"] not in text

    def test_toggling_source_switch_does_not_touch_score_or_selection(self, gu_form):
        # Peeking at the source is a pure display toggle -- must not advance the
        # quiz, change the score, or require re-answering.
        item = self._ITEMS[0]
        state = self._state(cv=item, rem=self._ITEMS[1:], sc={"correct": 0, "total": 0})
        sc_b = state[8]
        result = self._call(gu_form, state, radio=_FakeRadio(value="да"), show_source=True)
        assert "✓" in str(result)
        assert sc_b[0] == {"correct": 0, "total": 0}

    def test_next_with_answer_advances_and_scores(self, gu_form):
        item = self._ITEMS[0]
        state = self._state(cv=item, rem=self._ITEMS[1:])
        sc_b = state[8]
        result = self._call(gu_form, state, radio=_FakeRadio(value="да"), next_v=1)
        assert result == "*...*"
        assert sc_b[0] == {"correct": 1, "total": 1}

    def test_next_without_answer_rerenders(self, gu_form):
        item = self._ITEMS[0]
        state = self._state(cv=item, rem=self._ITEMS[1:])
        sc_b = state[8]
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1)
        assert result != "*...*"
        assert sc_b[0]["total"] == 0

    def test_prev_goes_back(self, gu_form):
        past = {"word": self._ITEMS[1], "answer": "нет", "correct": True}
        state = self._state(cv=self._ITEMS[0], rem=[],
                            sc={"correct": 1, "total": 1}, hist=[past])
        cv_b = state[2]; sc_b = state[8]
        result = self._call(gu_form, state, prev_v=1)
        assert result == "*...*"
        assert cv_b[0] == self._ITEMS[1]
        assert sc_b[0]["total"] == 0

    def test_done_shows_callout(self, gu_form):
        state = self._state(cv=None, rem=[], sc={"correct": 1, "total": 2})
        with pytest.raises(StopIteration) as exc_info:
            self._call(gu_form, state)
        assert "callout" in str(exc_info.value.args[0])

    def test_empty_items_shows_no_reviewed_pairs_message(self, gu_form):
        state = self._state(rem=None)
        result = self._call(gu_form, state, items=[])
        assert "Пока нет проверенных пар" in str(result)

    def test_empty_items_lang_en_message(self, gu_form):
        state = self._state(rem=None)
        result = self._call(gu_form, state, items=[], lang="en")
        assert "No reviewed word" in str(result)

    def test_lang_en_uses_yes_no_progress(self, gu_form):
        state = self._state(cv=self._ITEMS[0], rem=self._ITEMS[1:])
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), lang="en")
        assert "correct" in str(result)

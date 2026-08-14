"""Tests for notebook_utils — greek_compare, strip_diacritics, GreekConfig, nav functions."""
import pytest

import json
import unicodedata
from unittest.mock import patch, MagicMock

import marimo as mo

import eee_project as _eee
from eee_project._grammar_fmt import fmt_ud_feats
from eee_project.notebook_utils import (
    greek_compare,
    strip_diacritics,
    poly_to_mono,
    parse_stanza_text,
    parse_stanza_translations,
    load_ga_config,
    MODERN_GREEK,
    ANCIENT_GREEK,
    GreekUtils,
    eee_topbar,
    parent_back_url,
    eee_hero,
    eee_card_list,
    eee_footer,
    _source_host_base,
    magnify_image,
    language_bridge,
    language_selector,
    save_language_selection,
    ConfigStore,
    build_grc_paradigm_table,
    build_modern_paradigm_table,
    build_grc_lexicon_tabs,
    make_paradigm_form,
    interactive_text,
    _InteractiveTextWidget,
    setup_ancient_greek,
    add_labels,
    filter_grc_quiz_words,
    grc_coverage_words,
    grc_lexicon_sources,
    norm_grc_surface,
    resolve_clicked_word,
    _norm_grc,
    _DIA_ESM_TMPL,
    _PARA_ESM,
    _ITEXT_ESM,
    _cors_safe_raw_url,
    _fetch_url_bytes,
    _fetch_url_bytes_async,
)
from conftest import StubMo as _StubMo, StubBackend as _StubBackend, StubMoLayout as _StubMoLayout


# ────────────────────────────────────────── poly_to_mono ──

class TestPolyToMono:
    """poly_to_mono: polytonic → monotonic — remap grave/circumflex to tonos, drop
    breathings + iota subscript, keep tonos + diaeresis."""

    def _eq(self, got, expected):
        assert got == unicodedata.normalize("NFC", expected)

    def test_smooth_breathing_dropped(self):
        self._eq(poly_to_mono("ἄνθρωπος"), "άνθρωπος")

    def test_rough_breathing_dropped(self):
        self._eq(poly_to_mono("ὕδωρ"), "ύδωρ")

    def test_grave_becomes_tonos(self):
        self._eq(poly_to_mono("καλὸς"), "καλός")

    def test_circumflex_becomes_tonos(self):
        self._eq(poly_to_mono("δῶρον"), "δώρον")

    def test_circumflex_on_diphthong(self):
        self._eq(poly_to_mono("οἶκος"), "οίκος")

    def test_iota_subscript_dropped(self):
        self._eq(poly_to_mono("χώρᾳ"), "χώρα")

    def test_tonos_preserved(self):
        self._eq(poly_to_mono("άνθρωπος"), "άνθρωπος")

    def test_diaeresis_and_tonos_preserved(self):
        self._eq(poly_to_mono("καΐκι"), "καΐκι")

    def test_idempotent(self):
        for w in ["ἄνθρωπος", "καλὸς", "χώρᾳ", "καΐκι"]:
            once = poly_to_mono(w)
            assert poly_to_mono(once) == once

    def test_final_sigma_unchanged(self):
        assert poly_to_mono("λόγος").endswith("ς")
        assert "σσ" in poly_to_mono("θάλασσα")

    def test_no_forbidden_marks_remain(self):
        out = unicodedata.normalize("NFD", poly_to_mono("ᾧ ἁγνῷ ἀνδρὶ"))
        for cp in ("̓", "̔", "ͅ", "̀", "͂"):
            assert cp not in out


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


# ──────────────────────────── build_modern_paradigm_table (el renderer) ──

class TestModernParadigmTable:
    """The el diachronic paradigm renderer (section-03); grc renderer untouched."""

    def _bt(self):
        from modern_greek_backend_eee import ModernGreekBackend
        return build_modern_paradigm_table(ModernGreekBackend())

    def test_noun_four_cases_no_dative(self):
        html = self._bt()({"lemma": "ἄνθρωπος", "form": "ἄνθρωπος", "pos": "noun"})
        # poly_to_mono(ἄνθρωπος) + Modern inflection → nom + gen present
        assert html and "άνθρωπος" in html and "ανθρώπου" in html
        assert "Дат." not in html                       # 4 cases (Nom/Gen/Acc/Voc), no dative

    def test_verb_voices_and_particle_in_form(self):
        html = self._bt()({"lemma": "γράφω", "form": "γράφω", "pos": "verb"})
        assert html and html.count("<table") == 2       # Active + Passive tables
        assert "θα γράψω" in html and "να γράψω" in html # θα/να particle IN the form cell (Gemini R3)
        assert "έγραφα" in html and "έγραψα" in html     # imperfect + aorist

    def test_hide_if_absent_returns_none_when_empty(self):
        class _Empty:
            def get_slot_templates(self, *a, **k):
                return []
        bt = build_modern_paradigm_table(_Empty())
        assert bt({"lemma": "x", "form": "x", "pos": "noun"}, hide_if_absent=True) is None

    def test_forms_are_html_escaped(self):
        class _Slot:
            tag, tag_type = "Nom|Sing|Masc", "ud"
            features = {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}

        class _Stub:
            def get_slot_templates(self, lang, pos, terms):
                return [_Slot()] if pos == "noun" else []

            def inflect(self, lemma, feats, pos, language=None, **k):
                return {"a<b"} if feats.get("Case") == "Nom" and feats.get("Number") == "Sing" else set()

        html = build_modern_paradigm_table(_Stub())({"lemma": "x", "form": "x", "pos": "noun"})
        assert html and "a&lt;b" in html and "a<b" not in html.replace("a&lt;b", "")

    def test_public_api(self):
        import eee_project as eee
        assert hasattr(eee, "build_modern_paradigm_table")
        assert callable(eee.build_modern_paradigm_table)

    def test_pronoun_gendered_singular_only(self):
        # κανένας is singular-only (no plural in this "no one/not any" sense,
        # see Pronoun('κανένας').all() -- only a "sg" key exists at all) and
        # has no vocative (no pronoun does) -- both must render as em-dash,
        # not be silently omitted or crash the table.
        html = self._bt()({"lemma": "κανένας", "form": "κανένας", "pos": "pronoun"})
        assert html and "κανένας" in html and "καμία" in html and "κανενός" in html
        # 4 rows (Nom/Gen/Acc/Voc) x 2 cols (Sg/Pl) = 8 cells; only Nom/Gen/Acc
        # Sg have real data -- the other 5 (Nom/Gen/Acc Pl + Voc Sg/Pl) are —.
        assert html.count(chr(8212)) == 5

    def test_pronoun_personal_case_number(self):
        # εγώ: Case+Number shape, no Gender axis -- must resolve through the
        # same Case x Number table as gendered pronouns (Gender is unioned
        # away, ignored by mg_pron_path("personal", ...) on the backend
        # side), not crash or silently return nothing.
        html = self._bt()({"lemma": "εγώ", "form": "εγώ", "pos": "pronoun"})
        assert html and "εγώ" in html and "εμένα" in html and "εμείς" in html

    def test_pronoun_indeclinable_returns_none(self):
        # πού never changes form regardless of Case/Number/Gender -- showing
        # it in every cell of a declension table would misrepresent an
        # invariant word as if it declines, so this must return None rather
        # than a table repeating the same word 8 times.
        html = self._bt()({"lemma": "πού", "form": "πού", "pos": "pronoun"})
        assert html is None


# ──────────────────────────── Modern rung in build_grc_lexicon_tabs ──

class TestModernRung:
    """el_backend appends a Modern rung to build_grc_lexicon_tabs (section-04)."""

    _W = {"lemma": "ἄνθρωπος", "form": "ἄνθρωπος", "pos": "noun",
          "lexicon_tag": 'ancient-greek["homer"]'}

    def _backends(self):
        from ancient_greek_backend_eee import AncientGreekBackend
        from unimorph_backend_eee import UniMorphBackend
        return AncientGreekBackend(lexicons=["homer"]), UniMorphBackend(language="grc")

    def test_modern_period_registered(self):
        from eee_project.notebook_utils import _GRC_LEX_PERIOD, _GRC_LEX_DESCR
        assert "modern" in _GRC_LEX_PERIOD and "modern" in _GRC_LEX_DESCR

    def test_modern_rung_present_with_el_backend(self):
        from modern_greek_backend_eee import ModernGreekBackend
        ag, um = self._backends()
        tabs = build_grc_lexicon_tabs(ag, um, lexicons={"homer": ag}, el_backend=ModernGreekBackend())
        html = tabs(dict(self._W)) or ""
        assert "Modern Greek" in html and "άνθρωπος" in html   # Modern rung + monotonic Modern form

    def test_no_modern_rung_without_el_backend(self):
        ag, um = self._backends()
        tabs = build_grc_lexicon_tabs(ag, um, lexicons={"homer": ag}, el_backend=None)
        assert "Modern Greek" not in (tabs(dict(self._W)) or "")

    def test_modern_rung_error_isolated(self):
        class _Boom:
            def get_slot_templates(self, *a, **k):
                raise RuntimeError("boom")
        ag, um = self._backends()
        tabs = build_grc_lexicon_tabs(ag, um, lexicons={"homer": ag}, el_backend=_Boom())
        # must not raise; Modern rung omitted, the grc/unimorph side still renders
        assert "Modern Greek" not in (tabs(dict(self._W)) or "")

    def test_no_modern_only_table_when_form_unattested_anywhere(self):
        # Regression: _lexicon_tag can tag a word "homer" based on its LEMMA
        # having *some* paradigm, even when THIS surface form isn't attested in
        # it (see notebook _lexicon_tag's lemma-only fallback). Reported live:
        # clicking "ἄλγεα" (lemma ἄλγος, tagged 'ancient-greek["homer"]') showed
        # a Modern-Greek-only table -- misleading, since no ancient source
        # actually confirms this form. The whole table must be hidden, not just
        # the ancient side, when neither a curated lexicon nor the unimorph
        # fallback attests the exact form (odyssey interactive-text, section 03).
        from modern_greek_backend_eee import ModernGreekBackend
        ag, um = self._backends()
        w = {"lemma": "ἄλγος", "form": "ἄλγεα", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        tabs = build_grc_lexicon_tabs(ag, um, lexicons={"homer": ag}, el_backend=ModernGreekBackend())
        assert tabs(w) is None


# ──────────────────────────── build_grc_lexicon_tabs require_lexicon ──

class TestRequireLexicon:
    """require_lexicon="homer": whole table hidden unless Homer specifically
    attests the exact form, even when another lexicon (or Modern) does --
    reported live for ανθρωπων (tagged "lsj" only; Homer has zero ανθρωπος
    forms) still showing a Classical+Modern table (odyssey interactive-text,
    section 03)."""

    def _backends(self):
        from ancient_greek_backend_eee import AncientGreekBackend
        from unimorph_backend_eee import UniMorphBackend
        return AncientGreekBackend(lexicons=["homer"]), UniMorphBackend(language="grc")

    def test_hidden_when_required_lexicon_lacks_exact_form(self):
        # ανθρωπος has ZERO Homer-lexicon paradigm data (confirmed live);
        # ανθρωπων is tagged "lsj" only, and LSJ has the exact form.
        from modern_greek_backend_eee import ModernGreekBackend
        ag, um = self._backends()
        w = {"lemma": "ἄνθρωπος", "form": "ἀνθρώπων", "pos": "noun",
             "lexicon_tag": 'ancient-greek["lsj"]'}
        tabs = build_grc_lexicon_tabs(ag, um, lexicons={"homer": ag}, el_backend=ModernGreekBackend(),
                                       require_lexicon="homer")
        assert tabs(w) is None

    def test_shown_when_required_lexicon_has_exact_form(self):
        # ανηρ (Ανδρα, accusative) has 14 confirmed Homer forms.
        from modern_greek_backend_eee import ModernGreekBackend
        ag, um = self._backends()
        w = {"lemma": "ἀνήρ", "form": "Ἄνδρα", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        tabs = build_grc_lexicon_tabs(ag, um, lexicons={"homer": ag}, el_backend=ModernGreekBackend(),
                                       require_lexicon="homer")
        html = tabs(w)
        assert html is not None
        # attested in the anchor lexicon -> the rest of the diachronic
        # progression (here: Modern) still renders alongside it, unchanged
        assert "Modern Greek" in html

    def test_default_none_preserves_prior_behaviour(self):
        # Same "lsj"-only word as the hidden case above, but WITHOUT
        # require_lexicon -- must render normally (backward compatible).
        # lexicons= must genuinely include an "lsj" backend (not just "homer"),
        # or this exercises the unimorph-fallback path instead of the
        # tag-matching path its own name/comment claims to guard.
        from ancient_greek_backend_eee import AncientGreekBackend
        from modern_greek_backend_eee import ModernGreekBackend
        ag, um = self._backends()
        ag_lsj = AncientGreekBackend(lexicons=["lsj"])
        w = {"lemma": "ἄνθρωπος", "form": "ἀνθρώπων", "pos": "noun",
             "lexicon_tag": 'ancient-greek["lsj"]'}
        tabs = build_grc_lexicon_tabs(ag, um, lexicons={"homer": ag, "lsj": ag_lsj},
                                       el_backend=ModernGreekBackend())
        html = tabs(w)
        assert html is not None
        assert "Modern Greek" in html  # confirms the tag-matched lsj path, not the fallback

    def test_unknown_required_lexicon_key_hides(self):
        ag, um = self._backends()
        w = {"lemma": "ἀνήρ", "form": "Ἄνδρα", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        tabs = build_grc_lexicon_tabs(ag, um, lexicons={"homer": ag}, require_lexicon="nonexistent")
        assert tabs(w) is None


# ────────────────────────────────────────── add_labels ──

class TestAddLabels:
    def test_context_present_uses_dash_format(self):
        words = [{"context": "IX.42", "meaning": "loosen"}]
        add_labels(words)
        assert words[0]["_label"] == "IX.42 – loosen"

    def test_context_missing_uses_guillemets(self):
        words = [{"meaning": "loosen"}]
        add_labels(words)
        assert words[0]["_label"] == "«loosen»"

    def test_context_empty_string_uses_guillemets(self):
        words = [{"context": "", "meaning": "loosen"}]
        add_labels(words)
        assert words[0]["_label"] == "«loosen»"

    def test_mutates_in_place_multiple_words(self):
        words = [{"meaning": "a"}, {"context": "ctx", "meaning": "b"}]
        result = add_labels(words)
        assert result is None
        assert words[0]["_label"] == "«a»"
        assert words[1]["_label"] == "ctx – b"


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


# ───────────────────────────────────────── parse_stanza_text ──

class TestParseStanzaText:
    def test_default_prefix_single_stanza(self):
        md = "### Ithaki 1-3\n\nΣαν βγεις\nνα εύχεσαι\n"
        assert parse_stanza_text(md) == {"Ithaki 1-3": ["Σαν βγεις", "να εύχεσαι"]}

    def test_custom_ref_prefix(self):
        md = "### Odyss. IX.39-42\n\nἸλιόθεν\nἸσμάρῳ\n"
        assert parse_stanza_text(md, ref_prefix="### Odyss. ") == {
            "IX.39-42": ["Ἰλιόθεν", "Ἰσμάρῳ"]
        }

    def test_multiple_stanzas_in_order(self):
        md = "### A\nline1\nline2\n### B\nline3\n"
        result = parse_stanza_text(md)
        assert list(result.keys()) == ["A", "B"]
        assert result["A"] == ["line1", "line2"]
        assert result["B"] == ["line3"]

    def test_comment_lines_skipped(self):
        md = "<!-- edition note -->\n### A\n<!-- inline comment -->\nreal line\n"
        assert parse_stanza_text(md) == {"A": ["real line"]}

    def test_blank_lines_skipped(self):
        md = "### A\nline1\n\n\nline2\n"
        assert parse_stanza_text(md) == {"A": ["line1", "line2"]}

    def test_lines_before_first_heading_ignored(self):
        md = "orphan line\n### A\nreal line\n"
        assert parse_stanza_text(md) == {"A": ["real line"]}

    def test_empty_input(self):
        assert parse_stanza_text("") == {}


# ─────────────────────────────────── parse_stanza_translations ──

class TestParseStanzaTranslations:
    def test_single_translator_single_stanza(self):
        md = "## Жуковский\n### A\nline1\nline2\n"
        out, desc = parse_stanza_translations(md)
        assert out == {"Жуковский": {"A": "line1\nline2"}}
        assert desc == {}

    def test_description_comment_captured(self):
        md = "## Жуковский\n<!-- **Жуковский, 1849** · рус. -->\n### A\nline1\n"
        out, desc = parse_stanza_translations(md)
        assert desc == {"Жуковский": "**Жуковский, 1849** · рус."}
        assert out == {"Жуковский": {"A": "line1"}}

    def test_translator_without_description_omitted_from_desc(self):
        # подстрочник's own convention: no <!-- **...** --> comment at all
        md = "## подстрочник\n### A\nline1\n"
        out, desc = parse_stanza_translations(md)
        assert "подстрочник" not in desc
        assert out == {"подстрочник": {"A": "line1"}}

    def test_multiple_translators_and_stanzas(self):
        md = (
            "## Жуковский\n### A\nj-a\n### B\nj-b\n"
            "---\n"
            "## Вересаев\n### A\nv-a\n### B\nv-b\n"
        )
        out, desc = parse_stanza_translations(md)
        assert out == {
            "Жуковский": {"A": "j-a", "B": "j-b"},
            "Вересаев": {"A": "v-a", "B": "v-b"},
        }

    def test_dash_separator_not_treated_as_content(self):
        md = "## T\n### A\nline1\n---\n"
        out, _ = parse_stanza_translations(md)
        assert out == {"T": {"A": "line1"}}

    def test_custom_ref_prefix(self):
        md = "## T\n### Odyss. IX.39-42\nline1\n"
        out, _ = parse_stanza_translations(md, ref_prefix="### Odyss. ")
        assert out == {"T": {"IX.39-42": "line1"}}

    def test_empty_input(self):
        assert parse_stanza_translations("") == ({}, {})

    def test_round_trips_with_parse_stanza_text_line_count(self):
        # the contract parse_stanza_text/parse_stanza_translations callers rely
        # on: one translation line per source line, same order, so they can be
        # zipped positionally.
        greek_md = "### A\nline1\nline2\nline3\n"
        trans_md = "## T\n### A\nt1\nt2\nt3\n"
        greek = parse_stanza_text(greek_md)
        trans, _ = parse_stanza_translations(trans_md)
        assert len(greek["A"]) == len(trans["T"]["A"].split("\n"))


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


class TestSetupAncientGreek:
    def test_registers_and_chains(self):
        from eee_project import get_chain
        class _FakeBackend:
            def paradigm(self, w, p): return {}
        fb = _FakeBackend()
        setup_ancient_greek(fb)
        assert get_chain("grc") == ["ancient-greek"]


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

    def test_all_50_keys_present_in_all_3_languages(self):
        # regression: guards against a TSV row silently dropped for one
        # language during a future edit -- every key must resolve in en/ru/el.
        gu = GreekUtils(mo_module=_StubMo())
        keys = [
            'test1_heading', 'test2_heading', 'test3_heading', 'test4_heading',
            'select_nouns', 'select_verbs', 'select_adjs', 'select_pron', 'translation_label',
            'simple_noun_heading', 'article_noun_heading', 'verb_heading', 'adj_heading', 'pron_heading',
            'noun_empty', 'verb_empty', 'verb_no_tense', 'adj_empty', 'pron_empty',
            'tense_label', 'mode_label', 'indefinite_label', 'check_label',
            'def_prefix', 'indef_prefix',
            'nouns_not_found', 'verbs_not_found', 'adjs_not_found', 'pron_not_found',
            'test1_done', 'test2_done', 'test3_done', 'test4_done',
            'poem_section_heading', 'vocabulary_heading',
            'test_label', 'presence_test_topic', 'noun_test_topic', 'verb_test_topic', 'adj_test_topic',
            'drill_title', 'drill_description', 'pos_label', 'load_tsv_label',
            'require_article_label', 'full_paradigm_label',
            'verb_done', 'noun_done', 'adj_done', 'word_label',
        ]
        for key in keys:
            for lang in ('en', 'ru', 'el'):
                label = gu.ui_label(key, lang)
                assert label != key, f"{key!r} missing a real {lang} label (echoed the key back)"


# ──────── language_bridge / language_selector / save_language_selection ──

class _FakeDropdown:
    """Mirrors real marimo dropdown semantics: .value resolves through
    *options* by the given label, not the label itself."""
    def __init__(self, options=None, value=None, label=""):
        self.options = options or {}
        self.label = label
        self.value = self.options.get(value)


class _LangMo(_StubMoLayout):
    class ui:
        @staticmethod
        def dropdown(options=None, value=None, label=""):
            return _FakeDropdown(options, value, label)
        @staticmethod
        def anywidget(inst):
            return inst


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


class TestSaveLanguageSelection:
    def test_bridge_none_is_noop(self):
        selector = language_selector(_LangMo(), None)
        save_language_selection(None, selector)  # must not raise

    def test_skips_write_while_bridge_unset(self):
        # the race-condition fix: don't clobber a real stored value with the
        # placeholder default before the (async) browser read has landed --
        # simulated here by the bridge still reporting None.
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        mo_stub = _LangMo()
        bridge = language_bridge(mo_stub)
        selector = language_selector(mo_stub, bridge)
        save_language_selection(bridge, selector)
        assert bridge.save == ""

    def test_writes_once_bridge_has_real_value(self):
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        mo_stub = _LangMo()
        bridge = language_bridge(mo_stub)
        bridge.stored = "ru"  # simulates the browser read landing
        selector = language_selector(mo_stub, bridge)
        save_language_selection(bridge, selector)
        assert bridge.save == "ru"


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
        import eee_project.notebook_utils as _nu
        if not _nu._ANYWIDGET_OK:
            pytest.skip("anywidget not installed")
        result = eee_topbar(_FormMo(), back_url="", lang="en",
                            titles="T", ga_config={"measurement_id": "G-TEST123"})
        assert result is not None
        assert "G-TEST123" in result._esm

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


class TestParentBackUrl:
    """Deliberately remote-only (no local-first check) — see the function's
    own docstring: a Path(__file__).parent.parent local lookup silently
    finds nothing on molab every time, since molab only bundles the calling
    notebook's own directory, never a parent's."""

    _PARENT_TSV = (
        "url\ticon\tgreek\tlabel\ttitle\tdesc\tindex_url\n"
        "https://molab.marimo.io/notebooks/nb_CHILD/app\tΑ\tgreek\tlabel\ttitle\tdesc\thttps://molab.marimo.io/notebooks/nb_PARENT/app\n"
    )

    def test_fetches_remote_and_returns_index_url(self):
        with patch("urllib.request.urlopen", return_value=_make_resp(self._PARENT_TSV.encode("utf-8"))):
            result = parent_back_url("https://example.com/parent-fetch-test/index.tsv")
        assert result == "https://molab.marimo.io/notebooks/nb_PARENT/app"

    def test_network_failure_returns_none(self):
        with patch("urllib.request.urlopen", side_effect=Exception("network error")):
            result = parent_back_url("https://example.com/parent-failure-test/index.tsv")
        assert result is None

    def test_repeat_call_is_cached_no_second_fetch(self):
        _url = "https://example.com/parent-cache-test/index.tsv"
        with patch("urllib.request.urlopen", return_value=_make_resp(self._PARENT_TSV.encode("utf-8"))) as _mock:
            parent_back_url(_url)
            parent_back_url(_url)
        assert _mock.call_count == 1


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

    def test_github_pages_host(self, monkeypatch):
        self._install_fake_js(monkeypatch, "eee-project.github.io")
        assert _source_host_base() == "https://github.com/EEE-project"

    def test_gitlab_pages_host(self, monkeypatch):
        self._install_fake_js(monkeypatch, "eee-project.gitlab.io")
        assert _source_host_base() == "https://gitlab.com/EEE-project"

    def test_split_gitlab_project_host_still_maps_to_gitlab(self, monkeypatch):
        # A split course lives on the same eee-project.gitlab.io domain,
        # just a different path -- hostname-only detection must not need
        # special-casing per split project.
        self._install_fake_js(monkeypatch, "eee-project.gitlab.io")
        assert _source_host_base() == "https://gitlab.com/EEE-project"

    def test_codeberg_pages_host(self, monkeypatch):
        self._install_fake_js(monkeypatch, "eee-project.codeberg.page")
        assert _source_host_base() == "https://codeberg.org/EEE-project"

    def test_no_js_module_falls_back_to_codeberg(self, monkeypatch):
        import sys
        monkeypatch.delitem(sys.modules, "js", raising=False)
        assert _source_host_base() == "https://codeberg.org/EEE-project"

    def test_unrecognized_hostname_falls_back_to_codeberg(self, monkeypatch):
        self._install_fake_js(monkeypatch, "localhost")
        assert _source_host_base() == "https://codeberg.org/EEE-project"

    def test_eee_footer_links_to_detected_host(self, monkeypatch):
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
_SAMPLE_GA = {"measurement_id": "G-TEST1234"}


def _make_resp(data: bytes):
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


# ──────────────────────────────────────── _norm_grc ──

class TestNormGrc:
    def test_strips_acute(self):
        assert _norm_grc("λόγος") == "λογος"

    def test_strips_rough_breathing(self):
        assert _norm_grc("ἄνθρωπος") == "ανθρωπος"

    def test_strips_circumflex(self):
        assert _norm_grc("τῶν") == "των"

    def test_lowercases(self):
        assert _norm_grc("Λόγος") == "λογος"

    def test_plain_unchanged(self):
        assert _norm_grc("λογος") == "λογος"

    def test_empty(self):
        assert _norm_grc("") == ""


# ─────────────────────────── build_grc_paradigm_table ──

class _EmptyGrcBackend:
    """Backend stub that returns no slot templates."""
    def get_slot_templates(self, lang, pos, terms_lang="en"):
        return None


class TestBuildGrcParadigmTable:
    def test_returns_callable(self):
        fn = build_grc_paradigm_table(_EmptyGrcBackend(), _EmptyGrcBackend())
        assert callable(fn)

    def test_unknown_pos_returns_none(self):
        fn = build_grc_paradigm_table(_EmptyGrcBackend(), _EmptyGrcBackend())
        result = fn({"lemma": "δέ", "pos": "particle", "form": "δέ"})
        assert result is None

    def test_no_slots_returns_none_for_noun(self):
        fn = build_grc_paradigm_table(_EmptyGrcBackend(), _EmptyGrcBackend())
        result = fn({"lemma": "θεός", "pos": "noun", "form": "θεόν"})
        assert result is None

    def test_no_slots_returns_none_for_verb(self):
        fn = build_grc_paradigm_table(_EmptyGrcBackend(), _EmptyGrcBackend())
        result = fn({"lemma": "λύω", "pos": "verb", "form": "λύει"})
        assert result is None

    def test_no_slots_returns_none_for_adj(self):
        fn = build_grc_paradigm_table(_EmptyGrcBackend(), _EmptyGrcBackend())
        result = fn({"lemma": "καλός", "pos": "adj", "form": "καλόν"})
        assert result is None

    def test_public_api(self):
        import eee_project as eee
        assert hasattr(eee, "build_grc_paradigm_table")
        assert callable(eee.build_grc_paradigm_table)


# ──────────────────────────── build_grc_lexicon_tabs ──

class TestBuildGrcLexiconTabs:
    def test_returns_callable(self):
        fn = build_grc_lexicon_tabs(
            _EmptyGrcBackend(), _EmptyGrcBackend(), lexicons={}
        )
        assert callable(fn)

    def test_no_lexicon_tag_delegates_to_paradigm(self):
        fn = build_grc_lexicon_tabs(
            _EmptyGrcBackend(), _EmptyGrcBackend(), lexicons={}
        )
        w = {"lemma": "θεός", "pos": "noun", "form": "θεόν", "lexicon_tag": ""}
        assert fn(w) is None

    def test_unknown_pos_returns_none(self):
        fn = build_grc_lexicon_tabs(
            _EmptyGrcBackend(), _EmptyGrcBackend(), lexicons={}
        )
        w = {"lemma": "δέ", "pos": "particle", "form": "δέ", "lexicon_tag": ""}
        assert fn(w) is None

    def test_lang_kwarg_accepted(self):
        fn_pt = build_grc_paradigm_table(_EmptyGrcBackend(), _EmptyGrcBackend())
        fn_lt = build_grc_lexicon_tabs(_EmptyGrcBackend(), _EmptyGrcBackend(), lexicons={})
        w = {"lemma": "θεός", "pos": "noun", "form": "θεόν", "lexicon_tag": ""}
        fn_pt(w, lang="ru")   # must not raise TypeError
        fn_lt(w, lang="ru")   # must not raise TypeError

    def test_public_api(self):
        import eee_project as eee
        assert hasattr(eee, "build_grc_lexicon_tabs")
        assert callable(eee.build_grc_lexicon_tabs)


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
    def __init__(self, value=None, disabled=False, label=""):
        self.value = value
        self.disabled = disabled
        self.label = label


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


class _FormMo(_StubMoLayout):
    """Extended marimo stub with button/radio support."""
    class Html:
        def __init__(self, s): self.s = s
        def __str__(self): return self.s
        def __repr__(self): return self.s
    class ui:
        @staticmethod
        def button(label="", on_click=None, disabled=False):
            return _FakeBtn(value=None, disabled=disabled, label=label)
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


# ────────────────────────────────────────── make_renew_button ──

class TestMakeRenewButton:
    def test_returns_renew_button(self, gu_form):
        btn = gu_form.make_renew_button()
        assert btn.label == "↺ Новый набор"


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


class TestRenderGlossPanel:
    def test_no_selection_shows_placeholder(self, gu_form):
        panel = gu_form.render_gloss_panel(
            [{"form": "x", "lemma": "x"}], "not-there", lambda w: "",
        )
        assert "Выберите слово" in panel

    def test_selected_word_without_lexicon_tables(self, gu_form):
        words = [{"form": "λόγος", "lemma": "λόγος", "context": "word", "meaning": "word/reason"}]
        panel = gu_form.render_gloss_panel(words, "λόγος", lambda w: "")
        assert "λόγος" in panel
        assert "word/reason" in panel

    def test_selected_word_with_lexicon_tables(self, gu_form):
        words = [{"form": "λόγος", "lemma": "λόγος", "context": "word", "meaning": "word/reason"}]
        panel = gu_form.render_gloss_panel(words, "λόγος", lambda w: "<table>...</table>")
        assert "λόγος" in panel[0]
        assert "word/reason" in panel[0]
        assert "Формы слова по эпохам" in panel[1]
        assert str(panel[2]) == "<table>...</table>"


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

    def _call(self, gu, state, wi=None, next_v=None, prev_v=None, vocab=None, lang="ru"):
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, fut_g, fut_s = state
        wi = wi or _FakeWI()
        return gu.word_drill_form(
            cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
            hist_g, hist_s, fut_g, fut_s,
            wi, wi._ui, _FakeBtn(None), _FakeBtn(prev_v), _FakeBtn(next_v),
            vocab=vocab or _WD_VOCAB,
            lang=lang,
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


# ────────────────────────────────────────── word_quiz_form ──

class TestWordQuizForm:
    def _state(self, cv=None, rem=None, sc=None, rst=None, hist=None, fut=None):
        return _form_state(cv, rem, sc, rst, hist, fut)

    def _call(self, gu, state, radio=None, next_v=None, prev_v=None, vocab=None,
              build_paradigm_table=None, lang="ru", renew_btn=None):
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, _, fut_g, fut_s = state
        return gu.word_quiz_form(
            cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
            hist_g, hist_s, fut_g, fut_s,
            radio or _FakeRadio(), _FakeBtn(next_v), _FakeBtn(prev_v),
            vocab=vocab or _WQ_VOCAB,
            build_paradigm_table=build_paradigm_table,
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

    def test_next_with_answer_advances(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        sc_b = state[8]
        result = self._call(gu_form, state, radio=_FakeRadio(value=w["form"]), next_v=1)
        assert result == "*...*"
        assert sc_b[0]["total"] == 1

    def test_next_without_answer_rerenders(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        sc_b = state[8]
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1)
        assert result != "*...*"
        assert sc_b[0]["total"] == 0

    def test_renew_btn_included_in_nav_row(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        renew = _FakeBtn(label="renew")
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1, renew_btn=renew)
        assert renew in result[-1]

    def test_no_renew_btn_omitted_from_nav_row(self, gu_form):
        w = _WQ_VOCAB[0]
        state = self._state(cv=w, rem=_WQ_VOCAB[1:])
        result = self._call(gu_form, state, radio=_FakeRadio(value=None), next_v=1)
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


# ────────────────────────────────────────── ensure_file ──

@pytest.fixture
def gu_marimo():
    return GreekUtils(mo_module=mo, config=ANCIENT_GREEK)


class TestEnsureFile:
    def test_existing_file_returned_without_download(self, gu_marimo, tmp_path):
        f = tmp_path / "vocab.tsv"
        f.write_text("Word\tTranslation\n")
        result = gu_marimo.ensure_file("vocab.tsv", nb_dir=tmp_path, remote_base="http://example.com")
        assert result == f

    def test_missing_remote_returns_none_and_prints(self, gu_marimo, tmp_path, capsys):
        from urllib.error import HTTPError
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            "http://example.com/missing.pdf", 404, "Not Found", {}, None
        )):
            result = gu_marimo.ensure_file("missing.pdf", nb_dir=tmp_path, remote_base="http://example.com")
        assert result is None
        captured = capsys.readouterr()
        assert "missing.pdf" in captured.out
        assert "404" in captured.out or "Not Found" in captured.out

    def test_failed_download_leaves_no_file(self, gu_marimo, tmp_path):
        from urllib.error import HTTPError
        with patch("urllib.request.urlopen", side_effect=HTTPError(
            "http://example.com/file.tsv", 404, "Not Found", {}, None
        )):
            gu_marimo.ensure_file("file.tsv", nb_dir=tmp_path, remote_base="http://example.com")
        assert not (tmp_path / "file.tsv").exists()

    def test_successful_download(self, gu_marimo, tmp_path):
        with patch("urllib.request.urlopen", return_value=_make_resp(b"downloaded")):
            result = gu_marimo.ensure_file("file.tsv", nb_dir=tmp_path, remote_base="http://example.com")
        assert result == tmp_path / "file.tsv"
        assert result.read_text() == "downloaded"

    def test_download_non_ascii_filename(self, gu_marimo, tmp_path):
        # Regression: ensure_file used to call urllib.request.urlretrieve(),
        # which raises UnicodeEncodeError ("'ascii' codec can't encode...")
        # under Pyodide (pyodide_http's patched urllib) whenever the local
        # destination path contains non-ASCII characters -- confirmed this
        # is specific to urlretrieve's internals, not urlopen, by
        # reproducing locally with plain CPython (urlretrieve itself was
        # fine there, isolating the bug to the Pyodide-specific code path).
        # Real course notebooks fetch Cyrillic-named PDFs this way.
        with patch("urllib.request.urlopen", return_value=_make_resp(b"%PDF-1.4 fake")):
            result = gu_marimo.ensure_file(
                "Одиссея. Зачин.pdf", nb_dir=tmp_path, remote_base="http://example.com",
            )
        assert result == tmp_path / "Одиссея. Зачин.pdf"
        assert result.read_bytes() == b"%PDF-1.4 fake"

    def test_codeberg_remote_base_rewritten_before_fetch(self, gu_marimo, tmp_path):
        # ensure_file's remote fetch must go out via the CORS-safe Codeberg
        # API form, not the plain git-web raw URL (which sends no
        # Access-Control-Allow-Origin header and is silently blocked by a
        # browser fetch inside a self-hosted WASM export).
        seen = {}

        def fake_urlopen(url, timeout=None):
            seen["url"] = url
            return _make_resp(b"x")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            gu_marimo.ensure_file(
                "vocab.tsv", nb_dir=tmp_path,
                remote_base="https://codeberg.org/EEE-project/eee-project/raw/branch/main/examples",
            )
        assert seen["url"] == (
            "https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/examples/vocab.tsv?ref=main"
        )


class TestEnsureFiles:
    """GreekUtils.ensure_files: concurrent ensure_file() for several filenames at once."""

    def test_all_local_returns_paths_without_fetching(self, gu_marimo, tmp_path):
        import asyncio
        (tmp_path / "a.tsv").write_text("a")
        (tmp_path / "b.tsv").write_text("b")
        with patch("urllib.request.urlopen") as mock_urlopen:
            result = asyncio.run(gu_marimo.ensure_files(
                "a.tsv", "b.tsv", nb_dir=tmp_path, remote_base="http://example.com",
            ))
        mock_urlopen.assert_not_called()
        assert result == {"a.tsv": tmp_path / "a.tsv", "b.tsv": tmp_path / "b.tsv"}

    def test_missing_files_fetched_and_written(self, gu_marimo, tmp_path):
        import asyncio
        with patch("urllib.request.urlopen", return_value=_make_resp(b"downloaded")):
            result = asyncio.run(gu_marimo.ensure_files(
                "x.tsv", "y.tsv", nb_dir=tmp_path, remote_base="http://example.com",
            ))
        assert result["x.tsv"] == tmp_path / "x.tsv"
        assert result["y.tsv"] == tmp_path / "y.tsv"
        assert (tmp_path / "x.tsv").read_text() == "downloaded"
        assert (tmp_path / "y.tsv").read_text() == "downloaded"

    def test_mixed_local_and_remote(self, gu_marimo, tmp_path):
        import asyncio
        (tmp_path / "local.tsv").write_text("already here")
        with patch("urllib.request.urlopen", return_value=_make_resp(b"fetched")):
            result = asyncio.run(gu_marimo.ensure_files(
                "local.tsv", "remote.tsv", nb_dir=tmp_path, remote_base="http://example.com",
            ))
        assert result["local.tsv"].read_text() == "already here"
        assert result["remote.tsv"].read_text() == "fetched"

    def test_one_failure_does_not_affect_others(self, gu_marimo, tmp_path, capsys):
        import asyncio
        from urllib.error import HTTPError

        def fake_urlopen(url, timeout=None):
            if "missing" in url:
                raise HTTPError(url, 404, "Not Found", {}, None)
            return _make_resp(b"ok")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = asyncio.run(gu_marimo.ensure_files(
                "missing.tsv", "present.tsv", nb_dir=tmp_path, remote_base="http://example.com",
            ))
        assert result["missing.tsv"] is None
        assert result["present.tsv"] == tmp_path / "present.tsv"
        assert "missing.tsv" in capsys.readouterr().out

    def test_codeberg_remote_base_rewritten_before_fetch(self, gu_marimo, tmp_path):
        import asyncio
        seen = []

        def fake_urlopen(url, timeout=None):
            seen.append(url)
            return _make_resp(b"x")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            asyncio.run(gu_marimo.ensure_files(
                "vocab.tsv", nb_dir=tmp_path,
                remote_base="https://codeberg.org/EEE-project/eee-project/raw/branch/main/examples",
            ))
        assert seen == [
            "https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/examples/vocab.tsv?ref=main"
        ]


class TestCorsSafeRawUrl:
    """_cors_safe_raw_url: rewrite CORS-blind git-forge raw URLs at fetch time."""

    def test_codeberg_raw_branch_url_rewritten(self):
        assert _cors_safe_raw_url(
            "https://codeberg.org/EEE-project/eee-project/raw/branch/main/examples/vocab.tsv"
        ) == "https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/examples/vocab.tsv?ref=main"

    def test_codeberg_nested_path_preserved(self):
        assert _cors_safe_raw_url(
            "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main/"
            "ancient_greek/palaestra/index.tsv"
        ) == (
            "https://codeberg.org/api/v1/repos/EEE-project/created_with_eee/raw/"
            "ancient_greek/palaestra/index.tsv?ref=main"
        )

    def test_codeberg_non_main_branch_preserved(self):
        assert _cors_safe_raw_url(
            "https://codeberg.org/EEE-project/eee-project/raw/branch/dev/x.tsv"
        ) == "https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/x.tsv?ref=dev"

    def test_gitlab_raw_url_rewritten_with_percent_encoded_path(self):
        assert _cors_safe_raw_url(
            "https://gitlab.com/EEE-project/created_with_eee/-/raw/main/"
            "ancient_greek/palaestra/index.tsv"
        ) == (
            "https://gitlab.com/api/v4/projects/EEE-project%2Fcreated_with_eee/"
            "repository/files/ancient_greek%2Fpalaestra%2Findex.tsv/raw?ref=main"
        )

    def test_gitlab_flat_filename(self):
        assert _cors_safe_raw_url(
            "https://gitlab.com/EEE-project/eee-project/-/raw/main/README.md"
        ) == (
            "https://gitlab.com/api/v4/projects/EEE-project%2Feee-project/"
            "repository/files/README.md/raw?ref=main"
        )

    def test_github_raw_url_unchanged(self):
        # raw.githubusercontent.com already sends Access-Control-Allow-Origin.
        url = "https://raw.githubusercontent.com/EEE-project/eee-project/main/README.md"
        assert _cors_safe_raw_url(url) == url

    def test_already_codeberg_api_form_unchanged(self):
        # Idempotent: a URL already in the CORS-safe form must not be rewritten again.
        url = "https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/examples/vocab.tsv"
        assert _cors_safe_raw_url(url) == url

    def test_unrelated_url_unchanged(self):
        url = "https://example.com/some/file.tsv"
        assert _cors_safe_raw_url(url) == url


class TestFetchUrlBytes:
    """_fetch_url_bytes: plain urlopen on CPython, raw sync XHR on Pyodide.

    The XHR branch bypasses pyodide_http entirely because it raises
    UnicodeEncodeError on a non-ASCII Content-Disposition response header
    (confirmed via a diagnostic traceback pointing inside
    pyodide_http/_urllib.py itself) -- e.g. Codeberg's raw-content API
    sends the primary filename= parameter as raw UTF-8, un-percent-encoded,
    for any non-ASCII filename. `js` only exists under Pyodide, so these
    tests inject a fake module into sys.modules to exercise the branch.
    """

    @staticmethod
    def _install_fake_js(monkeypatch, *, status=200, status_text="OK", body=b""):
        import sys
        import types

        sent = {}

        class _FakeXHR:
            def open(self, method, url, is_async):
                sent["method"], sent["url"], sent["async"] = method, url, is_async

            def send(self, _body):
                sent["timeout"] = self.timeout
                self.status = status
                self.statusText = status_text
                self.response = body

        class _FakeTypedArray:
            def __init__(self, data):
                self._data = data

            def to_py(self):
                return memoryview(self._data)

        fake_js = types.ModuleType("js")
        fake_js.XMLHttpRequest = types.SimpleNamespace(new=_FakeXHR)
        fake_js.Uint8Array = types.SimpleNamespace(new=_FakeTypedArray)
        monkeypatch.setitem(sys.modules, "js", fake_js)
        monkeypatch.setattr(sys, "platform", "emscripten")
        return sent

    def test_cpython_uses_urlopen(self):
        with patch("urllib.request.urlopen", return_value=_make_resp(b"cpython path")):
            assert _fetch_url_bytes("https://example.com/x.tsv", 30) == b"cpython path"

    def test_emscripten_uses_sync_xhr_and_returns_bytes(self, monkeypatch):
        sent = self._install_fake_js(monkeypatch, status=200, body=b"pdf bytes here")
        result = _fetch_url_bytes("https://example.com/Одиссея.pdf", 30)
        assert result == b"pdf bytes here"
        assert sent["method"] == "GET"
        assert sent["url"] == "https://example.com/Одиссея.pdf"
        assert sent["async"] is False
        assert sent["timeout"] == 30 * 1000  # xhr.timeout is milliseconds

    def test_emscripten_raises_http_error_on_failure_status(self, monkeypatch):
        from urllib.error import HTTPError
        self._install_fake_js(monkeypatch, status=404, status_text="Not Found")
        with pytest.raises(HTTPError):
            _fetch_url_bytes("https://example.com/missing.pdf", 30)


class TestFetchUrlBytesAsync:
    """_fetch_url_bytes_async: threaded urlopen on CPython, pyodide.http.pyfetch on Pyodide.

    Exists so GreekUtils.ensure_files() can fetch several files concurrently
    via asyncio.gather -- real network-level overlap, which sync XHR (used
    by _fetch_url_bytes) can't provide. `pyodide.http` only exists under
    Pyodide, so these tests inject a fake module into sys.modules to
    exercise that branch, matching the `js`-faking pattern above.
    """

    @staticmethod
    def _install_fake_pyfetch(monkeypatch, *, ok=True, status=200, status_text="OK", body=b"", hang=False):
        import asyncio
        import sys
        import types

        sent = {}

        class _FakeResponse:
            def __init__(self):
                self.ok = ok
                self.status = status
                self.status_text = status_text

            async def bytes(self):
                return body

        async def fake_pyfetch(url, **kwargs):
            sent["url"] = url
            sent["kwargs"] = kwargs
            if hang:
                await asyncio.sleep(10)
            return _FakeResponse()

        fake_http = types.ModuleType("pyodide.http")
        fake_http.pyfetch = fake_pyfetch
        fake_pyodide = types.ModuleType("pyodide")
        fake_pyodide.http = fake_http
        monkeypatch.setitem(sys.modules, "pyodide", fake_pyodide)
        monkeypatch.setitem(sys.modules, "pyodide.http", fake_http)
        monkeypatch.setattr(sys, "platform", "emscripten")
        return sent

    def test_cpython_delegates_to_sync_fetch_via_thread(self):
        import asyncio
        with patch("urllib.request.urlopen", return_value=_make_resp(b"cpython async path")):
            result = asyncio.run(_fetch_url_bytes_async("https://example.com/x.tsv", 30))
        assert result == b"cpython async path"

    def test_emscripten_uses_pyfetch_and_returns_bytes(self, monkeypatch):
        import asyncio
        sent = self._install_fake_pyfetch(monkeypatch, body=b"pdf bytes here")
        result = asyncio.run(_fetch_url_bytes_async("https://example.com/Одиссея.pdf", 30))
        assert result == b"pdf bytes here"
        assert sent["url"] == "https://example.com/Одиссея.pdf"
        assert sent["kwargs"]["method"] == "GET"

    def test_emscripten_raises_http_error_on_failure_status(self, monkeypatch):
        import asyncio
        from urllib.error import HTTPError
        self._install_fake_pyfetch(monkeypatch, ok=False, status=404, status_text="Not Found")
        with pytest.raises(HTTPError):
            asyncio.run(_fetch_url_bytes_async("https://example.com/missing.pdf", 30))

    def test_emscripten_enforces_timeout(self, monkeypatch):
        # pyfetch has no native timeout (unlike XHR's .timeout); this must
        # be enforced with asyncio.wait_for around the whole await chain.
        import asyncio
        self._install_fake_pyfetch(monkeypatch, hang=True)
        with pytest.raises(asyncio.TimeoutError):
            asyncio.run(_fetch_url_bytes_async("https://example.com/slow.pdf", 0.05))


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
        ok, fb = gu.check_noun_test("ὁ ἀγρός", form, article=True)
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
        ok, fb = gu_mg.check_noun_test("ο λόγος", form, article=True, indefinite=True)
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
        assert calls["words"] == vocab
        assert calls["words"] is not vocab  # a fresh copy, not the same list object
        assert calls["hist"] == []
        assert calls["msg"] == ""
        assert calls["cap"] is None
        assert calls["entered"] == {}
        assert calls["sub"] == 0
        assert calls["prev"] == 0
        assert calls["nxt"] == 0


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

    def test_nxt_disabled_with_one_remaining(self, gu):
        with self._patched():
            _, _, nxt_btn, _ = gu.paradigm_drill_widgets(labels=["1 sg:"], remaining_len=1)
        assert nxt_btn.disabled is True

    def test_nxt_enabled_with_more_remaining(self, gu):
        with self._patched():
            _, _, nxt_btn, _ = gu.paradigm_drill_widgets(labels=["1 sg:"], remaining_len=3)
        assert nxt_btn.disabled is False

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
        assert restart_btn.label == "Начать заново"

    def test_lang_en_uses_english_labels(self, gu):
        with self._patched():
            _, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="en",
            )
        assert nxt_btn.label == "Next ▸"
        assert prev_btn.label == "◂ Prev"
        assert restart_btn.label == "↺ Start over"

    def test_lang_el_uses_greek_labels(self, gu):
        with self._patched():
            _, prev_btn, nxt_btn, restart_btn = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="el",
            )
        assert nxt_btn.label == "Επόμενο"
        assert prev_btn.label == "Προηγούμενο"
        assert restart_btn.label == "Από την αρχή"

    def test_explicit_labels_override_lang_default(self, gu):
        with self._patched():
            _, prev_btn, nxt_btn, _ = gu.paradigm_drill_widgets(
                labels=["1 sg:"], lang="en", next_label="Continue", prev_label="Back",
            )
        assert nxt_btn.label == "Continue"
        assert prev_btn.label == "Back"


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
        assert state["words"][2][0] == self._VOCAB
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

    def test_enter_on_correct_slot_advances_focus(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["λύω", ""], submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_verb_slot", return_value=True), \
             patch.object(gu, "check_verb_test", return_value=(False, "")):
            self._call(gu, state, cv, form, self._meta())
        assert form.widget.focus_request == {"request_id": 1, "advance_to": 1}

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
        assert state["words"][2][0] == self._VOCAB
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

    def test_active_cases_attribute_set(self, gu):
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
        # regular and sg cells are included.
        class _NounBackend:
            def paradigm(self, word, pos):
                # noun paradigm layout: {gender: {num: {case: set}}}
                return {"masc": {"sg": {"nom": {word}, "acc": {word}, "gen": {word}, "dat": {word}},
                                 "pl": {"nom": {word}, "acc": {word}, "gen": {word}, "dat": {word}}}}
        gu = GreekUtils(_NounBackend(), _RichMo())
        mg_word = {"Word": "λόγος", "Translation": "word"}
        _, _, form = gu.create_noun_test_ui([mg_word], mode='full')
        labels = [t.label for t in form]
        assert any("Def." in l for l in labels)
        assert any("Ind." in l for l in labels)

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
        assert gu.adjective_slot_labels("simple")[0] == "Masc Sg:"

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
        assert labels[0] == "Masc Sg:"
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

@pytest.mark.parametrize("esm", [_DIA_ESM_TMPL, _PARA_ESM], ids=["dia", "para"])
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


class TestDiacriticsElement:
    def _fake_ui(self, val="text", enter_pressed=0):
        class _W:
            value = val
        _W.enter_pressed = enter_pressed
        class _UI:
            widget = _W()
            def _mime_(self): return ("text/html", "<div/>")
        return _UI()

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

    def test_homer_words_defaults_empty_list_when_none(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set())
        assert w.homer_words == []

    def test_homer_words_stored_as_list_not_set(self):
        w = interactive_text(self._mo(), lines=["ἄνδρα"], clickable=set(), homer_words={"ανδρα", "μοι"})
        assert isinstance(w.homer_words, list)
        assert set(w.homer_words) == {"ανδρα", "μοι"}

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
        form, md = gu.create_adjective_test_ui([self._WORD], [], self._WORD)
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
        ok, fb = gu.check_adjective_test(self._WORD, form)
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


# ──────────────────────────────── create_pronoun_test_ui ──

class TestCreatePronounTestUi:
    _WORD = {"Word": "κανένας", "Translation": "no one/any"}

    @pytest.fixture
    def gu(self):
        return GreekUtils(_StubBackend(), _RichMo(), config=ANCIENT_GREEK)

    def test_no_current_pron_returns_none_form(self, gu):
        form, md = gu.create_pronoun_test_ui([], [], None)
        assert form is None

    def test_basic_form_created(self, gu):
        form, md = gu.create_pronoun_test_ui([self._WORD], [self._WORD], self._WORD)
        assert form is not None
        assert form.pron_word == "κανένας"
        assert form.pron_mode == "simple"

    def test_full_mode_more_inputs(self, gu):
        form_s, _ = gu.create_pronoun_test_ui([self._WORD], [self._WORD], self._WORD, mode="simple")
        form_f, _ = gu.create_pronoun_test_ui([self._WORD], [self._WORD], self._WORD, mode="full")
        assert len(form_f.value) > len(form_s.value)

    def test_singular_only_word_gets_three_fields_not_six(self):
        # The exact user-reported case: κανένας must show only its 3 real
        # (singular) fields, not all 6 with 3 destined to fail with "?".
        def _paradigm_fn(word, pos):
            if pos != "pronoun":
                return {}
            return {"sg": {"masc": {"nom": {"κανένας"}}, "fem": {"nom": {"καμία"}}, "neut": {"nom": {"κανένα"}}}}
        gu = GreekUtils(_StubBackend(_paradigm_fn), _RichMo(), config=ANCIENT_GREEK)
        form, _ = gu.create_pronoun_test_ui([self._WORD], [self._WORD], self._WORD)
        assert len(form.value) == 3
        assert len(form.active_slots) == 3

    def test_empty_words4test_shows_empty_message(self, gu):
        form, md = gu.create_pronoun_test_ui([self._WORD], [], self._WORD)
        assert form is not None
        assert "empty" in md.lower()

    def test_words4test_md_contains_translation(self, gu):
        _, md = gu.create_pronoun_test_ui([self._WORD], [self._WORD], self._WORD)
        assert "no one/any" in md


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
        ok, fb = gu.check_pronoun_test(self._WORD, form)
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
        assert state["words"][2][0] == self._VOCAB
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

    def test_enter_on_correct_slot_advances_focus(self, gu):
        cv = self._VOCAB[0]
        state = self._state()
        form = _pdform(["καλός"] + [""] * 5, submit_count=1, enter_field_index=0)
        with patch.object(gu, "check_adjective_slot", return_value=True), \
             patch.object(gu, "check_adjective_test", return_value=(False, "")):
            self._call(gu, state, cv, form)
        assert form.widget.focus_request == {"request_id": 1, "advance_to": 1}

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


# ──────────────────────────────── GreekUtils.diacritics_text method ──

class TestGreekUtilsDiacriticsTextMethod:
    def test_delegates_to_module_function(self, gu_form):
        with patch("eee_project.notebook_utils.diacritics_text", return_value="widget") as mock_fn:
            result = gu_form.diacritics_text(placeholder="test", label="lbl", value="v")
        assert result == "widget"
        mock_fn.assert_called_once()


# ──────────────────────────────── build_grc_paradigm_table with data ──

class _SlotTag:
    def __init__(self, tag):
        self.tag = tag

class _GrcNounBackend:
    def get_slot_templates(self, lang, pos, terms_lang="en"):
        if pos == "noun":
            return [_SlotTag(f".{c}{n}M") for c in "NGDAV" for n in "SP"]
        return []

class _GrcVerbBackend:
    _PS = ["1S", "2S", "3S", "1P", "2P", "3P"]
    def get_slot_templates(self, lang, pos, terms_lang="en"):
        if pos == "verb":
            slots = [_SlotTag(f"{t}.{ps}") for t in ["PAI","IAI","AAI","AMI","API","XAI","YAI"] for ps in self._PS]
            slots += [_SlotTag("PAN"), _SlotTag("PAD.2S"), _SlotTag("PAD.2P"),
                      _SlotTag("AAD.2S"), _SlotTag("AMD.2S")]
            # dual -- only for the tense/voice combos the real engine supports
            slots += [_SlotTag(f"{t}.{ps}") for t in ["PAI","IAI","FAI","XAI"] for ps in ("2D", "3D")]
            slots += [_SlotTag("PAD.2D")]
            return slots
        return []

class _GrcAdjBackend:
    def get_slot_templates(self, lang, pos, terms_lang="en"):
        if pos == "adjective":
            return [_SlotTag(f".{c}{n}M") for c in "NGDA" for n in "SP"]
        return []

class _GrcPronDemBackend:
    """Adjective-shaped pronoun family (demonstrative/relative/interrogative/
    indefinite/reciprocal) -- same Case+Number+Gender tag shape _GrcAdjBackend
    uses, returned for pos == "pronoun" instead of "adjective". Matches
    section-05's ag_pron_key/pronoun-tags.tsv shape (dotted, undotted-inside).
    Includes Dual ("D") in the number axis, unlike _GrcAdjBackend -- caught
    in code review: pronoun-tags.tsv has real Dual rows for this family
    (adj-tags.tsv has none), so a Sing/Plur-only stub would never exercise
    the dual-column code path at all."""
    def get_slot_templates(self, lang, pos, terms_lang="en"):
        if pos == "pronoun":
            return [_SlotTag(f".{c}{n}M") for c in "NGDA" for n in "SPD"]
        return []

class _GrcPronPrsBackend:
    """Personal-pronoun family (ἐγώ/σύ) -- Case x Number(incl. Dual) x
    Person, no Gender. Tag shape confirmed against section-05's
    ag_pron_key: dotted, Case+Number+Person, e.g. ".NS1", ".ND1"."""
    def get_slot_templates(self, lang, pos, terms_lang="en"):
        if pos == "pronoun":
            return [_SlotTag(f".{c}{n}{p}") for c in "NGDA" for n in "SDP" for p in "12"]
        return []

class _GrcUmNounBackend:
    def get_slot_templates(self, lang, pos, terms_lang="en"):
        if pos == "noun":
            return [_SlotTag(f"N;{c};{ns}") for c in ["NOM","GEN","DAT","ACC","VOC"] for ns in ["SG","PL"]]
        return []


class TestBuildGrcParadigmTableWithData:
    @pytest.fixture
    def fn(self):
        return build_grc_paradigm_table(_GrcNounBackend(), _EmptyGrcBackend())

    def test_noun_with_ag_data_returns_html(self, fn):
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "θεος", "pos": "noun", "form": "θεος"})
        assert result is not None
        assert "θεος" in result
        assert "отсутствует" not in result

    def test_noun_form_not_found_adds_note(self, fn):
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "θεος", "pos": "noun", "form": "θεον"})
        assert result is not None
        assert "отсутствует" in result

    def test_noun_no_forms_returns_none(self, fn):
        with patch("eee_project.inflect_slot", return_value=set()):
            result = fn({"lemma": "θεος", "pos": "noun", "form": "θεος"})
        assert result is None

    def test_missing_lemma_falls_back_to_form(self, fn):
        """Flat-vocab word dicts (load_vocab_tsv) have no lemma key."""
        def fake_inflect(word, slot, pos, *, language, backend):
            assert word == "θεος"  # falls back to form, not KeyError
            return {"θεος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"pos": "noun", "form": "θεος"})
        assert result is not None
        assert "θεος" in result

    def test_noun_unimorph_fallback(self):
        fn = build_grc_paradigm_table(_EmptyGrcBackend(), _GrcUmNounBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == "N;NOM;SG" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "θεος", "pos": "noun", "form": "θεος"})
        assert result is not None

    def test_verb_with_data_returns_html(self):
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"λυω"} if slot.tag == "PAI.1S" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "λυω", "pos": "verb", "form": "λυω"})
        assert result is not None
        assert "table" in result

    def test_verb_infinitive_row(self):
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            if slot.tag == "PAI.1S": return {"λυω"}
            if slot.tag == "PAN": return {"λυειν"}
            return set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "λυω", "pos": "verb", "form": "λυω"})
        assert result is not None
        assert "Инф." in result

    def test_verb_imperative_row(self):
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            if slot.tag == "PAI.1S": return {"λυω"}
            if slot.tag == "PAD.2S": return {"λυε"}
            return set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "λυω", "pos": "verb", "form": "λυω"})
        assert result is not None
        assert "Пов." in result

    def test_verb_perfect_tense_column(self):
        """XAI (perfect active indicative) must render as its own column,
        labelled "Перф." -- added alongside the byzantine lexicon (both of
        whose entries are perfect-tense-only), which would otherwise have no
        way to ever surface in this table despite being correctly generated
        by the backend."""
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"εγνωκαν"} if slot.tag == "XAI.3P" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "γιγνωσκω", "pos": "verb", "form": "εγνωκαν"})
        assert result is not None
        assert "Перф." in result
        assert "εγνωκαν" in result
        assert "отсутствует" not in result

    def test_verb_pluperfect_tense_column(self):
        """YAI (pluperfect active indicative) must render as its own
        column, labelled "Плюскв." -- same fix shape as XAI/perfect above:
        odyssey_morpheus_verbs_lexicon's ἄνωγα/ὄρνυμι forms: overrides were
        already correct but had no column to ever surface in (2026-07-27)."""
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"ηνωγεα"} if slot.tag == "YAI.1S" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "ανωγα", "pos": "verb", "form": "ηνωγεα"})
        assert result is not None
        assert "Плюскв." in result
        assert "ηνωγεα" in result
        assert "отсутствует" not in result

    def test_verb_no_perfect_data_omits_column(self):
        """A verb with only present-tense data must not show an empty
        Перф. column -- tenses are only included when at least one cell in
        them has data (pre-existing behavior, unchanged by adding XAI)."""
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"λυω"} if slot.tag == "PAI.1S" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "λυω", "pos": "verb", "form": "λυω"})
        assert result is not None
        assert "Перф." not in result

    def test_verb_no_pluperfect_data_omits_column(self):
        """Same negative case as no_perfect_data_omits_column, for YAI."""
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"λυω"} if slot.tag == "PAI.1S" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "λυω", "pos": "verb", "form": "λυω"})
        assert result is not None
        assert "Плюскв." not in result

    def test_verb_dual_row(self):
        """2D/3D rows render for tenses the engine supports (Pres/Imp/Fut/
        Perf Act Ind + Pres Act Imp), labelled '2 дв.'/'3 дв.'."""
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            if slot.tag == "PAI.1S": return {"λυω"}
            if slot.tag == "PAI.2D": return {"λυετον"}
            return set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "λυω", "pos": "verb", "form": "λυω"})
        assert result is not None
        assert "2 дв." in result
        assert "λυετον" in result

    def test_verb_no_dual_data_omits_row_content_but_keeps_label(self):
        """A verb with no dual data anywhere still shows the 2 дв./3 дв.
        rows (unlike whole tenses, dual is a row within an already-shown
        tense, so it can't be hidden the same way) -- but every cell in
        them is correctly '—', not an error or missing row."""
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"λυω"} if slot.tag == "PAI.1S" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "λυω", "pos": "verb", "form": "λυω"})
        assert result is not None
        assert "2 дв." in result

    def test_adj_with_data_returns_html(self):
        fn = build_grc_paradigm_table(_GrcAdjBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"καλος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "καλος", "pos": "adj", "form": "καλος"})
        assert result is not None
        assert "καλος" in result

    def test_adj_no_forms_returns_none(self):
        fn = build_grc_paradigm_table(_GrcAdjBackend(), _EmptyGrcBackend())
        with patch("eee_project.inflect_slot", return_value=set()):
            result = fn({"lemma": "καλος", "pos": "adj", "form": "καλον"})
        assert result is None

    def test_pronoun_demonstrative_with_data_returns_html(self):
        """Adjective-shaped pronoun family (e.g. οὗτος) with data returns
        HTML containing the expected forms, via _collect_rows/_case_table --
        mirrors test_adj_with_data_returns_html exactly, pos="pronoun"."""
        fn = build_grc_paradigm_table(_GrcPronDemBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"ουτος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "οὗτος", "pos": "pronoun", "form": "ουτος"})
        assert result is not None
        assert "ουτος" in result

    def test_pronoun_demonstrative_dual_column_renders(self):
        """Regression guard for a real bug found in code review: the
        adjective-shaped pronoun family (demonstrative/relative/
        interrogative/indefinite/reciprocal) genuinely has Dual forms in
        pronoun-tags.tsv (unlike regular adjectives, whose tag table has
        no Dual rows at all) -- an earlier version of this branch reused
        _collect_rows/_case_table's Sing/Plur-only default unmodified,
        silently making every pronoun dual cell structurally unreachable
        even though the underlying lexicon data was correct and present.
        Asserts the dual column's own label text appears (mirroring
        test_verb_dual_row's style), not just a generic "—" placeholder
        that would pass regardless of whether the column exists at all."""
        fn = build_grc_paradigm_table(_GrcPronDemBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            if slot.tag == ".NSM": return {"ουτος"}
            if slot.tag == ".NDM": return {"τουτω"}
            return set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "οὗτος", "pos": "pronoun", "form": "ουτος"})
        assert result is not None
        assert "Дв." in result
        assert "τουτω" in result

    def test_pronoun_demonstrative_no_forms_returns_none(self):
        """Mirrors test_adj_no_forms_returns_none, pos="pronoun"."""
        fn = build_grc_paradigm_table(_GrcPronDemBackend(), _EmptyGrcBackend())
        with patch("eee_project.inflect_slot", return_value=set()):
            result = fn({"lemma": "οὗτος", "pos": "pronoun", "form": "τουτο"})
        assert result is None

    def test_pronoun_personal_with_data_returns_html(self):
        """Personal-pronoun family (e.g. ἐγώ) with data returns HTML
        containing the expected forms."""
        fn = build_grc_paradigm_table(_GrcPronPrsBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"εγω"} if slot.tag == ".NS1" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "ἐγώ", "pos": "pronoun", "form": "εγω"})
        assert result is not None
        assert "εγω" in result

    def test_pronoun_personal_dual_row(self):
        """A personal pronoun's dual forms (νώ/νῷν for ἐγώ, σφώ/σφῷν for σύ)
        render in the table when present -- mirrors test_verb_dual_row, but
        this family's dual is 1st/2nd person (there is no 3rd-person
        personal pronoun in scope -- that's αὐτός, out of scope), unlike
        verb dual which is 2nd/3rd person."""
        fn = build_grc_paradigm_table(_GrcPronPrsBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            if slot.tag == ".NS1": return {"εγω"}
            if slot.tag == ".ND1": return {"νω"}
            return set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "ἐγώ", "pos": "pronoun", "form": "εγω"})
        assert result is not None
        assert "νω" in result

    def test_pronoun_personal_no_dual_data_still_shows_row(self):
        """Mirrors test_verb_no_dual_data_omits_row_content_but_keeps_label:
        a personal pronoun with no dual data anywhere still renders its
        dual row/column (with "—" placeholders), not omitted entirely.
        Asserts the dual column's own label text (1 дв.), not just a bare
        "—" -- caught in code review: a plain chr(8212)-in-result check
        would pass identically even if the dual columns were removed
        entirely, since 23 of the 24 non-dual cells are also "—" in this
        fixture."""
        fn = build_grc_paradigm_table(_GrcPronPrsBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"εγω"} if slot.tag == ".NS1" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "ἐγώ", "pos": "pronoun", "form": "εγω"})
        assert result is not None
        assert "1 дв." in result
        assert "2 дв." in result

    def test_pronoun_no_forms_returns_none(self):
        """pos="pronoun" with a backend that has zero pronoun slot data
        returns None -- same pattern as every other "no data" test in this
        class."""
        fn = build_grc_paradigm_table(_EmptyGrcBackend(), _EmptyGrcBackend())
        result = fn({"lemma": "τις", "pos": "pronoun", "form": "τις"})
        assert result is None


# ──────────────────────────────── build_grc_lexicon_tabs with data ──

class TestBuildGrcLexiconTabsWithData:
    def test_no_available_no_um_data_returns_none(self):
        fn = build_grc_lexicon_tabs(_EmptyGrcBackend(), _EmptyGrcBackend(),
                                     lexicons={"homer": _EmptyGrcBackend()})
        w = {"lemma": "δε", "pos": "particle", "form": "δε", "lexicon_tag": ""}
        assert fn(w) is None

    def test_unimorph_header_when_um_has_data(self):
        fn = build_grc_lexicon_tabs(_EmptyGrcBackend(), _GrcUmNounBackend(),
                                     lexicons={"homer": _EmptyGrcBackend()})
        w = {"lemma": "θεος", "pos": "noun", "form": "θεος", "lexicon_tag": ""}
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == "N;NOM;SG" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn(w)
        assert result is not None
        assert "unimorph" in result

    def test_modern_rung_preserved_after_unimorph_confirms_form(self):
        # Companion to TestModernRung's "no Modern-only table" regression: when
        # the unimorph fallback DOES confirm the exact form (ancient
        # confirmation exists, just not via a curated lexicon), the Modern rung
        # is still appended alongside it -- only a TOTAL absence of ancient
        # confirmation (neither curated lexicon nor unimorph) hides Modern too.
        class _StubModernBackend:
            def get_slot_templates(self, lang, pos, terms):
                class _Slot:
                    tag, tag_type = "Nom|Sing|Masc", "ud"
                    features = {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}
                return [_Slot()] if pos == "noun" else []

        fn = build_grc_lexicon_tabs(_EmptyGrcBackend(), _GrcUmNounBackend(),
                                     lexicons={"homer": _EmptyGrcBackend()},
                                     el_backend=_StubModernBackend())
        w = {"lemma": "θεος", "pos": "noun", "form": "θεος", "lexicon_tag": ""}

        # build_modern_paradigm_table routes inflection through the SAME shared
        # eee_project.inflect_slot dispatcher as the ancient/unimorph side (it
        # does not call the backend's .inflect() directly) -- one mock must
        # recognize both tag shapes, or patching it for the unimorph case
        # silently starves the Modern slot too.
        def fake_inflect(word, slot, pos, *, language, backend):
            if slot.tag == "N;NOM;SG":
                return {"θεος"}
            if slot.tag == "Nom|Sing|Masc":
                return {"θεος"}
            return set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn(w)
        assert result is not None
        assert "unimorph" in result
        assert "Modern Greek" in result

    def test_single_lexicon_shows_header(self):
        ag = _GrcNounBackend()
        fn = build_grc_lexicon_tabs(ag, _EmptyGrcBackend(), lexicons={"homer": ag})
        w = {"lemma": "θεος", "pos": "noun", "form": "θεος", "lexicon_tag": '"homer"'}
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn(w)
        assert result is not None
        assert "homer" in result

    def test_multi_lexicon_shows_tabs(self):
        ag = _GrcNounBackend()
        fn = build_grc_lexicon_tabs(ag, _EmptyGrcBackend(),
                                     lexicons={"homer": ag, "lxx": ag})
        w = {"lemma": "θεος", "pos": "noun", "form": "θεος",
             "lexicon_tag": '"homer","lxx"'}
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn(w)
        assert result is not None
        assert "radio" in result or "style" in result

    def test_first_tab_defaults_to_visible_not_hidden(self):
        """Regression: re-rendering to a new word with FEWER tabs than the
        previous one's live DOM can strip every radio's checked state (the
        browser's own DOM patching preserves live checked/unchecked state
        by tree position across same-shaped renders; a checked radio at a
        position the new render doesn't have has nowhere to land).
        Confirmed live via Playwright against a real browser: selecting a
        later tab for one word, then clicking a word with fewer tabs, left
        zero radios checked and zero panels visible. The first tab's
        panel/caption/summary-label must default to visible (not
        hidden-until-:checked) so losing the checked state entirely still
        shows something sane instead of a blank switcher."""
        ag = _GrcNounBackend()
        fn = build_grc_lexicon_tabs(ag, _EmptyGrcBackend(),
                                     lexicons={"homer": ag, "lxx": ag})
        w = {"lemma": "θεος", "pos": "noun", "form": "θεος",
             "lexicon_tag": '"homer","lxx"'}
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn(w)
        assert result is not None

        uid = abs(hash(w["lemma"] + w["form"])) % 99999
        initial_hide_block = result.split("{display:none}")[0]
        # "homer" (dict-insertion first) must NOT be in the unconditional
        # hide-all rule -- it defaults to visible.
        assert f"#lp-{uid}-homer" not in initial_hide_block
        # "lxx" (the other tab) still defaults to hidden, as before.
        assert f"#lp-{uid}-lxx" in initial_hide_block
        # A rule must hide "homer" specifically when "lxx" is genuinely checked.
        assert f"#lr-{uid}-lxx:checked~#lp-{uid}-homer{{display:none}}" in result

    def test_multi_lexicon_one_table_falls_back(self):
        ag = _GrcNounBackend()
        empty = _EmptyGrcBackend()
        fn = build_grc_lexicon_tabs(ag, empty,
                                     lexicons={"homer": ag, "lxx": empty})
        w = {"lemma": "θεος", "pos": "noun", "form": "θεος",
             "lexicon_tag": '"homer","lxx"'}
        def fake_inflect(word, slot, pos, *, language, backend):
            if backend is ag and slot.tag == ".NSM":
                return {"θεος"}
            return set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn(w)
        # Only one table produced → falls back to single-table path
        assert result is not None


# ──────────────────────── filter_grc_quiz_words / grc_coverage_words ──
# Extracted from identical boilerplate duplicated across all 3 Odyssey
# lesson notebooks (_has_displayable_form/_in_homer and
# _words_for_coverage/_norm_f pairs).

class _FakeAgHomer:
    """get_slot_templates always returns one non-empty slot."""
    def get_slot_templates(self, lang, pos, terms_lang="en"):
        return [_SlotTag(".NSM")]


class _EmptyAgHomer:
    """get_slot_templates always returns no slots (word not quizzable)."""
    def get_slot_templates(self, lang, pos, terms_lang="en"):
        return []


class _FakeEee:
    """inflect_slot returns forms only for lemmas in _homeric_lemmas."""
    def __init__(self, homeric_lemmas):
        self._homeric_lemmas = homeric_lemmas

    def inflect_slot(self, lemma, slot, pos, *, language, backend):
        return {lemma} if lemma in self._homeric_lemmas else set()


def _fake_build_paradigm_table(displayable_forms):
    """Returns a build_paradigm_table(w) stub: w["form"] in the set → some
    HTML without #f97316; otherwise HTML with #f97316 (irregular), or None
    when hide_if_absent=True (the homer-mode "form present in this backend" probe)."""
    def _fn(w, *, _backend=None, hide_if_absent=False, **_kw):
        if w["form"] in displayable_forms:
            return f"<table>{w['form']}</table>"
        if hide_if_absent:
            return None
        return f"<table>{w['form']}<span style='color:#f97316'>irregular</span></table>"
    return _fn


class TestFilterGrcQuizWords:
    def test_mode_none_returns_all_unfiltered(self):
        words = [{"form": "α", "lemma": "α", "pos": "noun"},
                 {"form": "β", "lemma": "β", "pos": "verb"}]
        result = filter_grc_quiz_words(
            words, "none", build_paradigm_table=_fake_build_paradigm_table(set()),
            lexicons={"homer": object()},
        )
        assert result == words

    def test_homer_mode_keeps_only_homeric_words(self):
        words = [{"form": "α", "lemma": "λέγω", "pos": "verb"},
                 {"form": "β", "lemma": "ἄγνωστος", "pos": "verb"}]
        result = filter_grc_quiz_words(
            words, "homer", build_paradigm_table=_fake_build_paradigm_table({"α"}),
            lexicons={"homer": object()},
        )
        assert result == [words[0]]

    def test_homer_mode_excludes_homeric_but_non_displayable_form(self):
        """Homeric-attested lemma, but the tested surface form itself is not
        highlighted in the rendered paradigm (e.g. an epic variant the
        backend doesn't generate) — must not be quizzable under "homer"."""
        words = [{"form": "ὤλονθ'", "lemma": "ὄλλυμι", "pos": "verb"}]
        result = filter_grc_quiz_words(
            words, "homer", build_paradigm_table=_fake_build_paradigm_table(set()),
            lexicons={"homer": object()},
        )
        assert result == []

    def test_homer_mode_no_slots_excludes_word(self):
        words = [{"form": "α", "lemma": "λέγω", "pos": "verb"}]
        result = filter_grc_quiz_words(
            words, "homer", build_paradigm_table=_fake_build_paradigm_table(set()),
            lexicons={"homer": object()},
        )
        assert result == []

    def test_default_mode_keeps_only_displayable_forms(self):
        words = [{"form": "λέγω", "lemma": "λέγω", "pos": "verb"},
                 {"form": "ἴδεν", "lemma": "ὁράω", "pos": "verb"}]
        result = filter_grc_quiz_words(
            words, "current", build_paradigm_table=_fake_build_paradigm_table({"λέγω"}),
            lexicons={"homer": object()},
        )
        assert result == [words[0]]

    def test_default_mode_paradigm_table_exception_excludes_word(self):
        words = [{"form": "λέγω", "lemma": "λέγω", "pos": "verb"}]
        def _raises(w):
            raise ValueError("boom")
        result = filter_grc_quiz_words(
            words, "current", build_paradigm_table=_raises,
            lexicons={"homer": object()},
        )
        assert result == []

    def test_homer_mode_paradigm_exception_excludes_word(self):
        def _raises(w, **kw):
            raise ValueError("boom")
        words = [{"form": "λέγω", "lemma": "λέγω", "pos": "verb"}]
        result = filter_grc_quiz_words(
            words, "homer", build_paradigm_table=_raises,
            lexicons={"homer": object()},
        )
        assert result == []

    def test_default_mode_none_result_excludes_word(self):
        words = [{"form": "λέγω", "lemma": "λέγω", "pos": "verb"}]
        result = filter_grc_quiz_words(
            words, "current", build_paradigm_table=lambda w: None,
            lexicons={"homer": object()},
        )
        assert result == []


class TestGrcCoverageWords:
    def test_mode_none_python_returns_empty_set(self):
        words = [{"form": "λέγω", "lemma": "λέγω", "pos": "verb"}]
        result = grc_coverage_words(
            words, None, build_paradigm_table=_fake_build_paradigm_table(set()),
            lexicons={"homer": object()},
        )
        assert result == set()

    def test_mode_str_none_returns_every_normalized_form(self):
        words = [{"form": "λέγω", "lemma": "λέγω", "pos": "verb"},
                 {"form": "θεός", "lemma": "θεός", "pos": "noun"}]
        result = grc_coverage_words(
            words, "none", build_paradigm_table=_fake_build_paradigm_table(set()),
            lexicons={"homer": object()},
        )
        assert result == {"λεγω", "θεος"}

    def test_homer_mode_filters_to_homeric_forms(self):
        words = [{"form": "λέγω", "lemma": "λέγω", "pos": "verb"},
                 {"form": "ἄγνωστος", "lemma": "ἄγνωστος", "pos": "verb"}]
        result = grc_coverage_words(
            words, "homer", build_paradigm_table=_fake_build_paradigm_table({"λέγω"}),
            lexicons={"homer": object()},
        )
        assert result == {"λεγω"}

    def test_homer_mode_excludes_homeric_but_non_displayable_form(self):
        words = [{"form": "ὤλονθ'", "lemma": "ὄλλυμι", "pos": "verb"}]
        result = grc_coverage_words(
            words, "homer", build_paradigm_table=_fake_build_paradigm_table(set()),
            lexicons={"homer": object()},
        )
        assert result == set()

    def test_default_mode_filters_to_displayable_forms(self):
        words = [{"form": "λέγω", "lemma": "λέγω", "pos": "verb"},
                 {"form": "ἴδεν", "lemma": "ὁράω", "pos": "verb"}]
        result = grc_coverage_words(
            words, "current", build_paradigm_table=_fake_build_paradigm_table({"λέγω"}),
            lexicons={"homer": object()},
        )
        assert result == {"λεγω"}

    def test_normalization_strips_accents_and_elision(self):
        words = [{"form": "πότνι᾽", "lemma": "πότνια", "pos": "noun"}]
        result = grc_coverage_words(
            words, "none", build_paradigm_table=_fake_build_paradigm_table(set()),
            lexicons={"homer": object()},
        )
        assert result == {"ποτνι"}


class _FakeParadigmBackend:
    """paradigm(lemma, pos) returns a fixed {tag: {forms}} dict for one lemma/pos,
    or raises if `raises` is set — mirrors AncientGreekBackend.paradigm()'s shape."""
    def __init__(self, table=None, *, raises=False):
        self._table = table or {}
        self._raises = raises

    def paradigm(self, lemma, pos):
        if self._raises:
            raise ValueError("boom")
        return self._table.get((lemma, pos), {})


class TestGrcLexiconSources:
    """Extracted from _lexicon_tag, duplicated identically across all 7 Odyssey
    lesson notebooks (each with its own hand-maintained _LEXICONS list and an
    exact-string match blind to case/accent/movable-nu variation)."""

    def test_non_lexicon_tag_pos_returns_empty(self):
        w = {"lemma": "καλός", "form": "καλός", "pos": "adv"}
        result = grc_lexicon_sources(w, lexicons={"homer": _FakeParadigmBackend()})
        assert result == []

    def test_matches_single_lexicon(self):
        w = {"lemma": "λόγος", "form": "λόγος", "pos": "noun"}
        backend = _FakeParadigmBackend({("λόγος", "noun"): {".NSM": {"λόγος"}}})
        result = grc_lexicon_sources(w, lexicons={"homer": backend})
        assert result == ["homer"]

    def test_no_match_anywhere_returns_empty(self):
        w = {"lemma": "λόγος", "form": "λόγος", "pos": "noun"}
        backend = _FakeParadigmBackend({("λόγος", "noun"): {".NSM": {"ἄλλος"}}})
        result = grc_lexicon_sources(w, lexicons={"homer": backend})
        assert result == []

    def test_sorted_names_across_multiple_matching_lexicons(self):
        w = {"lemma": "λόγος", "form": "λόγος", "pos": "noun"}
        backend = _FakeParadigmBackend({("λόγος", "noun"): {".NSM": {"λόγος"}}})
        result = grc_lexicon_sources(
            w, lexicons={"morphgnt": backend, "homer": backend, "lsj": backend},
        )
        assert result == ["homer", "lsj", "morphgnt"]

    def test_only_matching_lexicons_included(self):
        w = {"lemma": "λόγος", "form": "λόγος", "pos": "noun"}
        hit = _FakeParadigmBackend({("λόγος", "noun"): {".NSM": {"λόγος"}}})
        miss = _FakeParadigmBackend({("λόγος", "noun"): {".NSM": {"ἄλλος"}}})
        result = grc_lexicon_sources(w, lexicons={"homer": hit, "lsj": miss})
        assert result == ["homer"]

    def test_case_insensitive_match(self):
        """Sentence-initial capital in running text (e.g. Ἄνδρα) vs. the
        lowercase form every backend actually generates."""
        w = {"lemma": "ἀνήρ", "form": "Ἄνδρα", "pos": "noun"}
        backend = _FakeParadigmBackend({("ἀνήρ", "noun"): {".ASM": {"ἄνδρα"}}})
        result = grc_lexicon_sources(w, lexicons={"homer": backend})
        assert result == ["homer"]

    def test_accent_insensitive_match(self):
        """Grave-for-acute accent shift in connected running text (θεοὶ) vs.
        the citation-form acute every backend generates (θεοί)."""
        w = {"lemma": "θεός", "form": "θεοὶ", "pos": "noun"}
        backend = _FakeParadigmBackend({("θεός", "noun"): {".NPM": {"θεοί"}}})
        result = grc_lexicon_sources(w, lexicons={"homer": backend})
        assert result == ["homer"]

    def test_movable_nu_insensitive_match(self):
        w = {"lemma": "ἀληθής", "form": "ἀληθέσιν", "pos": "adj"}
        backend = _FakeParadigmBackend({("ἀληθής", "adjective"): {".DPN": {"ἀληθέσι(ν)"}}})
        result = grc_lexicon_sources(w, lexicons={"homer": backend})
        assert result == ["homer"]

    def test_adj_pos_aliased_to_adjective_for_paradigm_call(self):
        w = {"lemma": "καλός", "form": "καλός", "pos": "adj"}
        backend = _FakeParadigmBackend({("καλός", "adjective"): {".NSM": {"καλός"}}})
        result = grc_lexicon_sources(w, lexicons={"homer": backend})
        assert result == ["homer"]

    def test_paradigm_exception_excludes_that_lexicon_only(self):
        w = {"lemma": "λόγος", "form": "λόγος", "pos": "noun"}
        ok = _FakeParadigmBackend({("λόγος", "noun"): {".NSM": {"λόγος"}}})
        broken = _FakeParadigmBackend(raises=True)
        result = grc_lexicon_sources(w, lexicons={"homer": ok, "lsj": broken})
        assert result == ["homer"]

    def test_participle_form_matches(self):
        """Unlike build_grc_paradigm_table's study-table view (indicative/
        infinitive/imperative only), grc_lexicon_sources checks the full
        paradigm() result, including participle cells."""
        w = {"lemma": "φεύγω", "form": "πεφευγότες", "pos": "verb"}
        backend = _FakeParadigmBackend({("φεύγω", "verb"): {"XAP.NPM": {"πεφευγότες"}}})
        result = grc_lexicon_sources(w, lexicons={"homer": backend})
        assert result == ["homer"]


class TestNormGrcSurface:
    """norm_grc_surface: made public (was _norm_grc_surface) for section-03 of the
    odyssey interactive-text project — the panel needs to normalize a single
    clicked surface form the same way grc_coverage_words normalizes the vocab."""

    def test_public_api(self):
        import eee_project as eee
        assert hasattr(eee, "norm_grc_surface")
        assert callable(eee.norm_grc_surface)

    def test_case_preserved(self):
        assert norm_grc_surface("Ἄνδρα") == "Ανδρα"

    def test_strips_trailing_comma(self):
        assert norm_grc_surface("ἔννεπε,") == "εννεπε"


class TestResolveClickedWord:
    """resolve_clicked_word: exact-then-normalized lookup for the interactive-text
    panel. Regression for a real bug found live: a plain
    {norm_grc_surface(form): w} dict silently collided ὅ ("which", I.3-4 vocab)
    with ὁ ("his", I.9 vocab) -- both normalize to "ο" once breathing marks are
    stripped -- so clicking one showed the other's gloss and paradigm
    (odyssey interactive-text, section 03)."""

    _WORDS = [
        {"form": "ὅ", "lemma": "ὅς", "meaning": "которое, что"},
        {"form": "οἳ", "lemma": "ὅς", "meaning": "которые"},
        {"form": "ὁ", "lemma": "ὅς", "meaning": "их"},
        {"form": "οἱ", "lemma": "αὐτός", "meaning": "ему"},
    ]

    def test_public_api(self):
        import eee_project as eee
        assert hasattr(eee, "resolve_clicked_word")
        assert callable(eee.resolve_clicked_word)

    def test_empty_selection_returns_none(self):
        assert resolve_clicked_word(self._WORDS, "") is None

    def test_lookup_miss_returns_none(self):
        assert resolve_clicked_word(self._WORDS, "οὐδέποτε") is None

    def test_breathing_mark_pairs_resolve_to_the_distinct_correct_entry(self):
        # The confirmed real collision: exact matching must distinguish all four,
        # even though all four collapse to just two norm_grc_surface keys ("ο", "οι").
        assert resolve_clicked_word(self._WORDS, "ὅ")["meaning"] == "которое, что"
        assert resolve_clicked_word(self._WORDS, "ὁ")["meaning"] == "их"
        assert resolve_clicked_word(self._WORDS, "οἳ")["meaning"] == "которые"
        assert resolve_clicked_word(self._WORDS, "οἱ")["meaning"] == "ему"

    def test_normalized_fallback_used_only_when_exact_match_absent(self):
        # A sentence-position accent variant not present verbatim in words_raw
        # still resolves via the normalized fallback.
        words = [{"form": "τις", "lemma": "τις", "meaning": "some"}]
        assert resolve_clicked_word(words, "τίς")["meaning"] == "some"

    def test_missing_form_key_does_not_raise(self):
        words = [{"lemma": "x", "meaning": "y"}]  # no "form" key
        assert resolve_clicked_word(words, "ανδρα") is None


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


class TestStanzaMatchWidgets:
    def test_no_cv_placeholder_radio(self, gu_form):
        radio, _, _ = gu_form.stanza_match_widgets(cv=None, remaining=[], stanzas=_SM_STANZAS)
        assert radio.options == [""]

    def test_cv_gives_multiple_options(self, gu_form):
        radio, _, _ = gu_form.stanza_match_widgets(cv=_SM_STANZAS[0], remaining=_SM_STANZAS[1:], stanzas=_SM_STANZAS)
        assert len(radio.options) > 1

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
              direction="grc_to_tr", lang="ru", renew_btn=None):
        cv_g, cv_s, _, rem_g, rem_s, _, sc_g, sc_s, _, rst_g, rst_s, hist_g, hist_s, _, fut_g, fut_s = state
        return gu.stanza_match_form(
            cv_g, cv_s, rem_g, rem_s, sc_g, sc_s, rst_g, rst_s,
            hist_g, hist_s, fut_g, fut_s,
            radio or _FakeRadio(), _FakeBtn(next_v), _FakeBtn(prev_v),
            stanzas=stanzas or _SM_STANZAS,
            direction=direction,
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

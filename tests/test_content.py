"""Tests for eee_project.content -- functions relocated here from
notebook_utils.py (see that module's own docstring for the shared
navigation/GreekUtils surface still tested in test_notebook_utils.py)."""
import json
import unicodedata
from unittest.mock import patch

import pytest

from eee_project import SlotTemplate
from eee_project.content import (
    load_ga_config,
    greek_compare,
    strip_diacritics,
    poly_to_mono,
    parse_stanza_text,
    parse_stanza_translations,
    find_stanza_translation,
    interlinear_translator_key,
    strip_comment_lines,
    add_labels,
    setup_ancient_greek,
    _norm_grc,
    build_grc_paradigm_table,
    build_modern_paradigm_table,
    build_grc_lexicon_tabs,
    build_grc_period_tables,
    grc_period_options,
    render_grc_period_table,
    filter_grc_quiz_words,
    grc_coverage_words,
    grc_lexicon_sources,
    norm_grc_surface,
    resolve_clicked_word,
    parent_back_url,
    _source_host_base,
    save_language_selection,
    _cors_safe_raw_url,
    _rehost_raw_url,
    _fetch_url_bytes,
    _fetch_url_bytes_async,
    _fetch_json_url,
    _UI_LANGS,
    _load_ui_labels,
    _GRC_TCOL,
    _EL_VERB_COL_LBL,
    _EL_VOICE_CAP,
)
from eee_project.notebook_utils import language_bridge, language_selector
from conftest import (
    LangMo as _LangMo, FakeParadigmBackend as _FakeParadigmBackend,
    SAMPLE_GA as _SAMPLE_GA, make_resp as _make_resp,
)

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


# ──────────────────────────── build_modern_paradigm_table (el renderer) ──

class _PassiveOnlyVerbBackend:
    """Present-indicative slots for the passive voice only; every form is γράφω."""
    def get_slot_templates(self, lang, pos, terms):
        if pos != "verb":
            return []
        return [
            SlotTemplate(label="", tag_type="ud",
                         features={"Tense": "Pres", "Mood": "Ind", "Voice": "Pass", "Person": p, "Number": n})
            for p in "123" for n in ("Sing", "Plur")
        ]

    def inflect(self, lemma, feats, pos, language=None, **k):
        return {"γράφω"}


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

    def test_declinable_pronoun_without_modern_forms_returns_none(self):
        # reaches the table builder (unlike the indeclinable case): no table, not a grid of dashes
        bt = build_modern_paradigm_table(_EmptyGrcBackend())
        assert bt({"lemma": "κανένας", "form": "κανένας", "pos": "pronoun"}) is None

    def test_verb_with_only_passive_forms_renders_only_the_passive_table(self):
        # a deponent verb has no Active forms: that table is skipped, not shown empty
        bt = build_modern_paradigm_table(_PassiveOnlyVerbBackend(), lang="en")
        html = bt({"lemma": "γράφω", "form": "γράφω", "pos": "verb"})
        assert html and html.count("<table") == 1
        assert "pass." in html and "act." not in html

    def test_verb_without_modern_forms_returns_none(self):
        bt = build_modern_paradigm_table(_EmptyGrcBackend())
        assert bt({"lemma": "γράφω", "form": "γράφω", "pos": "verb"}) is None

    def test_unsupported_pos_returns_none(self):
        bt = build_modern_paradigm_table(_EmptyGrcBackend())
        assert bt({"lemma": "και", "form": "και", "pos": "particle"}) is None

    def test_noun_case_labels_lang_en(self):
        # lang used to be accepted and silently ignored -- table labels
        # were hardcoded Russian regardless of what was passed.
        html = self._bt()({"lemma": "ἄνθρωπος", "form": "ἄνθρωπος", "pos": "noun"}, lang="en")
        assert html and "Nom." in html and "Gen." in html
        assert "Им." not in html and "Род." not in html

    def test_verb_voice_caption_lang_en(self):
        html = self._bt()({"lemma": "γράφω", "form": "γράφω", "pos": "verb"}, lang="en")
        assert html and "act." in html and "pass." in html
        assert "действ." not in html and "страд." not in html
        assert "θα γράψω" in html  # particle/form content itself is language-independent

    def test_verb_tense_column_labels_lang_el(self):
        html = self._bt()({"lemma": "γράφω", "form": "γράφω", "pos": "verb"}, lang="el")
        assert html and "Ενεστ." in html  # present
        assert "Наст." not in html

    def test_default_caption_is_localized_not_fixed_english(self):
        # Companion to the grc-side test of the same name: the fallback
        # table caption (no _cap passed) must vary with lang, not stay
        # fixed at one language regardless of what's requested.
        bt = self._bt()
        html_ru = bt({"lemma": "ἄνθρωπος", "form": "ἄνθρωπος", "pos": "noun"})
        html_en = bt({"lemma": "ἄνθρωπος", "form": "ἄνθρωπος", "pos": "noun"}, lang="en")
        assert html_ru and "новогреческий" in html_ru and "modern-greek" not in html_ru
        assert html_en and "modern-greek" in html_en


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

    def test_required_lexicon_backend_error_hides_table(self):
        # a raising require_lexicon backend is isolated like the Modern rung: table hidden, nothing propagates
        w = {"lemma": "θεος", "form": "θεος", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        tabs = build_grc_lexicon_tabs(_GrcNounBackend(), _EmptyGrcBackend(),
                                       lexicons={"homer": object()}, require_lexicon="homer")
        with patch("eee_project.inflect_slot", side_effect=RuntimeError("boom")):
            assert tabs(w) is None


# ────────── build_grc_period_tables / grc_period_options / render_grc_period_table ──
# Data-returning siblings of build_grc_lexicon_tabs, for callers that want a
# real mo.ui.dropdown (native <select>, correctly closes on pick) instead of
# its CSS-only radio/details picker -- see each function's own docstring.

class TestBuildGrcPeriodTables:
    def _backends(self):
        from ancient_greek_backend_eee import AncientGreekBackend
        from unimorph_backend_eee import UniMorphBackend
        return AncientGreekBackend(lexicons=["homer"]), UniMorphBackend(language="grc")

    def test_returns_callable(self):
        fn = build_grc_period_tables(_EmptyGrcBackend(), _EmptyGrcBackend(), lexicons={})
        assert callable(fn)

    def test_no_lexicon_tag_returns_none(self):
        fn = build_grc_period_tables(_EmptyGrcBackend(), _EmptyGrcBackend(), lexicons={})
        w = {"lemma": "θεός", "pos": "noun", "form": "θεόν", "lexicon_tag": ""}
        assert fn(w) is None

    def test_single_lexicon_returns_one_entry(self):
        # Ἄνδρα (ἀνήρ): confirmed-attested Homer form, same fixture as
        # TestRequireLexicon.test_shown_when_required_lexicon_has_exact_form.
        ag, um = self._backends()
        fn = build_grc_period_tables(ag, um, lexicons={"homer": ag})
        w = {"lemma": "ἀνήρ", "form": "Ἄνδρα", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        result = fn(w)
        assert result is not None
        assert [n for n, _ in result] == ["homer"]
        assert "<table" in result[0][1]

    def test_modern_rung_appended(self):
        from modern_greek_backend_eee import ModernGreekBackend
        ag, um = self._backends()
        fn = build_grc_period_tables(ag, um, lexicons={"homer": ag}, el_backend=ModernGreekBackend())
        w = {"lemma": "ἀνήρ", "form": "Ἄνδρα", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        names = [n for n, _ in fn(w)]
        assert names == ["homer", "modern"]

    def test_no_modern_rung_without_el_backend(self):
        ag, um = self._backends()
        fn = build_grc_period_tables(ag, um, lexicons={"homer": ag}, el_backend=None)
        w = {"lemma": "ἀνήρ", "form": "Ἄνδρα", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        assert "modern" not in [n for n, _ in fn(w)]

    def test_modern_rung_error_isolated(self):
        # Same fixture as TestModernRung.test_modern_rung_error_isolated.
        class _Boom:
            def get_slot_templates(self, *a, **k):
                raise RuntimeError("boom")
        ag, um = self._backends()
        fn = build_grc_period_tables(ag, um, lexicons={"homer": ag}, el_backend=_Boom())
        w = {"lemma": "ἀνήρ", "form": "Ἄνδρα", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        # must not raise; Modern rung omitted, the homer side still returned
        names = [n for n, _ in fn(w)]
        assert names == ["homer"]

    def test_no_table_when_form_unattested_anywhere(self):
        # Same regression fixture as
        # TestModernRung.test_no_modern_only_table_when_form_unattested_anywhere:
        # a lemma-only tag match must not surface a Modern-only result when
        # the tested FORM itself is attested nowhere, ancient or modern.
        from modern_greek_backend_eee import ModernGreekBackend
        ag, um = self._backends()
        fn = build_grc_period_tables(ag, um, lexicons={"homer": ag}, el_backend=ModernGreekBackend())
        w = {"lemma": "ἄλγος", "form": "ἄλγεα", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        assert fn(w) is None

    def test_require_lexicon_hides_when_absent(self):
        # Same fixture as TestRequireLexicon.test_hidden_when_required_lexicon_lacks_exact_form.
        from ancient_greek_backend_eee import AncientGreekBackend
        from modern_greek_backend_eee import ModernGreekBackend
        ag, um = self._backends()
        ag_lsj = AncientGreekBackend(lexicons=["lsj"])
        w = {"lemma": "ἄνθρωπος", "form": "ἀνθρώπων", "pos": "noun",
             "lexicon_tag": 'ancient-greek["lsj"]'}
        fn = build_grc_period_tables(ag, um, lexicons={"homer": ag, "lsj": ag_lsj},
                                      el_backend=ModernGreekBackend(), require_lexicon="homer")
        assert fn(w) is None

    def test_require_lexicon_shown_keeps_rest_of_progression(self):
        # Same fixture as TestRequireLexicon.test_shown_when_required_lexicon_has_exact_form.
        from modern_greek_backend_eee import ModernGreekBackend
        ag, um = self._backends()
        w = {"lemma": "ἀνήρ", "form": "Ἄνδρα", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        fn = build_grc_period_tables(ag, um, lexicons={"homer": ag},
                                      el_backend=ModernGreekBackend(), require_lexicon="homer")
        names = [n for n, _ in fn(w)]
        # attested in the anchor lexicon -> the rest of the diachronic
        # progression (here: Modern) still comes alongside it, unchanged
        assert names == ["homer", "modern"]

    def test_require_lexicon_default_none_preserves_tag_matched_behaviour(self):
        # Same fixture as TestRequireLexicon.test_default_none_preserves_prior_behaviour
        # -- that test's own comment claims this confirms the tag-matched lsj
        # path rather than the unimorph fallback, but its assertion only
        # checks "Modern Greek" in html, which is true either way.
        #
        # Historical note (accurate against ancient-greek-backend-eee 0.3.0,
        # WRONG since 2.0.1, confirmed 2026-09-26): this fixture used to
        # exercise the unimorph fallback instead of the tag-matched lsj path
        # -- 0.3.0's lsj-scoped lookup failed to attest ἀνθρώπων (a common,
        # basic noun form any reasonably complete AG engine should find),
        # so `_resolve_grc_period_tables`'s `available` loop got an empty
        # `tbl` and fell through to the `len(tables) == 0` unimorph branch.
        # 2.0.1 (30+ releases of real lexicon/backend work later) correctly
        # attests it directly via the tag-matched "lsj" backend -- this
        # test's own NAME was already aspirational back then ("preserves
        # tag_matched_behaviour" while actually observing the fallback);
        # it's simply true now. `_resolve_grc_period_tables` itself is
        # unchanged; only the backend's attestation improved.
        #
        # What this test actually confirms: require_lexicon=None does NOT
        # apply require_lexicon's hide-unless-attested gating.
        from ancient_greek_backend_eee import AncientGreekBackend
        from modern_greek_backend_eee import ModernGreekBackend
        ag, um = self._backends()
        ag_lsj = AncientGreekBackend(lexicons=["lsj"])
        w = {"lemma": "ἄνθρωπος", "form": "ἀνθρώπων", "pos": "noun",
             "lexicon_tag": 'ancient-greek["lsj"]'}
        fn = build_grc_period_tables(ag, um, lexicons={"homer": ag, "lsj": ag_lsj},
                                      el_backend=ModernGreekBackend())
        names = [n for n, _ in fn(w)]
        assert names == ["lsj", "modern"]

    def test_unknown_required_lexicon_key_hides(self):
        # Same fixture as TestRequireLexicon.test_unknown_required_lexicon_key_hides.
        ag, um = self._backends()
        w = {"lemma": "ἀνήρ", "form": "Ἄνδρα", "pos": "noun",
             "lexicon_tag": 'ancient-greek["homer"]'}
        fn = build_grc_period_tables(ag, um, lexicons={"homer": ag}, require_lexicon="nonexistent")
        assert fn(w) is None

    def test_public_api(self):
        import eee_project as eee
        assert hasattr(eee, "build_grc_period_tables")
        assert callable(eee.build_grc_period_tables)


class TestGrcPeriodOptions:
    def test_maps_full_labels_to_period_keys(self):
        # same full _GRC_LEX_PERIOD labels build_grc_lexicon_tabs's own
        # CSS picker already used for its summary pill and menu options.
        tables = [("homer", "<table>1</table>"), ("lsj", "<table>2</table>"),
                  ("modern", "<table>3</table>")]
        assert grc_period_options(tables) == {
            "Epic Greek · c. 800–700 BCE": "homer",
            "Classical Attic · 5th–4th c. BCE": "lsj",
            "Modern Greek · 16th c.–present": "modern",
        }

    def test_empty_tables(self):
        assert grc_period_options([]) == {}

    def test_public_api(self):
        import eee_project as eee
        assert hasattr(eee, "grc_period_options")
        assert callable(eee.grc_period_options)


class TestRenderGrcPeriodTable:
    _TABLES = [("homer", "<table>HOMER</table>"), ("lsj", "<table>LSJ</table>")]

    def test_renders_chosen_period_only(self):
        html = render_grc_period_table(self._TABLES, "lsj")
        assert "LSJ" in html and "HOMER" not in html

    @pytest.mark.parametrize("period", [None, "nonexistent"])
    def test_defaults_to_first_when_period_missing_or_unknown(self, period):
        html = render_grc_period_table(self._TABLES, period)
        assert "HOMER" in html

    def test_multiple_periods_show_description_but_not_a_repeated_header(self):
        html = render_grc_period_table(self._TABLES, "homer")
        assert "Epic Greek" not in html
        assert "homer lexicon" in html

    def test_single_period_includes_header_and_description(self):
        html = render_grc_period_table([("homer", "<table>HOMER</table>")], "homer")
        assert "Epic Greek" in html
        assert "homer lexicon" in html

    def test_empty_tables_returns_empty_string(self):
        assert render_grc_period_table([], None) == ""

    def test_public_api(self):
        import eee_project as eee
        assert hasattr(eee, "render_grc_period_table")
        assert callable(eee.render_grc_period_table)


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

    # phrase comparison: punctuation/whitespace are separators, not content

    def test_trailing_punctuation_ignored(self):
        assert greek_compare("Έχεις κανένα σχέδιο;", "Έχεις κανένα σχέδιο") is True

    def test_leading_punctuation_ignored(self):
        assert greek_compare("«Έχεις κανένα σχέδιο»", "Έχεις κανένα σχέδιο") is True

    def test_multiple_internal_spaces_ignored(self):
        assert greek_compare("Έχεις  κανένα   σχέδιο", "Έχεις κανένα σχέδιο") is True

    def test_comma_and_exclamation_ignored(self):
        assert greek_compare("Άντε, ρε!", "Άντε ρε") is True

    def test_ellipsis_ignored(self):
        assert greek_compare("Έλα τώρα...", "Έλα τώρα") is True

    def test_different_word_sequence_still_fails(self):
        assert greek_compare("Έχεις κανένα σχέδιο", "Έχεις κανένα βιβλίο") is False

    def test_different_word_count_still_fails(self):
        assert greek_compare("Έχεις κανένα σχέδιο", "Έχεις σχέδιο") is False


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


# ───────────────────────────────────── find_stanza_translation ──

class TestFindStanzaTranslation:
    def test_exact_match(self):
        translations = {"IX.39-42": "text-a", "IX.43-46": "text-b"}
        assert find_stanza_translation("IX.43-46", translations) == "text-b"

    def test_falls_back_to_containing_coarser_range(self):
        translations = {"IX.39-46 (equivalent passage)": "wide-text"}
        assert find_stanza_translation("IX.39-42", translations) == "wide-text"
        assert find_stanza_translation("IX.43-46", translations) == "wide-text"

    def test_en_dash_and_ascii_hyphen_both_parse(self):
        translations = {"IX.39–46": "wide-text"}
        assert find_stanza_translation("IX.39-42", translations) == "wide-text"
        assert find_stanza_translation("IX.39–42", translations) == "wide-text"

    def test_no_containing_range_returns_dash(self):
        translations = {"IX.100-110": "unrelated"}
        assert find_stanza_translation("IX.39-42", translations) == "—"

    def test_different_book_not_matched(self):
        translations = {"I.39-46": "wrong-book"}
        assert find_stanza_translation("IX.39-42", translations) == "—"

    def test_partial_overlap_not_matched(self):
        # a stored range that only partially covers ref must not match --
        # only full containment counts.
        translations = {"IX.40-46": "partial"}
        assert find_stanza_translation("IX.39-42", translations) == "—"

    def test_unparseable_ref_returns_dash(self):
        assert find_stanza_translation("Ithaki 1-3", {"Ithaki 1-3": "x"}) == "x"
        assert find_stanza_translation("prologue", {"IX.1-10": "x"}) == "—"

    def test_empty_translations(self):
        assert find_stanza_translation("IX.39-42", {}) == "—"

    def test_allow_coarse_fallback_false_rejects_coarser_range(self):
        translations = {"IX.39-46 (equivalent passage)": "wide-text"}
        assert find_stanza_translation("IX.39-42", translations, allow_coarse_fallback=False) == "—"

    def test_allow_coarse_fallback_false_still_allows_exact_match(self):
        translations = {"IX.39-42": "text-a"}
        assert find_stanza_translation("IX.39-42", translations, allow_coarse_fallback=False) == "text-a"


# ───────────────────────────────────── interlinear_translator_key ──

class TestInterlinearTranslatorKey:
    def test_ru(self):
        assert interlinear_translator_key("ru") == "interlinear_ru"

    def test_en(self):
        assert interlinear_translator_key("en") == "interlinear_en"

    def test_el(self):
        assert interlinear_translator_key("el") == "interlinear_el"

    def test_matches_parse_stanza_translations_section_naming(self):
        # The KB names its interlinear section "## interlinear_{lang}" --
        # confirm the helper's output is a key parse_stanza_translations
        # would actually produce from such a section.
        md = "## interlinear_ru\n### IX.39-42\nline\n"
        translations, _ = parse_stanza_translations(md)
        assert interlinear_translator_key("ru") in translations


# ──────────────────────────────────────── strip_comment_lines ──

class TestStripCommentLines:
    def test_comment_line_dropped(self):
        text = "<!-- grc: εἶμ' Ὀδυσεὺς -->\nI-am Odysseus"
        assert strip_comment_lines(text) == "I-am Odysseus"

    def test_multiple_comment_lines(self):
        text = "<!-- grc: x -->\ngloss-a\n<!-- grc: y -->\ngloss-b"
        assert strip_comment_lines(text) == "gloss-a\ngloss-b"

    def test_any_comment_tag_dropped_not_just_grc(self):
        # generic by design -- a future note type uses the same mechanism
        # without this function needing to know its tag.
        text = "<!-- note: some future annotation -->\nreal content"
        assert strip_comment_lines(text) == "real content"

    def test_no_comment_lines_unchanged(self):
        # plain prose (e.g. a translator with no embedded annotations)
        # passes through unchanged -- a safe no-op.
        text = "plain prose line one\nplain prose line two"
        assert strip_comment_lines(text) == text

    def test_empty_input(self):
        assert strip_comment_lines("") == ""

    def test_blank_lines_preserved(self):
        text = "<!-- grc: x -->\ngloss-a\n\ngloss-b"
        assert strip_comment_lines(text) == "gloss-a\n\ngloss-b"


class TestSetupAncientGreek:
    def test_registers_and_chains(self):
        from eee_project import get_chain
        class _FakeBackend:
            def paradigm(self, w, p): return {}
        fb = _FakeBackend()
        setup_ancient_greek(fb)
        assert get_chain("grc") == ["ancient-greek"]


class TestUiLabel:
    """Paradigm-drill widget-chrome strings come from data/labels/ui-{lang}.tsv --
    never a per-notebook UI_STRINGS dict + local t_ui() closure. Not Config-scoped
    (unlike tense_labels): one GreekUtils instance with no backend at all still
    resolves every key, since this text belongs to the shared widget, not any
    one course's grammar."""

    def test_load_ui_labels_discovers_languages_by_filename(self):
        # _load_ui_labels globs data/labels/ui-*.tsv rather than a fixed
        # ("en", "ru", "el") tuple -- a new language needs only a new file.
        labels = _load_ui_labels()
        assert {lang for entry in labels.values() for lang in entry} == {'en', 'ru', 'el'}

    def test_grc_el_compound_dicts_track_ui_langs_not_a_fixed_literal(self):
        # _GRC_TCOL/_EL_VERB_COL_LBL/_EL_VOICE_CAP (built via the shared
        # _lang_map() helper) iterate _UI_LANGS (itself derived from
        # whichever ui-*.tsv files exist -- see the test above), not a
        # hardcoded ("en", "ru", "el") tuple. So dropping in ui-fr.tsv with
        # their same keys would add "fr" to all three with no source
        # change -- proven here by construction, not by re-importing the
        # module with a 4th file on disk. The sibling default-caption
        # strings (grc_default_caption/el_default_caption) have the same
        # property for free -- they're plain _ui_label() calls, not a
        # cached dict, so there's no separate structure to check here.
        assert _UI_LANGS == sorted(_UI_LANGS)  # base assumption the dicts below rely on
        for name, d in (("_GRC_TCOL", _GRC_TCOL), ("_EL_VERB_COL_LBL", _EL_VERB_COL_LBL),
                        ("_EL_VOICE_CAP", _EL_VOICE_CAP)):
            assert set(d.keys()) == set(_UI_LANGS), f"{name} has a fixed language set, not derived from _UI_LANGS"


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

    def test_fetches_from_url(self):
        with patch("urllib.request.urlopen", return_value=_make_resp(json.dumps(_SAMPLE_GA).encode("utf-8"))):
            assert load_ga_config("https://example.com/ga.json") == _SAMPLE_GA

    def test_url_rewrites_codeberg_before_fetch(self):
        # Same CORS-safe rewrite ConfigStore.from_url()'s ga= URL already
        # gets -- a WASM export's browser fetch is blocked by Codeberg's
        # plain git-web raw endpoint (no CORS headers).
        seen_urls = []

        def fake_urlopen(url, timeout=None):
            seen_urls.append(url)
            return _make_resp(json.dumps(_SAMPLE_GA).encode("utf-8"))

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = load_ga_config("https://codeberg.org/EEE-project/eee-project/raw/branch/main/ga.json")
        assert seen_urls == ["https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/ga.json?ref=main"]
        assert result == _SAMPLE_GA

    def test_url_fetch_failure_returns_none(self):
        with patch("urllib.request.urlopen", side_effect=OSError("network down")):
            assert load_ga_config("https://example.com/ga.json") is None


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
        _source_host_base.cache_clear()
        self._install_fake_js(monkeypatch, "eee-project.github.io")
        assert _source_host_base() == "https://github.com/EEE-project"

    def test_gitlab_pages_host(self, monkeypatch):
        _source_host_base.cache_clear()
        self._install_fake_js(monkeypatch, "eee-project.gitlab.io")
        assert _source_host_base() == "https://gitlab.com/EEE-project"

    def test_split_gitlab_project_host_still_maps_to_gitlab(self, monkeypatch):
        # A split course lives on the same eee-project.gitlab.io domain,
        # just a different path -- hostname-only detection must not need
        # special-casing per split project.
        _source_host_base.cache_clear()
        self._install_fake_js(monkeypatch, "eee-project.gitlab.io")
        assert _source_host_base() == "https://gitlab.com/EEE-project"

    def test_codeberg_pages_host(self, monkeypatch):
        _source_host_base.cache_clear()
        self._install_fake_js(monkeypatch, "eee-project.codeberg.page")
        assert _source_host_base() == "https://codeberg.org/EEE-project"

    def test_no_js_module_falls_back_to_codeberg(self, monkeypatch):
        _source_host_base.cache_clear()
        import sys
        monkeypatch.delitem(sys.modules, "js", raising=False)
        assert _source_host_base() == "https://codeberg.org/EEE-project"

    def test_unrecognized_hostname_falls_back_to_codeberg(self, monkeypatch):
        _source_host_base.cache_clear()
        self._install_fake_js(monkeypatch, "localhost")
        assert _source_host_base() == "https://codeberg.org/EEE-project"


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
        _source_host_base.cache_clear()
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

    def test_gitlab_remote_base_non_ascii_filename_not_double_encoded(self, gu_marimo, tmp_path):
        # Regression: ensure_file() pre-quotes the filename via
        # urllib.parse.quote() before handing the URL to
        # _cors_safe_raw_url(), which used to re-quote the whole path for
        # GitLab's file_path parameter -- double-encoding the '%' already
        # in the filename's percent-encoding and 404ing on GitLab specifically
        # (Codeberg's branch doesn't re-quote, so it never showed this bug).
        seen = {}

        def fake_urlopen(url, timeout=None):
            seen["url"] = url
            return _make_resp(b"%PDF-1.4 fake")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            gu_marimo.ensure_file(
                "Одиссея 1.pdf", nb_dir=tmp_path,
                remote_base="https://gitlab.com/EEE-project/created_with_eee/-/raw/main/"
                "ancient_greek/odyssey/2026_06_15",
            )
        assert seen["url"] == (
            "https://gitlab.com/api/v4/projects/EEE-project%2Fcreated_with_eee/"
            "repository/files/ancient_greek%2Fodyssey%2F2026_06_15%2F"
            "%D0%9E%D0%B4%D0%B8%D1%81%D1%81%D0%B5%D1%8F%201.pdf/raw?ref=main"
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
        _source_host_base.cache_clear()
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
        _source_host_base.cache_clear()
        assert _cors_safe_raw_url(
            "https://codeberg.org/EEE-project/eee-project/raw/branch/main/examples/vocab.tsv"
        ) == "https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/examples/vocab.tsv?ref=main"

    def test_codeberg_nested_path_preserved(self):
        _source_host_base.cache_clear()
        assert _cors_safe_raw_url(
            "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main/"
            "ancient_greek/palaestra/index.tsv"
        ) == (
            "https://codeberg.org/api/v1/repos/EEE-project/created_with_eee/raw/"
            "ancient_greek/palaestra/index.tsv?ref=main"
        )

    def test_codeberg_non_main_branch_preserved(self):
        _source_host_base.cache_clear()
        assert _cors_safe_raw_url(
            "https://codeberg.org/EEE-project/eee-project/raw/branch/dev/x.tsv"
        ) == "https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/x.tsv?ref=dev"

    def test_gitlab_raw_url_rewritten_with_percent_encoded_path(self):
        _source_host_base.cache_clear()
        assert _cors_safe_raw_url(
            "https://gitlab.com/EEE-project/created_with_eee/-/raw/main/"
            "ancient_greek/palaestra/index.tsv"
        ) == (
            "https://gitlab.com/api/v4/projects/EEE-project%2Fcreated_with_eee/"
            "repository/files/ancient_greek%2Fpalaestra%2Findex.tsv/raw?ref=main"
        )

    def test_gitlab_flat_filename(self):
        _source_host_base.cache_clear()
        assert _cors_safe_raw_url(
            "https://gitlab.com/EEE-project/eee-project/-/raw/main/README.md"
        ) == (
            "https://gitlab.com/api/v4/projects/EEE-project%2Feee-project/"
            "repository/files/README.md/raw?ref=main"
        )

    def test_github_raw_url_unchanged(self):
        # raw.githubusercontent.com already sends Access-Control-Allow-Origin.
        _source_host_base.cache_clear()
        url = "https://raw.githubusercontent.com/EEE-project/eee-project/main/README.md"
        assert _cors_safe_raw_url(url) == url

    def test_already_codeberg_api_form_unchanged(self):
        # Idempotent: a URL already in the CORS-safe form must not be rewritten again.
        _source_host_base.cache_clear()
        url = "https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/examples/vocab.tsv"
        assert _cors_safe_raw_url(url) == url

    def test_unrelated_url_unchanged(self):
        _source_host_base.cache_clear()
        url = "https://example.com/some/file.tsv"
        assert _cors_safe_raw_url(url) == url

    def test_github_host_rewrites_codeberg_then_cors(self, monkeypatch):
        # _cors_safe_raw_url now rehosts Codeberg URLs internally, then applies CORS transform.
        # GitHub raw URLs already have CORS headers, so no API transform needed.
        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.github.io")
        assert _cors_safe_raw_url(
            "https://codeberg.org/EEE-project/greek-knowledge-eee/raw/branch/main/vocab.tsv"
        ) == "https://raw.githubusercontent.com/EEE-project/greek-knowledge-eee/main/vocab.tsv"

    def test_gitlab_host_rewrites_codeberg_then_cors(self, monkeypatch):
        # _cors_safe_raw_url now rehosts Codeberg URLs to GitLab form, then applies GitLab API CORS transform.
        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.gitlab.io")
        assert _cors_safe_raw_url(
            "https://codeberg.org/EEE-project/greek-knowledge-eee/raw/branch/main/vocab.tsv"
        ) == (
            "https://gitlab.com/api/v4/projects/EEE-project%2Fgreek-knowledge-eee/"
            "repository/files/vocab.tsv/raw?ref=main"
        )

    def test_codeberg_host_no_rehost_still_cors_transforms(self, monkeypatch):
        # When running on Codeberg, rehost is a no-op, but CORS transform still applies.
        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.codeberg.page")
        assert _cors_safe_raw_url(
            "https://codeberg.org/EEE-project/eee-project/raw/branch/main/README.md"
        ) == "https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/README.md?ref=main"


class TestRehostRawUrl:
    """_rehost_raw_url: rewrite a Codeberg-shaped raw URL to whichever host
    is actually serving the page -- see the host-resilience design doc."""

    _CODEBERG_URL = (
        "https://codeberg.org/EEE-project/greek-knowledge-eee/raw/branch/main/"
        "texts/odyssey/translations_en.md"
    )

    def test_github_host_rewrites_to_raw_githubusercontent(self, monkeypatch):
        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.github.io")
        assert _rehost_raw_url(self._CODEBERG_URL) == (
            "https://raw.githubusercontent.com/EEE-project/greek-knowledge-eee/"
            "main/texts/odyssey/translations_en.md"
        )

    def test_gitlab_host_rewrites_to_gitlab_raw(self, monkeypatch):
        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.gitlab.io")
        assert _rehost_raw_url(self._CODEBERG_URL) == (
            "https://gitlab.com/EEE-project/greek-knowledge-eee/-/raw/main/"
            "texts/odyssey/translations_en.md"
        )

    def test_codeberg_host_unchanged(self, monkeypatch):
        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.codeberg.page")
        assert _rehost_raw_url(self._CODEBERG_URL) == self._CODEBERG_URL

    def test_local_dev_fallback_unchanged(self, monkeypatch):
        _source_host_base.cache_clear()
        import sys
        monkeypatch.delitem(sys.modules, "js", raising=False)
        assert _rehost_raw_url(self._CODEBERG_URL) == self._CODEBERG_URL

    def test_non_codeberg_shaped_url_passes_through(self, monkeypatch):
        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.github.io")
        url = "https://raw.githubusercontent.com/EEE-project/eee-project/main/README.md"
        assert _rehost_raw_url(url) == url

    def test_non_ancient_greek_repo_also_works(self, monkeypatch):
        # Confirms owner/repo are genuinely wildcarded, not hardcoded to
        # created_with_eee -- greek-knowledge-eee (or any future repo) gets
        # the identical treatment with no repo-specific code path.
        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.gitlab.io")
        url = "https://codeberg.org/EEE-project/created_with_eee/raw/branch/main/greek.md"
        assert _rehost_raw_url(url) == (
            "https://gitlab.com/EEE-project/created_with_eee/-/raw/main/greek.md"
        )

    def test_ensure_file_integration_github_host(self, gu_marimo, tmp_path, monkeypatch):
        # Integration test: ensure_file wiring calls _rehost_raw_url before fetch,
        # and the rewritten URL is actually used, not the original Codeberg one.
        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.github.io")
        seen = {}

        def fake_urlopen(url, timeout=None):
            seen["url"] = url
            return _make_resp(b"fetched")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = gu_marimo.ensure_file(
                "vocab.tsv",
                nb_dir=tmp_path,
                remote_base="https://codeberg.org/EEE-project/greek-knowledge-eee/raw/branch/main/texts",
            )
        assert result == tmp_path / "vocab.tsv"
        # URL must be rewritten to raw.githubusercontent.com (GitHub), not Codeberg
        assert "raw.githubusercontent.com" in seen["url"]
        assert "EEE-project/greek-knowledge-eee" in seen["url"]
        assert "codeberg.org" not in seen["url"]

    def test_ensure_files_integration_gitlab_host(self, gu_marimo, tmp_path, monkeypatch):
        # Integration test: ensure_files (async) wiring calls _rehost_raw_url before fetch.
        # After _rehost_raw_url rewrites to gitlab.com format, _cors_safe_raw_url
        # converts it to the GitLab API form for CORS safety.
        import asyncio

        _source_host_base.cache_clear()
        TestSourceHostBase._install_fake_js(monkeypatch, "eee-project.gitlab.io")
        seen = []

        def fake_urlopen(url, timeout=None):
            seen.append(url)
            return _make_resp(b"fetched")

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = asyncio.run(gu_marimo.ensure_files(
                "vocab.tsv", "greek.md",
                nb_dir=tmp_path,
                remote_base="https://codeberg.org/EEE-project/created_with_eee/raw/branch/main/materials",
            ))
        assert result["vocab.tsv"] == tmp_path / "vocab.tsv"
        assert result["greek.md"] == tmp_path / "greek.md"
        # Both URLs must be rewritten to gitlab.com (GitLab API form after CORS transform),
        # not Codeberg
        assert len(seen) == 2
        for url in seen:
            assert "gitlab.com" in url
            assert "api/v4" in url  # CORS-safe form
            assert "codeberg.org" not in url


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


class TestFetchJsonUrl:
    """_fetch_json_url: the CORS-rewrite + fetch + JSON-parse composition
    shared by load_ga_config's URL branch. ConfigStore.from_url keeps its
    own inline copy rather than calling this -- see _fetch_json_url's own
    docstring for why (it swallows fetch errors; from_url's ga= fetch is
    meant to also blank out already-fetched lessons on failure)."""

    def test_fetches_and_parses(self):
        with patch("urllib.request.urlopen", return_value=_make_resp(b'{"a": 1}')):
            assert _fetch_json_url("https://example.com/x.json") == {"a": 1}

    def test_rewrites_codeberg_url(self):
        _source_host_base.cache_clear()
        seen_urls = []

        def fake_urlopen(url, timeout=None):
            seen_urls.append(url)
            return _make_resp(b'{"a": 1}')

        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            _fetch_json_url("https://codeberg.org/EEE-project/eee-project/raw/branch/main/ga.json")
        assert seen_urls == ["https://codeberg.org/api/v1/repos/EEE-project/eee-project/raw/ga.json?ref=main"]

    def test_fetch_failure_returns_none(self):
        with patch("urllib.request.urlopen", side_effect=OSError("network down")):
            assert _fetch_json_url("https://example.com/x.json") is None

    def test_malformed_json_returns_none(self):
        with patch("urllib.request.urlopen", return_value=_make_resp(b"not json{{{")):
            assert _fetch_json_url("https://example.com/x.json") is None


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

    def test_pronoun_personal_no_forms_returns_none(self):
        """Mirrors test_pronoun_demonstrative_no_forms_returns_none for the personal family."""
        fn = build_grc_paradigm_table(_GrcPronPrsBackend(), _EmptyGrcBackend())
        with patch("eee_project.inflect_slot", return_value=set()):
            result = fn({"lemma": "ἐγώ", "pos": "pronoun", "form": "εγω"})
        assert result is None

    def test_pronoun_no_forms_returns_none(self):
        """pos="pronoun" with a backend that has zero pronoun slot data
        returns None -- same pattern as every other "no data" test in this
        class."""
        fn = build_grc_paradigm_table(_EmptyGrcBackend(), _EmptyGrcBackend())
        result = fn({"lemma": "τις", "pos": "pronoun", "form": "τις"})
        assert result is None


class TestBuildGrcParadigmTableMultilang:
    """build_grc_paradigm_table's own `lang` param (the per-call override on
    the returned closure, not the builder's) used to be accepted and
    silently ignored -- every row/column label was hardcoded Russian
    regardless of what was passed. These confirm passing lang="en"/"el"
    per call now actually changes the rendered labels."""

    def test_noun_case_label_lang_en(self):
        fn = build_grc_paradigm_table(_GrcNounBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "θεος", "pos": "noun", "form": "θεος"}, lang="en")
        assert "Nom." in result
        assert "Им." not in result

    def test_verb_tense_column_and_person_row_lang_en(self):
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"λυω"} if slot.tag == "PAI.1S" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "λυω", "pos": "verb", "form": "λυω"}, lang="en")
        assert "Pres." in result
        assert "1 sg." in result
        assert "Наст." not in result

    def test_verb_infinitive_row_lang_el(self):
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            if slot.tag == "PAI.1S": return {"λυω"}
            if slot.tag == "PAN": return {"λυειν"}
            return set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "λυω", "pos": "verb", "form": "λυω"}, lang="el")
        assert "Απρφ." in result
        assert "Инф." not in result

    def test_verb_imperative_row_lang_en(self):
        fn = build_grc_paradigm_table(_GrcVerbBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            if slot.tag == "PAI.1S": return {"λυω"}
            if slot.tag == "PAD.2S": return {"λυε"}
            return set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "λυω", "pos": "verb", "form": "λυω"}, lang="en")
        assert "Imp. 2sg." in result
        assert "Пов." not in result

    def test_pronoun_dual_label_lang_en(self):
        fn = build_grc_paradigm_table(_GrcPronPrsBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"εγω"} if slot.tag == ".NS1" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "ἐγώ", "pos": "pronoun", "form": "εγω"}, lang="en")
        assert "1 du." in result
        assert "1 дв." not in result

    def test_missing_paradigm_message_lang_en(self):
        fn = build_grc_paradigm_table(_GrcNounBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "θεος", "pos": "noun", "form": "θεον"}, lang="en")
        assert "missing in the paradigm of" in result
        assert "отсутствует" not in result

    def test_builder_level_lang_still_works_as_default(self):
        """The builder's own `lang="en"` (not a per-call override) must
        still work as the default when a call doesn't pass its own lang --
        this is the pre-existing mechanism (already used for
        get_slot_templates); the per-call override is additive, not a
        replacement for it."""
        fn = build_grc_paradigm_table(_GrcNounBackend(), _EmptyGrcBackend(), lang="en")
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result = fn({"lemma": "θεος", "pos": "noun", "form": "θεος"})
        assert "Nom." in result

    def test_default_caption_is_localized_not_fixed_english(self):
        """Regression: the fallback table caption (shown when neither the
        caller's own `_cap` nor the word's `lexicon_tag` is given) used to
        be the fixed literal "ancient-greek" regardless of `lang` -- a ru
        table would show an English caption in this one spot. Now varies
        with lang like every other label in this table."""
        fn = build_grc_paradigm_table(_GrcNounBackend(), _EmptyGrcBackend())
        def fake_inflect(word, slot, pos, *, language, backend):
            return {"θεος"} if slot.tag == ".NSM" else set()
        with patch("eee_project.inflect_slot", side_effect=fake_inflect):
            result_ru = fn({"lemma": "θεος", "pos": "noun", "form": "θεος"})
            result_en = fn({"lemma": "θεος", "pos": "noun", "form": "θεος"}, lang="en")
        assert "древнегреческий" in result_ru
        assert "ancient-greek" not in result_ru
        assert "ancient-greek" in result_en


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

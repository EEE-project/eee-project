"""Tests for GreekUtils — uses a stub backend so no real morphology library is required."""
from types import SimpleNamespace

import pytest

from eee_project import GreekUtils


# ---------------------------------------------------------------------------
# Stub backend
# ---------------------------------------------------------------------------

class _StubMo:
    """Minimal marimo stub — only the parts GreekUtils touches."""

    class _text:
        def __init__(self, label=""):
            self.label = label
            self.value = ""

    class _array:
        def __init__(self, elements):
            self.elements = elements
            self.value = [e.value for e in elements]

    class _md:
        def __init__(self, text):
            self.text = text

    class ui:
        @staticmethod
        def text(label=""):
            return _StubMo._text(label)

        @staticmethod
        def array(elements):
            return _StubMo._array(elements)

    @staticmethod
    def md(text):
        return _StubMo._md(text)


_mo = _StubMo()

import pandas as _pd_real


def _noun_paradigm(word):
    """Minimal modern-Greek noun paradigm for η μνήμη (fem)."""
    return {
        'fem': {
            'sg': {'nom': {'μνήμη'}, 'acc': {'μνήμη'}, 'gen': {'μνήμης'}},
            'pl': {'nom': {'μνήμες'}, 'acc': {'μνήμες'}, 'gen': {'μνημών'}},
        }
    }


def _verb_paradigm(word):
    """Minimal paradigm for γράφω (present active)."""
    return {
        'present': {
            'active': {
                'ind': {
                    'sg': {'pri': {'γράφω'}, 'sec': {'γράφεις'}, 'ter': {'γράφει'}},
                    'pl': {'pri': {'γράφουμε'}, 'sec': {'γράφετε'}, 'ter': {'γράφουν'}},
                }
            }
        }
    }


def _adj_paradigm(word):
    """Minimal paradigm for ωραίος."""
    return {
        'adj': {
            'sg': {
                'masc': {'nom': {'ωραίος'}, 'acc': {'ωραίο'}, 'gen': {'ωραίου'}},
                'fem':  {'nom': {'ωραία'},  'acc': {'ωραία'},  'gen': {'ωραίας'}},
                'neut': {'nom': {'ωραίο'},  'acc': {'ωραίο'},  'gen': {'ωραίου'}},
            },
            'pl': {
                'masc': {'nom': {'ωραίοι'}, 'acc': {'ωραίους'}, 'gen': {'ωραίων'}},
                'fem':  {'nom': {'ωραίες'}, 'acc': {'ωραίες'},  'gen': {'ωραίων'}},
                'neut': {'nom': {'ωραία'},  'acc': {'ωραία'},   'gen': {'ωραίων'}},
            },
        }
    }


class StubBackend:
    def paradigm(self, word, pos):
        if pos == 'noun':
            return _noun_paradigm(word)
        if pos == 'verb':
            return _verb_paradigm(word)
        if pos == 'adjective':
            return _adj_paradigm(word)
        return {}


@pytest.fixture
def gu():
    return GreekUtils(StubBackend(), _mo, _pd_real)


# ---------------------------------------------------------------------------
# Noun tests
# ---------------------------------------------------------------------------

def _snap(values, **attrs):
    s = SimpleNamespace(value=values)
    for k, v in attrs.items():
        setattr(s, k, v)
    return s


class TestCheckNounSimple:
    def test_correct_no_article(self, gu):
        snap = _snap(
            ["μνήμη", "μνήμη", "μνήμης", "μνήμες", "μνήμες", "μνημών"],
            test_word="η μνήμη", is_pluralia_tantum=False,
            active_cases=[["sg","nom"],["sg","acc"],["sg","gen"],["pl","nom"],["pl","acc"],["pl","gen"]],
        )
        assert gu.check_noun_test("η μνήμη", snap, mode='simple') is True

    def test_correct_with_article_ignored_simple(self, gu):
        # In simple mode articles are validated if present but not required
        snap = _snap(
            ["η μνήμη", "την μνήμη", "της μνήμης", "οι μνήμες", "τις μνήμες", "των μνημών"],
            test_word="η μνήμη", is_pluralia_tantum=False,
            active_cases=[["sg","nom"],["sg","acc"],["sg","gen"],["pl","nom"],["pl","acc"],["pl","gen"]],
        )
        assert gu.check_noun_test("η μνήμη", snap, mode='simple') is True

    def test_wrong_noun_form(self, gu):
        snap = _snap(
            ["μνήμη", "WRONG", "μνήμης", "μνήμες", "μνήμες", "μνημών"],
            test_word="η μνήμη", is_pluralia_tantum=False,
            active_cases=[["sg","nom"],["sg","acc"],["sg","gen"],["pl","nom"],["pl","acc"],["pl","gen"]],
        )
        assert gu.check_noun_test("η μνήμη", snap, mode='simple') is False

    def test_wrong_article_simple(self, gu):
        # wrong article in simple mode → error
        snap = _snap(
            ["ο μνήμη", "μνήμη", "μνήμης", "μνήμες", "μνήμες", "μνημών"],
            test_word="η μνήμη", is_pluralia_tantum=False,
            active_cases=[["sg","nom"],["sg","acc"],["sg","gen"],["pl","nom"],["pl","acc"],["pl","gen"]],
        )
        assert gu.check_noun_test("η μνήμη", snap, mode='simple') is False

    def test_stale_test_word(self, gu):
        snap = _snap(
            ["μνήμη", "μνήμη", "μνήμης", "μνήμες", "μνήμες", "μνημών"],
            test_word="η γειτονιά",
        )
        assert gu.check_noun_test("η μνήμη", snap, mode='simple') is False


class TestCheckNounComplex:
    def _correct_snap(self):
        return _snap(
            # definite (6): sg nom/acc/gen, pl nom/acc/gen
            ["η μνήμη", "την μνήμη", "της μνήμης",
             "οι μνήμες", "τις μνήμες", "των μνημών",
             # indefinite (3 sg): nom/acc/gen
             "μια μνήμη", "μια μνήμη", "μιας μνήμης"],
            test_word="η μνήμη", is_pluralia_tantum=False,
            active_cases=[["sg","nom"],["sg","acc"],["sg","gen"],["pl","nom"],["pl","acc"],["pl","gen"]],
        )

    def test_correct(self, gu):
        assert gu.check_noun_test("η μνήμη", self._correct_snap(), mode='complex') is True

    def test_missing_article_required(self, gu):
        snap = _snap(
            ["μνήμη", "μνήμη", "μνήμης", "οι μνήμες", "τις μνήμες", "των μνημών",
             "μια μνήμη", "μια μνήμη", "μιας μνήμης"],
            test_word="η μνήμη", is_pluralia_tantum=False,
            active_cases=[["sg","nom"],["sg","acc"],["sg","gen"],["pl","nom"],["pl","acc"],["pl","gen"]],
        )
        # missing definite article in complex mode → error
        assert gu.check_noun_test("η μνήμη", snap, mode='complex') is False

    def test_wrong_indefinite_article(self, gu):
        snap = _snap(
            ["η μνήμη", "η μνήμη", "της μνήμης",
             "οι μνήμες", "τις μνήμες", "των μνημών",
             "ένα μνήμη", "μια μνήμη", "μιας μνήμης"],  # ένα wrong for fem
            test_word="η μνήμη", is_pluralia_tantum=False,
            active_cases=[["sg","nom"],["sg","acc"],["sg","gen"],["pl","nom"],["pl","acc"],["pl","gen"]],
        )
        assert gu.check_noun_test("η μνήμη", snap, mode='complex') is False


# ---------------------------------------------------------------------------
# Verb tests
# ---------------------------------------------------------------------------

class TestCheckVerb:
    def test_correct_present(self, gu):
        snap = _snap(
            ["γράφω", "γράφεις", "γράφει", "γράφουμε", "γράφετε", "γράφουν"],
            verb_word="γράφω",
        )
        ok, errs = gu.check_verb_test("γράφω", snap, "present")
        assert ok is True
        assert errs == ""

    def test_wrong_form(self, gu):
        snap = _snap(
            ["γράφω", "WRONG", "γράφει", "γράφουμε", "γράφετε", "γράφουν"],
            verb_word="γράφω",
        )
        ok, errs = gu.check_verb_test("γράφω", snap, "present")
        assert ok is False
        assert "εσύ" in errs

    def test_future_requires_theta(self, gu):
        # future form needs "θα" prefix — missing prefix → error
        snap = _snap(
            ["γράφω", "γράφεις", "γράφει", "γράφουμε", "γράφετε", "γράφουν"],
            verb_word="γράφω",
        )
        ok, errs = gu.check_verb_test("γράφω", snap, "future")
        # present forms exist but they're the fallback; without θα prefix → error
        assert ok is False

    def test_stale_verb_word(self, gu):
        snap = _snap(
            ["γράφω", "γράφεις", "γράφει", "γράφουμε", "γράφετε", "γράφουν"],
            verb_word="λύω",
        )
        ok, errs = gu.check_verb_test("γράφω", snap, "present")
        assert ok is False

    def test_unknown_tense(self, gu):
        snap = _snap(["", "", "", "", "", ""], verb_word="γράφω")
        ok, errs = gu.check_verb_test("γράφω", snap, "subjunctive_past")
        assert ok is False
        assert "Unknown tense" in errs

    def test_none_form(self, gu):
        ok, errs = gu.check_verb_test("γράφω", None, "present")
        assert ok is False


# ---------------------------------------------------------------------------
# Adjective tests
# ---------------------------------------------------------------------------

class TestCheckAdjective:
    def test_correct_simple(self, gu):
        snap = _snap(
            ["ωραίος", "ωραία", "ωραίο", "ωραίοι", "ωραίες", "ωραία"],
            adj_word="ωραίος", adj_mode="simple",
        )
        ok, errs = gu.check_adjective_test("ωραίος", snap, mode='simple')
        assert ok is True

    def test_wrong_simple(self, gu):
        snap = _snap(
            ["ωραίος", "WRONG", "ωραίο", "ωραίοι", "ωραίες", "ωραία"],
            adj_word="ωραίος", adj_mode="simple",
        )
        ok, errs = gu.check_adjective_test("ωραίος", snap, mode='simple')
        assert ok is False
        assert "Fem" in errs

    def test_correct_complex(self, gu):
        answers = []
        p = StubBackend().paradigm("ωραίος", "adjective")['adj']
        for n in ('sg', 'pl'):
            for g_ in ('masc', 'fem', 'neut'):
                for c in ('nom', 'acc', 'gen'):
                    forms = p.get(n, {}).get(g_, {}).get(c, set())
                    answers.append(next(iter(forms)) if forms else "")
        snap = _snap(answers, adj_word="ωραίος", adj_mode="complex")
        ok, errs = gu.check_adjective_test("ωραίος", snap, mode='complex')
        assert ok is True

    def test_empty_form_returns_false(self, gu):
        ok, errs = gu.check_adjective_test("ωραίος", None, mode='simple')
        assert ok is False

    def test_all_empty_values(self, gu):
        snap = _snap(["", "", "", "", "", ""], adj_word="ωραίος", adj_mode="simple")
        ok, errs = gu.check_adjective_test("ωραίος", snap, mode='simple')
        assert ok is False
        assert "fill in" in errs


# ---------------------------------------------------------------------------
# Backend-agnostic: second stub with different data
# ---------------------------------------------------------------------------

class AltStubBackend:
    """A different backend with different words — verifies GreekUtils is not hardcoded."""
    def paradigm(self, word, pos):
        if pos == 'noun' and word == 'βιβλίο':
            return {
                'neut': {
                    'sg': {'nom': {'βιβλίο'}, 'acc': {'βιβλίο'}, 'gen': {'βιβλίου'}},
                    'pl': {'nom': {'βιβλία'}, 'acc': {'βιβλία'}, 'gen': {'βιβλίων'}},
                }
            }
        return {}


def test_alt_backend_noun():
    gu2 = GreekUtils(AltStubBackend(), _mo, _pd_real)
    snap = _snap(
        ["βιβλίο", "βιβλίο", "βιβλίου", "βιβλία", "βιβλία", "βιβλίων"],
        test_word="το βιβλίο", is_pluralia_tantum=False,
        active_cases=[["sg","nom"],["sg","acc"],["sg","gen"],["pl","nom"],["pl","acc"],["pl","gen"]],
    )
    assert gu2.check_noun_test("το βιβλίο", snap, mode='simple') is True


def test_alt_backend_unknown_word():
    """Backend returning empty paradigm → check returns False gracefully."""
    gu2 = GreekUtils(AltStubBackend(), _mo, _pd_real)
    snap = _snap(
        ["something", "something", "something", "somethings", "somethings", "somethings"],
        test_word="η άγνωστο", is_pluralia_tantum=False,
        active_cases=[["sg","nom"],["sg","acc"],["sg","gen"],["pl","nom"],["pl","acc"],["pl","gen"]],
    )
    assert gu2.check_noun_test("η άγνωστο", snap, mode='simple') is False

"""Backend selection tests — explicit comparison of all named backends.

Named backends:
  backend="modern-greek"   → ModernGreekBackend  (language inferred: "el")
  backend="ancient-greek"  → AncientGreekBackend (language inferred: "grc")
  backend="unimorph"       → UniMorphBackend     (language required: "el" or "grc")

All backends are mocked — no TSV or model calls.
"""
from unittest.mock import MagicMock, patch

import pytest

import eee
import eee._registry as _reg
from eee._exceptions import UnsupportedLanguageError


def _mock_backend(result=None):
    m = MagicMock()
    m.inflect.return_value = result or {"mocked"}
    return m


VERB_FEATURES = {"Tense": "Pres", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"}
NOUN_FEATURES = {"Case": "Gen", "Number": "Sing"}


# ── el: modern-greek vs unimorph ─────────────────────────────────────────────


def test_el_modern_greek_vs_unimorph_verb():
    """backend='modern-greek' and backend='unimorph' are independent for el verb."""
    dedicated = _mock_backend({"dedicated_form"})
    eee.register_backend("el", dedicated, backend="modern-greek")

    result_mg = eee.inflect("ακούω", VERB_FEATURES, "verb", backend="modern-greek")
    with patch("eee.backends.unimorph._lookup", return_value={"unimorph_form"}):
        result_um = eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="unimorph")

    dedicated.inflect.assert_called_once()
    assert result_mg == {"dedicated_form"}
    assert result_um == {"unimorph_form"}
    assert result_mg != result_um


def test_el_modern_greek_language_inferred():
    """backend='modern-greek' infers language='el'; explicit language= also accepted."""
    dedicated = _mock_backend({"x"})
    eee.register_backend("el", dedicated, backend="modern-greek")

    # language inferred
    eee.inflect("ακούω", VERB_FEATURES, "verb", backend="modern-greek")
    # language explicit — same result
    eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="modern-greek")

    assert dedicated.inflect.call_count == 2


def test_el_unimorph_not_called_when_modern_greek_selected():
    """UniMorphBackend is not invoked when backend='modern-greek'."""
    dedicated = _mock_backend({"x"})
    eee.register_backend("el", dedicated, backend="modern-greek")

    with patch("eee.backends.unimorph._lookup") as mock_lookup:
        eee.inflect("ακούω", VERB_FEATURES, "verb", backend="modern-greek")

    mock_lookup.assert_not_called()


def test_el_modern_greek_not_called_when_unimorph_selected():
    """ModernGreekBackend is not invoked when backend='unimorph' is specified."""
    dedicated = _mock_backend()
    eee.register_backend("el", dedicated, backend="modern-greek")

    with patch("eee.backends.unimorph._lookup", return_value={"x"}):
        eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="unimorph")

    dedicated.inflect.assert_not_called()


# ── grc: ancient-greek vs unimorph ───────────────────────────────────────────


def test_grc_ancient_greek_vs_unimorph_noun():
    """backend='ancient-greek' and backend='unimorph' are independent for grc noun."""
    ancient = _mock_backend({"ancient_form"})
    eee.register_backend("grc", ancient, backend="ancient-greek")

    result_ag = eee.inflect("βοηθός", NOUN_FEATURES, "noun", backend="ancient-greek")
    with patch("eee.backends.unimorph._lookup", return_value={"unimorph_form"}):
        result_um = eee.inflect("βοηθός", NOUN_FEATURES, "noun", language="grc", backend="unimorph")

    ancient.inflect.assert_called_once()
    assert result_ag == {"ancient_form"}
    assert result_um == {"unimorph_form"}
    assert result_ag != result_um


def test_grc_ancient_greek_language_inferred():
    """backend='ancient-greek' infers language='grc'."""
    ancient = _mock_backend({"x"})
    eee.register_backend("grc", ancient, backend="ancient-greek")

    eee.inflect("βοηθός", NOUN_FEATURES, "noun", backend="ancient-greek")

    ancient.inflect.assert_called_once()


def test_grc_unimorph_raises_for_verbs():
    """UniMorph does not cover Ancient Greek verbs — PosNotSupportedError."""
    from eee._exceptions import PosNotSupportedError
    with pytest.raises(PosNotSupportedError):
        eee.inflect("λύω", VERB_FEATURES, "verb", language="grc", backend="unimorph")


# ── Named backend error handling ──────────────────────────────────────────────


def test_unknown_named_backend_raises():
    """Requesting an unregistered backend name raises UnsupportedLanguageError."""
    with pytest.raises(UnsupportedLanguageError):
        eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="nonexistent")


def test_unimorph_without_language_raises_value_error():
    """backend='unimorph' without language= raises ValueError (multi-language backend)."""
    with pytest.raises(ValueError, match="multiple languages"):
        eee.inflect("ακούω", VERB_FEATURES, "verb", backend="unimorph")


def test_named_backend_does_not_fall_through_to_fallback():
    """Fallback is not consulted when an explicit backend name is given."""
    fallback = _mock_backend()
    eee.set_fallback_backend(fallback)
    with pytest.raises(UnsupportedLanguageError):
        eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="nonexistent")
    fallback.inflect.assert_not_called()

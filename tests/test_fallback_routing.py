"""Fallback routing tests — all backends mocked, no real model calls."""
from unittest.mock import MagicMock, patch

import pytest

import eee
import eee._registry as _reg


def _mock_backend(result=None):
    m = MagicMock()
    m.inflect.return_value = result or {"mocked"}
    return m


VERB_FEATURES = {"Tense": "Pres", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"}


def test_el_uses_dedicated_not_fallback():
    dedicated = _mock_backend({"λύω"})
    fallback = _mock_backend()
    eee.register_backend("el", dedicated)
    eee.set_fallback_backend(fallback)
    eee.inflect("λύω", VERB_FEATURES, "verb", language="el")
    dedicated.inflect.assert_called_once()
    fallback.inflect.assert_not_called()


def test_el_unimorph_backend_kwarg():
    fallback = _mock_backend({"λύει"})
    eee.set_fallback_backend(fallback)
    with patch("eee.backends.unimorph._lookup", return_value={"ακούω"}):
        result = eee.inflect("λύω", VERB_FEATURES, "verb", language="el", backend="unimorph")
    fallback.inflect.assert_not_called()
    assert result == {"ακούω"}


def test_unknown_language_uses_fallback():
    fallback = _mock_backend({"x"})
    eee.set_fallback_backend(fallback)
    eee.inflect("foo", {}, "noun", language="xx")
    fallback.inflect.assert_called_once()


def test_grc_verb_uses_dedicated_not_fallback():
    dedicated = _mock_backend({"λύει"})
    fallback = _mock_backend()
    eee.register_backend("grc", dedicated)
    eee.set_fallback_backend(fallback)
    eee.inflect("λύω", VERB_FEATURES, "verb", language="grc")
    dedicated.inflect.assert_called_once()
    fallback.inflect.assert_not_called()


def test_register_default_backends_wires_fallback():
    with patch("eee.backends.unimorph._lookup", return_value={"λύει"}):
        eee.register_default_backends()
        from eee._exceptions import UnsupportedLanguageError
        try:
            eee.inflect("λύω", VERB_FEATURES, "verb", language="el", backend="unimorph")
        except UnsupportedLanguageError:
            pytest.fail("UnsupportedLanguageError raised — builtin not wired")


def test_el_unimorph_works_without_register_default_backends():
    """backend='unimorph' is a builtin — no register_default_backends() call needed."""
    with patch("eee.backends.unimorph._lookup", return_value={"ακούω"}):
        result = eee.inflect("λύω", VERB_FEATURES, "verb", language="el", backend="unimorph")
    assert result == {"ακούω"}

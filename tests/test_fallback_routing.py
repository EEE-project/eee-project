"""Fallback routing tests — all backends mocked, no real model calls."""
from unittest.mock import MagicMock

import pytest

import eee_project as eee
import eee_project._registry as _reg


def _mock_backend(result=None):
    m = MagicMock()
    m.inflect.return_value = result or {"mocked"}
    return m


VERB_FEATURES = {"Tense": "Pres", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"}


@pytest.fixture(autouse=True)
def reset_registry():
    registered_before = dict(_reg._registered)
    cache_before = dict(_reg._cache)
    fallback_before = _reg._fallback
    chains_before = {k: dict(v) for k, v in _reg._chains.items()}
    yield
    _reg._registered.clear()
    _reg._registered.update(registered_before)
    _reg._cache.clear()
    _reg._cache.update(cache_before)
    _reg._fallback = fallback_before
    _reg._chains.clear()
    _reg._chains.update(chains_before)


def test_el_uses_registered_not_fallback():
    dedicated = _mock_backend({"λύω"})
    fallback = _mock_backend()
    eee.register_backend("el", dedicated)
    eee.set_fallback_backend(fallback)
    eee.inflect("λύω", VERB_FEATURES, "verb", language="el")
    dedicated.inflect.assert_called_once()
    fallback.inflect.assert_not_called()


def test_unknown_language_uses_fallback():
    fallback = _mock_backend({"x"})
    eee.set_fallback_backend(fallback)
    eee.inflect("foo", {}, "noun", language="xx")
    fallback.inflect.assert_called_once()


def test_grc_uses_registered_not_fallback():
    dedicated = _mock_backend({"λύει"})
    fallback = _mock_backend()
    eee.register_backend("grc", dedicated)
    eee.set_fallback_backend(fallback)
    eee.inflect("λύω", VERB_FEATURES, "verb", language="grc")
    dedicated.inflect.assert_called_once()
    fallback.inflect.assert_not_called()


def test_named_backend_registered_explicitly():
    """Explicit register_backend() + named backend works without builtins."""
    unimorph = _mock_backend({"ακούω"})
    eee.register_backend("el", unimorph, backend="unimorph")
    result = eee.inflect("λύω", VERB_FEATURES, "verb", language="el", backend="unimorph")
    assert result == {"ακούω"}

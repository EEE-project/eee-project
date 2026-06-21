"""Backend selection tests — explicit named backends with mock backends."""
from unittest.mock import MagicMock

import pytest

import eee_project as eee
import eee_project._registry as _reg
from eee_project._exceptions import UnsupportedLanguageError


def _mock_backend(result=None):
    m = MagicMock()
    m.inflect.return_value = result or {"mocked"}
    return m


VERB_FEATURES = {"Tense": "Pres", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"}
NOUN_FEATURES = {"Case": "Gen", "Number": "Sing"}


@pytest.fixture(autouse=True)
def reset_registry():
    registered_before = dict(_reg._registered)
    cache_before = dict(_reg._cache)
    fallback_before = _reg._fallback
    yield
    _reg._registered.clear()
    _reg._registered.update(registered_before)
    _reg._cache.clear()
    _reg._cache.update(cache_before)
    _reg._fallback = fallback_before


def test_el_named_backends_are_independent():
    """backend='modern-greek' and backend='unimorph' are independent for el."""
    dedicated = _mock_backend({"dedicated_form"})
    unimorph = _mock_backend({"unimorph_form"})
    eee.register_backend("el", dedicated, backend="modern-greek")
    eee.register_backend("el", unimorph, backend="unimorph")

    result_mg = eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="modern-greek")
    result_um = eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="unimorph")

    dedicated.inflect.assert_called_once()
    unimorph.inflect.assert_called_once()
    assert result_mg == {"dedicated_form"}
    assert result_um == {"unimorph_form"}


def test_el_unimorph_not_called_when_modern_greek_selected():
    """UniMorphBackend is not invoked when backend='modern-greek'."""
    dedicated = _mock_backend({"x"})
    unimorph = _mock_backend()
    eee.register_backend("el", dedicated, backend="modern-greek")
    eee.register_backend("el", unimorph, backend="unimorph")

    eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="modern-greek")

    unimorph.inflect.assert_not_called()


def test_el_modern_greek_not_called_when_unimorph_selected():
    """ModernGreekBackend is not invoked when backend='unimorph'."""
    dedicated = _mock_backend()
    unimorph = _mock_backend({"x"})
    eee.register_backend("el", dedicated, backend="modern-greek")
    eee.register_backend("el", unimorph, backend="unimorph")

    eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="unimorph")

    dedicated.inflect.assert_not_called()


def test_grc_named_backends_are_independent():
    """backend='ancient-greek' and backend='unimorph' are independent for grc."""
    ancient = _mock_backend({"ancient_form"})
    unimorph = _mock_backend({"unimorph_form"})
    eee.register_backend("grc", ancient, backend="ancient-greek")
    eee.register_backend("grc", unimorph, backend="unimorph")

    result_ag = eee.inflect("βοηθός", NOUN_FEATURES, "noun", language="grc", backend="ancient-greek")
    result_um = eee.inflect("βοηθός", NOUN_FEATURES, "noun", language="grc", backend="unimorph")

    ancient.inflect.assert_called_once()
    unimorph.inflect.assert_called_once()
    assert result_ag == {"ancient_form"}
    assert result_um == {"unimorph_form"}


def test_unknown_named_backend_raises():
    """Requesting an unregistered backend name raises UnsupportedLanguageError."""
    with pytest.raises(UnsupportedLanguageError):
        eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="nonexistent")


def test_no_language_no_backend_raises():
    """Calls without language= and without a single-language backend raise ValueError."""
    with pytest.raises(ValueError, match="language is required"):
        eee.inflect("ακούω", VERB_FEATURES, "verb")


def test_multi_language_backend_without_language_raises():
    """backend='unimorph' has no single canonical language, so language= is required."""
    with pytest.raises(ValueError, match="language is required"):
        eee.inflect("ακούω", VERB_FEATURES, "verb", backend="unimorph")


def test_named_backend_does_not_fall_through_to_fallback():
    """Fallback is not consulted when an explicit backend name is given."""
    fallback = _mock_backend()
    eee.set_fallback_backend(fallback)
    with pytest.raises(UnsupportedLanguageError):
        eee.inflect("ακούω", VERB_FEATURES, "verb", language="el", backend="nonexistent")
    fallback.inflect.assert_not_called()

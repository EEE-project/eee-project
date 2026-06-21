"""Public API tests — eee.__init__ delegation and framework behaviour."""
import pytest

import eee_project as eee
import eee_project._registry as _reg
from eee_project._exceptions import UnsupportedLanguageError


# ── Fake backend ──────────────────────────────────────────────────────────────


class FakeBackend:
    language = "xx"

    def inflect(self, lemma, features, pos, **_kw):
        return {"fake"}


# ── Fixtures ──────────────────────────────────────────────────────────────────


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


# ── inflect() ─────────────────────────────────────────────────────────────────


def test_inflect_unknown_language_raises_unsupported():
    with pytest.raises(UnsupportedLanguageError):
        eee.inflect("hello", {}, "verb", language="xx-unknown")


def test_inflect_unsupported_error_accessible_from_eee_namespace():
    with pytest.raises(eee.UnsupportedLanguageError):
        eee.inflect("hello", {}, "verb", language="no-such-lang")


def test_inflect_routes_to_registered_backend():
    fake = FakeBackend()
    eee.register_backend("xx", fake)
    result = eee.inflect("word", {}, "verb", language="xx")
    assert result == {"fake"}


def test_inflect_routes_to_fallback():
    fake = FakeBackend()
    eee.set_fallback_backend(fake)
    result = eee.inflect("word", {}, "verb", language="zz-unknown")
    assert result == {"fake"}


def test_inflect_missing_language_raises_value_error():
    with pytest.raises(ValueError, match="language is required"):
        eee.inflect("hello", {}, "verb")


# ── supported_languages() ─────────────────────────────────────────────────────


def test_supported_languages_returns_dict():
    langs = eee.supported_languages()
    assert isinstance(langs, dict)
    for v in langs.values():
        assert isinstance(v, list)


def test_supported_languages_excludes_fallback():
    fake = FakeBackend()
    eee.set_fallback_backend(fake)
    assert "xx" not in eee.supported_languages()


def test_supported_languages_excludes_explicit_registrations():
    fake = FakeBackend()
    eee.register_backend("de", fake)
    assert "de" not in eee.supported_languages()


# ── Exception re-exports ──────────────────────────────────────────────────────


def test_unsupported_language_error_in_eee_namespace():
    assert hasattr(eee, "UnsupportedLanguageError")
    assert eee.UnsupportedLanguageError is UnsupportedLanguageError


def test_backend_load_error_in_eee_namespace():
    from eee_project._exceptions import BackendLoadError
    assert hasattr(eee, "BackendLoadError")
    assert eee.BackendLoadError is BackendLoadError


def test_ambiguous_pos_error_in_eee_namespace():
    from eee_project._exceptions import AmbiguousPOSError
    assert hasattr(eee, "AmbiguousPOSError")
    assert eee.AmbiguousPOSError is AmbiguousPOSError

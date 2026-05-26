"""Public API tests — eee.__init__ delegation and lazy-load guarantee."""
import subprocess
import sys

import pytest

import eee
import eee._registry as _reg
from eee._exceptions import UnsupportedLanguageError


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
    yield
    _reg._registered.clear()
    _reg._registered.update(registered_before)
    _reg._cache.clear()
    _reg._cache.update(cache_before)
    _reg._fallback = fallback_before


# ── inflect() ─────────────────────────────────────────────────────────────────


def test_inflect_routes_to_mg_backend():
    result = eee.inflect(
        "λύω",
        {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act", "Person": "1", "Number": "Sing"},
        "verb",
        language="el",
    )
    assert result == {"λύω"}


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


# ── supported_languages() ─────────────────────────────────────────────────────


def test_supported_languages_returns_dict():
    assert isinstance(eee.supported_languages(), dict)


def test_supported_languages_contains_el():
    assert "el" in eee.supported_languages()


def test_supported_languages_excludes_fallback():
    fake = FakeBackend()
    eee.set_fallback_backend(fake)
    assert "xx" not in eee.supported_languages()


# ── Exception re-exports ──────────────────────────────────────────────────────


def test_unsupported_language_error_in_eee_namespace():
    assert hasattr(eee, "UnsupportedLanguageError")
    assert eee.UnsupportedLanguageError is UnsupportedLanguageError


def test_backend_load_error_in_eee_namespace():
    from eee._exceptions import BackendLoadError
    assert hasattr(eee, "BackendLoadError")
    assert eee.BackendLoadError is BackendLoadError


def test_ambiguous_pos_error_in_eee_namespace():
    from eee._exceptions import AmbiguousPOSError
    assert hasattr(eee, "AmbiguousPOSError")
    assert eee.AmbiguousPOSError is AmbiguousPOSError


def test_supported_languages_excludes_explicit_registrations():
    fake = FakeBackend()
    eee.register_backend("de", fake)
    assert "de" not in eee.supported_languages()


# ── Lazy-load guarantee ───────────────────────────────────────────────────────


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
    )


def test_import_eee_does_not_load_inflexion_library():
    result = _run(
        "import eee; "
        "assert 'modern_greek_inflexion_eee' not in __import__('sys').modules, "
        "'library was eagerly imported'"
    )
    assert result.returncode == 0, result.stderr


def test_inflect_el_triggers_inflexion_library_import():
    result = _run(
        "import eee; "
        "eee.inflect('λύω', {'Tense':'Pres','Mood':'Ind','VerbForm':'Fin','Voice':'Act','Person':'1','Number':'Sing'}, 'verb', language='el'); "
        "assert 'modern_greek_inflexion_eee' in __import__('sys').modules, "
        "'library was not imported after inflect()'"
    )
    assert result.returncode == 0, result.stderr

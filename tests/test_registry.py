"""Registry unit tests — hand-rolled fakes, no Mock()."""
from unittest.mock import patch, MagicMock

import pytest

from eee._exceptions import BackendLoadError, UnsupportedLanguageError
from eee._registry import (
    get_backend,
    register_backend,
    set_fallback_backend,
    supported_languages,
)
import eee._registry as _reg


# ── Fake backends ─────────────────────────────────────────────────────────────


class FakeBackend:
    language = "xx"

    def inflect(self, lemma, features, pos):
        return {"fake"}

    def analyze(self, form, pos=None):
        return []


class AnotherFakeBackend:
    language = "yy"

    def inflect(self, lemma, features, pos):
        return {"another"}

    def analyze(self, form, pos=None):
        return []


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def reset_registry():
    """Restore registry state after each test."""
    registered_before = dict(_reg._registered)
    cache_before = dict(_reg._cache)
    fallback_before = _reg._fallback
    yield
    _reg._registered.clear()
    _reg._registered.update(registered_before)
    _reg._cache.clear()
    _reg._cache.update(cache_before)
    _reg._fallback = fallback_before


# ── Routing tests ─────────────────────────────────────────────────────────────


def test_registered_backend_is_called():
    fake = FakeBackend()
    register_backend("xx", fake)
    backend = get_backend("xx")
    assert backend is fake


def test_fallback_called_for_unregistered_language():
    fake = FakeBackend()
    set_fallback_backend(fake)
    backend = get_backend("zz-unknown")
    assert backend is fake


def test_no_backend_no_fallback_raises_unsupported():
    with pytest.raises(UnsupportedLanguageError):
        get_backend("no-such-lang")


def test_unsupported_error_contains_language_code():
    with pytest.raises(UnsupportedLanguageError) as exc_info:
        get_backend("zzz")
    assert "zzz" in str(exc_info.value)


def test_unsupported_error_contains_install_hint():
    with pytest.raises(UnsupportedLanguageError) as exc_info:
        get_backend("zzz")
    assert "register" in str(exc_info.value).lower()


# ── Entry point loading ───────────────────────────────────────────────────────


def test_entry_point_loaded_on_first_call():
    ep = MagicMock()
    ep.name = "tt"
    ep.load.return_value = FakeBackend

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        backend = get_backend("tt")
    assert isinstance(backend, FakeBackend)


def test_entry_point_cached_on_second_call():
    ep = MagicMock()
    ep.name = "tt"
    ep.load.return_value = FakeBackend

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        first = get_backend("tt")
        second = get_backend("tt")
    assert first is second
    assert ep.load.call_count == 1


def test_entry_point_load_import_error_raises_backend_load_error():
    ep = MagicMock()
    ep.name = "tt"
    ep.load.side_effect = ImportError("missing package")

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        with pytest.raises(BackendLoadError) as exc_info:
            get_backend("tt")
    assert exc_info.value.__cause__ is not None


def test_entry_point_instantiation_error_raises_backend_load_error():
    class BrokenBackend:
        language = "tt"

        def __init__(self):
            raise RuntimeError("broken")

        def inflect(self, lemma, features, pos): ...
        def analyze(self, form, pos=None): ...

    ep = MagicMock()
    ep.name = "tt"
    ep.load.return_value = BrokenBackend

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        with pytest.raises(BackendLoadError) as exc_info:
            get_backend("tt")
    assert exc_info.value.__cause__ is not None


# ── Registration behaviour ────────────────────────────────────────────────────


def test_register_overrides_builtin():
    fake = FakeBackend()
    register_backend("el", fake)
    assert get_backend("el") is fake


def test_register_idempotent_same_instance():
    fake = FakeBackend()
    register_backend("xx", fake)
    register_backend("xx", fake)
    assert get_backend("xx") is fake


def test_register_override_replaces_previous():
    fake_a = FakeBackend()
    fake_b = AnotherFakeBackend()
    register_backend("xx", fake_a)
    register_backend("xx", fake_b)
    assert get_backend("xx") is fake_b


# ── supported_languages() ─────────────────────────────────────────────────────


def test_supported_languages_contains_el():
    langs = supported_languages()
    assert "el" in langs


def test_supported_languages_returns_dict():
    assert isinstance(supported_languages(), dict)


def test_supported_languages_excludes_fallback():
    fake = FakeBackend()
    set_fallback_backend(fake)
    langs = supported_languages()
    assert "xx" not in langs


def test_supported_languages_includes_entry_point_code():
    ep = MagicMock()
    ep.name = "la"
    ep.value = "latin_eee:LatinBackend"

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        langs = supported_languages()
    assert "la" in langs


def test_supported_languages_builtin_wins_over_entry_point():
    ep = MagicMock()
    ep.name = "el"
    ep.value = "some_other:Backend"

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        langs = supported_languages()
    assert langs["el"] == "ModernGreekBackend"


# ── Resolution order ──────────────────────────────────────────────────────────


def test_registered_beats_builtin():
    fake = FakeBackend()
    register_backend("el", fake)
    assert get_backend("el") is fake


def test_builtin_beats_entry_point():
    ep = MagicMock()
    ep.name = "el"
    ep.load.return_value = FakeBackend

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        backend = get_backend("el")
    assert not isinstance(backend, FakeBackend)


def test_entry_point_beats_fallback():
    fallback = AnotherFakeBackend()
    set_fallback_backend(fallback)

    ep = MagicMock()
    ep.name = "tt"
    ep.load.return_value = FakeBackend

    with patch("importlib.metadata.entry_points", return_value=[ep]):
        backend = get_backend("tt")
    assert isinstance(backend, FakeBackend)


def test_fallback_beats_unsupported():
    fake = FakeBackend()
    set_fallback_backend(fake)
    backend = get_backend("no-such-lang")
    assert backend is fake

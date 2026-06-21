import copy
import pytest
from unittest.mock import MagicMock

import eee_project._registry as _reg
from eee_project._tag_registry import _clear_tag_registry


@pytest.fixture(autouse=True)
def reset_registry():
    registered_before = dict(_reg._registered)
    cache_before = dict(_reg._cache)
    fallback_before = _reg._fallback
    chains_before = copy.deepcopy(_reg._chains_default)
    yield
    _reg._registered.clear()
    _reg._registered.update(registered_before)
    _reg._cache.clear()
    _reg._cache.update(cache_before)
    _reg._fallback = fallback_before
    _reg._chains.clear()
    _reg._chains.update(chains_before)
    _clear_tag_registry()


# ── Shared mock helpers ───────────────────────────────────────────────────────


class MockBackend:
    """Simple backend stub returning fixed forms."""
    def __init__(self, forms: set[str]):
        self._forms = forms

    def inflect(self, lemma, features, pos, **kw) -> set[str]:
        return set(self._forms)


def mock_backend(forms: set[str]) -> object:
    """MagicMock backend returning fixed forms (for call-count assertions)."""
    b = MagicMock()
    b.inflect.return_value = forms
    return b


def corpus_backend(forms: set[str], lemmas: list[str]) -> object:
    """MagicMock backend returning fixed forms and lemmas."""
    b = MagicMock()
    b.inflect.return_value = forms
    b.list_lemmas.return_value = list(lemmas)
    return b


def register(lang: str, name: str, backend: object) -> None:
    """Register a mock backend under a named key."""
    _reg.register_backend(lang, backend, backend=name)

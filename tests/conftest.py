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


def _mock_backend(**method_returns) -> object:
    """MagicMock backend with each keyword set as that method's .return_value."""
    b = MagicMock()
    for method, value in method_returns.items():
        getattr(b, method).return_value = value
    return b


def mock_backend(forms: set[str]) -> object:
    """MagicMock backend returning fixed forms (for call-count assertions)."""
    return _mock_backend(inflect=forms)


def corpus_backend(forms: set[str], lemmas: list[str]) -> object:
    """MagicMock backend returning fixed forms and lemmas."""
    return _mock_backend(inflect=forms, list_lemmas=list(lemmas))


def analyze_backend(rows: list[dict]) -> object:
    """MagicMock backend returning fixed analyze() candidate rows."""
    return _mock_backend(analyze=list(rows))


def register(lang: str, name: str, backend: object) -> None:
    """Register a mock backend under a named key."""
    _reg.register_backend(lang, backend, backend=name)


# ── Shared GreekUtils stubs (mo_module / paradigm backend) ────────────────────


class StubMo:
    """Minimal marimo stub — only the parts GreekUtils touches."""
    class ui:
        @staticmethod
        def text(label=""): return label
        @staticmethod
        def array(items): return items
        @staticmethod
        def button(label="", on_click=None, kind="neutral", disabled=False):
            import types
            return types.SimpleNamespace(label=label, on_click=on_click, kind=kind, disabled=disabled, value=0)
    @staticmethod
    def md(s): return s


class StubMoLayout:
    """Mixin: md/hstack/vstack/callout/accordion, shared by marimo stubs that
    need layout (word-drill/word-quiz tests) on top of their own distinct
    `ui` namespace."""
    @staticmethod
    def md(s): return s
    @staticmethod
    def hstack(items, **kwargs): return list(items)
    @staticmethod
    def vstack(items, **kwargs): return list(items)
    @staticmethod
    def callout(content, kind="info"): return ("callout", kind, content)
    @staticmethod
    def accordion(sections, **kwargs): return sections


class StubBackend:
    """Minimal morphology backend stub for GreekUtils(backend, mo, ...).

    paradigm() delegates to an injected callable, defaulting to always-empty —
    pass paradigm_fn=(word, pos) -> dict for tests that need real paradigm shapes.
    """
    def __init__(self, paradigm_fn=None):
        self._paradigm_fn = paradigm_fn or (lambda word, pos: {})

    def paradigm(self, word, pos):
        return self._paradigm_fn(word, pos)

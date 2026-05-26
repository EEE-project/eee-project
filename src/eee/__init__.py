"""eee — language-agnostic morphology umbrella for the EEE project."""
from __future__ import annotations

from eee import _registry
from eee._exceptions import (
    AmbiguousPOSError,
    BackendLoadError,
    UnsupportedLanguageError,
)

__version__ = "0.4.0"

__all__ = [
    "inflect",
    "list_lemmas",
    "register_backend",
    "set_fallback_backend",
    "supported_languages",
    "register_default_backends",
    "language_info",
    "UnsupportedLanguageError",
    "BackendLoadError",
    "AmbiguousPOSError",
]


def inflect(
    lemma: str,
    features: dict[str, str],
    pos: str,
    language: str | None = None,
    backend: str | None = None,
) -> set[str]:
    """Return inflected forms for lemma matching the given UD feature bundle.

    Parameters
    ----------
    lemma:    base form of the word
    features: UD FEATS dict, e.g. {"Tense": "Pres", "Mood": "Ind", "Person": "1"}
    pos:      part of speech — "verb", "noun", "adjective", "adverb"
    language: IETF language tag — "el", "grc", etc. May be omitted when backend
              maps to exactly one language (e.g. backend="modern-greek" → "el").
    backend:  named backend variant, e.g. "unimorph". None selects the default.

    Raises
    ------
    UnsupportedLanguageError  if language cannot be resolved or no backend found
    BackendLoadError          if a backend is found but fails to load
    """
    lang = _registry.resolve_language(language, backend)
    return _registry.get_backend(lang, backend=backend).inflect(lemma, features, pos)


def list_lemmas(pos: str, language: str | None = None, backend: str | None = None) -> list[str]:
    """Return lemmas available in the backend's corpus for the given POS.

    Returns [] for algorithm-based backends that have no finite vocabulary
    (e.g. ModernGreekBackend), or when no corpus data is available.
    """
    lang = _registry.resolve_language(language, backend)
    b = _registry.get_backend(lang, backend=backend)
    fn = getattr(b, "list_lemmas", None)
    if fn is None:
        return []
    return fn(pos)


def register_backend(code: str, instance: object, backend: str | None = None) -> None:
    """Register or override a backend instance for a language code.

    Pass backend='name' to register a named variant alongside the default.
    Idempotent: calling twice with the same instance produces the same state.
    Overrides any existing registration, including built-ins.
    """
    _registry.register_backend(code, instance, backend=backend)


def set_fallback_backend(instance: object) -> None:
    """Register a catch-all backend for unregistered languages.

    Not included in supported_languages().
    """
    _registry.set_fallback_backend(instance)


def register_default_backends() -> None:
    """Register UniMorphBackend as the fallback for languages without a dedicated backend.

    Call once at application startup. Tests that need isolated registry state
    should NOT call this.
    """
    from eee.backends.unimorph import UniMorphBackend
    _registry.set_fallback_backend(UniMorphBackend())


def language_info(code: str) -> dict | None:
    """Return the manifest entry for the given EEE language code, or None if unknown."""
    from eee.backends.unimorph import _load_manifest
    return _load_manifest().get("languages", {}).get(code)


def supported_languages() -> dict[str, str]:
    """Return a mapping of language code → backend class name.

    Includes built-in backends and discovered entry-point backends.
    Does NOT include the fallback backend or explicitly registered backends.
    """
    return _registry.supported_languages()

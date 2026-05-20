"""eee — language-agnostic morphology umbrella for the EEE project."""
from __future__ import annotations

from eee import _registry
from eee._exceptions import (
    AnalysisNotSupportedError,
    AmbiguousPOSError,
    BackendLoadError,
    UnsupportedLanguageError,
)

__version__ = "0.2.0"

__all__ = [
    "inflect",
    "analyze",
    "register_backend",
    "set_fallback_backend",
    "supported_languages",
    "UnsupportedLanguageError",
    "BackendLoadError",
    "AnalysisNotSupportedError",
    "AmbiguousPOSError",
]


def inflect(lemma: str, features: dict[str, str], pos: str, language: str) -> set[str]:
    """Return inflected forms for lemma matching the given UD feature bundle.

    Parameters
    ----------
    lemma:    base form of the word
    features: UD FEATS dict, e.g. {"Tense": "Pres", "Mood": "Ind", "Person": "1"}
    pos:      part of speech — "verb", "noun", "adjective", "adverb"
    language: IETF language tag — "el", "grc", "la", etc. Required; no default.

    Raises
    ------
    UnsupportedLanguageError  if no backend is registered for language
    BackendLoadError          if a backend is found but fails to load
    """
    return _registry.get_backend(language).inflect(lemma, features, pos)


def analyze(form: str, language: str, pos: str | None = None) -> list[dict[str, str]]:
    """Return possible morphological analyses for an inflected form.

    Each analysis is a UD FEATS dict. Returns a list because morphological
    ambiguity is common.

    Raises
    ------
    UnsupportedLanguageError      if no backend is registered for language
    AnalysisNotSupportedError     if the backend does not implement analysis
    """
    return _registry.get_backend(language).analyze(form, pos)


def register_backend(code: str, instance: object) -> None:
    """Register or override a backend instance for a language code.

    Idempotent: calling twice with the same instance produces the same state.
    Overrides any existing registration, including built-ins.
    """
    _registry.register_backend(code, instance)


def set_fallback_backend(instance: object) -> None:
    """Register a catch-all backend for unregistered languages.

    Not included in supported_languages().
    """
    _registry.set_fallback_backend(instance)


def supported_languages() -> dict[str, str]:
    """Return a mapping of language code → backend class name.

    Includes built-in backends and discovered entry-point backends.
    Does NOT include the fallback backend or explicitly registered backends.
    """
    return _registry.supported_languages()

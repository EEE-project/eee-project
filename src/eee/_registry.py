"""Language registry — routes language codes to backend instances.

Module-level state (_registered, _cache, _fallback) is not protected by locks.
For concurrent use, initialize from a single thread before spawning workers.
"""
from __future__ import annotations

import importlib
import importlib.metadata

from eee._exceptions import BackendLoadError, UnsupportedLanguageError

# ── Built-in backends (lazy-loaded on first use) ───────────────────────────────

_BUILTIN_BACKENDS: dict[str, str] = {
    "el": "eee.backends.modern_greek:ModernGreekBackend",
}

# ── Module-level state ────────────────────────────────────────────────────────

_registered: dict[str, object] = {}   # explicit registrations via register_backend()
_cache: dict[str, object] = {}         # lazy-loaded from builtins or entry points
_fallback: object | None = None        # catch-all backend


# ── Internal helpers ──────────────────────────────────────────────────────────


def _load_class(class_path: str) -> type:
    """Import and return a class from 'module.path:ClassName'."""
    module_path, class_name = class_path.split(":", 1)
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def _load_from_entry_points(language_code: str) -> object | None:
    """Search entry points for the given language code and instantiate if found."""
    try:
        eps = importlib.metadata.entry_points(group="eee.backends.v1")
    except Exception:
        # metadata subsystem may raise on partial installs — treat as "no entry points"
        return None

    for ep in eps:
        if ep.name == language_code:
            try:
                cls = ep.load()
                instance = cls()
            except Exception as exc:
                raise BackendLoadError(language_code, exc) from exc
            _cache[language_code] = instance
            return instance

    return None


# ── Public API ────────────────────────────────────────────────────────────────


def get_backend(language_code: str) -> object:
    """Resolve and return a backend instance for the given language code.

    Resolution order:
      1. Explicit registrations (_registered)
      2. Cached lazy-loaded instances (_cache)
      3. Built-in backends (_BUILTIN_BACKENDS)
      4. Entry points (group='eee.backends.v1')
      5. Fallback backend (_fallback)
      6. Raise UnsupportedLanguageError

    Raises:
        UnsupportedLanguageError: No backend found for the language code.
        BackendLoadError: Backend found but failed to load or instantiate.
    """
    if language_code in _registered:
        return _registered[language_code]

    if language_code in _cache:
        return _cache[language_code]

    if language_code in _BUILTIN_BACKENDS:
        try:
            cls = _load_class(_BUILTIN_BACKENDS[language_code])
            instance = cls()
        except Exception as exc:
            raise BackendLoadError(language_code, exc) from exc
        _cache[language_code] = instance
        return instance

    ep_instance = _load_from_entry_points(language_code)
    if ep_instance is not None:
        return ep_instance

    if _fallback is not None:
        return _fallback

    raise UnsupportedLanguageError(language_code)


def register_backend(language_code: str, instance: object) -> None:
    """Register a backend instance for a language code.

    Overrides any existing registration (builtin, cached, or previously
    registered). Calling again with the same instance is safe; the dict
    entry is simply overwritten.
    """
    _cache.pop(language_code, None)
    _registered[language_code] = instance


def set_fallback_backend(instance: object) -> None:
    """Set the catch-all backend for unregistered languages."""
    global _fallback
    _fallback = instance


def supported_languages() -> dict[str, str]:
    """Return mapping of language code → backend class name.

    Includes built-ins and discovered entry points without triggering lazy loads.
    Does NOT include the fallback backend or explicitly registered backends.
    """
    result: dict[str, str] = {}

    for code, class_path in _BUILTIN_BACKENDS.items():
        result[code] = class_path.split(":")[-1]

    try:
        eps = importlib.metadata.entry_points(group="eee.backends.v1")
        for ep in eps:
            if ep.name not in result:
                result[ep.name] = ep.value
    except Exception:
        pass

    return result

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
    "el":                "eee.backends.modern_greek:ModernGreekBackend",
    "el:modern-greek":   "eee.backends.modern_greek:ModernGreekBackend",
    "el:unimorph":       "eee.backends.unimorph:UniMorphBackend",
    # ancient-greek-morphology-eee is an optional package — soft import
    "grc:ancient-greek": "ancient_greek_morphology_eee:AncientGreekBackend",
    "grc:unimorph":      "eee.backends.unimorph:UniMorphBackend",
}

# Extra kwargs passed to the constructor when instantiating builtin backends.
_BUILTIN_BACKEND_KWARGS: dict[str, dict] = {
    "el:unimorph":  {"language": "el"},
    "grc:unimorph": {"language": "grc"},
}

# Backend names that map to exactly one language — language= can be inferred.
# Built from _BUILTIN_BACKENDS: any "lang:name" key where "name" appears for
# only one language. "unimorph" is excluded because it covers both el and grc.
def _build_single_language_map() -> dict[str, str]:
    langs_by_backend: dict[str, set[str]] = {}
    for key in _BUILTIN_BACKENDS:
        if ":" in key:
            lang, name = key.split(":", 1)
            langs_by_backend.setdefault(name, set()).add(lang)
    return {name: next(iter(langs)) for name, langs in langs_by_backend.items() if len(langs) == 1}

_SINGLE_LANGUAGE_BACKENDS: dict[str, str] = _build_single_language_map()
# {"modern-greek": "el", "ancient-greek": "grc"}

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


def resolve_language(language_code: str | None, backend: str | None) -> str:
    """Return a concrete language code, inferring from backend name if needed.

    If language_code is given, returns it unchanged.
    If language_code is None and backend maps to exactly one language, infers it.
    Otherwise raises UnsupportedLanguageError.
    """
    if language_code is not None:
        return language_code
    if backend is None:
        raise ValueError("language is required when backend is not specified")
    lang = _SINGLE_LANGUAGE_BACKENDS.get(backend)
    if lang is None:
        raise ValueError(
            f"backend={backend!r} supports multiple languages; specify language="
        )
    return lang


def get_backend(language_code: str, backend: str | None = None) -> object:
    """Resolve and return a backend instance for the given language code.

    Resolution order (backend=None):
      1. Explicit registrations (_registered)
      2. Cached lazy-loaded instances (_cache)
      3. Built-in backends (_BUILTIN_BACKENDS)
      4. Entry points (group='eee.backends.v1')
      5. Fallback backend (_fallback)
      6. Raise UnsupportedLanguageError

    With backend='name', only steps 1-3 are tried (no entry-point or fallback
    search); raises UnsupportedLanguageError if the named backend is not found.
    ModuleNotFoundError during builtin load is treated as UnsupportedLanguageError
    (soft import — optional packages that are not installed are silently absent).

    Raises:
        UnsupportedLanguageError: No backend found for the language code.
        BackendLoadError: Backend found but failed to load or instantiate.
    """
    key = f"{language_code}:{backend}" if backend else language_code

    if key in _registered:
        return _registered[key]

    if key in _cache:
        return _cache[key]

    if key in _BUILTIN_BACKENDS:
        try:
            cls = _load_class(_BUILTIN_BACKENDS[key])
            instance = cls(**_BUILTIN_BACKEND_KWARGS.get(key, {}))
        except ModuleNotFoundError:
            # Optional package not installed — fall through as if not registered
            pass
        except Exception as exc:
            raise BackendLoadError(language_code, exc) from exc
        else:
            _cache[key] = instance
            return instance

    if backend is not None:
        raise UnsupportedLanguageError(language_code)

    ep_instance = _load_from_entry_points(language_code)
    if ep_instance is not None:
        return ep_instance

    if _fallback is not None:
        return _fallback

    raise UnsupportedLanguageError(language_code)


def register_backend(language_code: str, instance: object, backend: str | None = None) -> None:
    """Register a backend instance for a language code.

    Pass backend='name' to register a named variant alongside the default.
    Overrides any existing registration (builtin, cached, or previously
    registered). Calling again with the same instance is safe.
    """
    key = f"{language_code}:{backend}" if backend else language_code
    _cache.pop(key, None)
    _registered[key] = instance


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

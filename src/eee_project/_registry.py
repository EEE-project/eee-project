"""Language registry — routes language codes to backend instances.

Module-level state (_registered, _cache, _fallback, _chains) is not protected by locks.
Initialize chains from a single thread before spawning workers.
"""
from __future__ import annotations

import importlib.metadata
import importlib.resources

import yaml

from eee_project._exceptions import BackendLoadError, UnsupportedLanguageError

# No built-in backends — all backends are optional external packages.
# Install a backend package (e.g. modern-greek-backend-eee) and call
# register_backend() + set_chain() to configure it.

# ── Module-level state ────────────────────────────────────────────────────────

_registered: dict[str, object] = {}   # explicit registrations via register_backend()
_cache: dict[str, object] = {}         # lazy-loaded from entry points
_fallback: object | None = None        # catch-all backend
# _chains and _chains_default are assigned after _load_yaml_data() is defined.


# ── Internal helpers ──────────────────────────────────────────────────────────


def _load_ep_instance(group: str, ep_name: str, cache_key: str, error_code: str) -> object | None:
    """Load and instantiate the first entry point matching ep_name in group.

    Caches the result under cache_key and returns it, or returns None if not found.
    """
    try:
        eps = importlib.metadata.entry_points(group=group)
    except Exception:
        return None
    for ep in eps:
        if ep.name == ep_name:
            try:
                cls = ep.load()
                instance = cls()
            except Exception as exc:
                raise BackendLoadError(error_code, exc) from exc
            _cache[cache_key] = instance
            return instance
    return None


def _load_from_entry_points(language_code: str) -> object | None:
    """Search eee_project.backends.v1 for language_code and instantiate if found."""
    instance = _load_ep_instance(
        "eee_project.backends.v1", language_code, language_code, language_code
    )
    if instance is not None:
        alias = _lang_to_default.get(language_code)
        if alias:
            _cache[f"{language_code}:{alias}"] = instance
    return instance


def _load_named_from_entry_points(language_code: str, name: str) -> object | None:
    """Search eee_project.named_backends.v1 for name and instantiate for language_code.

    If name is the canonical default backend for language_code, delegates to
    _load_from_entry_points to share the same instance (avoids double instantiation).
    """
    if _lang_to_default.get(language_code) == name:
        return _load_from_entry_points(language_code)
    return _load_ep_instance(
        "eee_project.named_backends.v1", name, f"{language_code}:{name}", name
    )


def _load_yaml_data() -> tuple[dict[str, str], dict[str, str], dict[str, dict], dict]:
    """Read languages.yaml once and return (lang_to_default, default_to_lang, chains, raw_manifest).

    raw_manifest is the parsed YAML document, kept around so other modules (e.g.
    language_info()) can read it without re-reading and re-parsing the file.

    Returns empty dicts on any error so a missing or corrupt data file does not
    abort import eee.
    """
    try:
        data_path = importlib.resources.files("eee_project.data").joinpath("languages.yaml")
        text = data_path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
    except (OSError, yaml.YAMLError):
        return {}, {}, {}, {}

    lang_to_default: dict[str, str] = {}
    default_to_lang: dict[str, str] = {}
    chains: dict[str, dict] = {}

    try:
        for code, info in data.get("languages", {}).items():
            default = info.get("default_backend")
            if default:
                lang_to_default[code] = default
                default_to_lang[default] = code
            chain_list = info.get("default_chain")
            if chain_list:
                chains[code] = {"backends": list(chain_list), "pre_hook": None, "post_hook": None}
    except (TypeError, AttributeError) as exc:
        import warnings
        warnings.warn(f"eee: malformed languages.yaml — {exc}", stacklevel=2)
        return {}, {}, {}, {}

    return lang_to_default, default_to_lang, chains, data


_lang_to_default, _default_to_lang, _chains_default, _raw_manifest = _load_yaml_data()
_chains = {k: dict(v) for k, v in _chains_default.items()}


# ── Public API ────────────────────────────────────────────────────────────────


def resolve_language(language_code: str | None, backend: str | None) -> str:
    """Return a concrete language code.

    If language_code is given, returns it unchanged.
    If language_code is None and backend is a known canonical alias, infers
    the language from the alias (e.g. backend="modern-greek" -> "el").
    Otherwise raises ValueError.
    """
    if language_code is not None:
        return language_code
    if backend is not None:
        lang = _default_to_lang.get(backend)
        if lang is not None:
            return lang
    raise ValueError("language is required")


def get_backend(language_code: str, backend: str | None = None) -> object:
    """Resolve and return a backend instance for the given language code.

    Resolution order (backend=None):
      1. Explicit registrations (_registered)
      2. Cached lazy-loaded instances (_cache)
      3. Entry points (group='eee_project.backends.v1')
      4. Fallback backend (_fallback)
      5. Raise UnsupportedLanguageError

    With backend='name', steps 1-3 are tried using the named_backends.v1 entry
    point group; raises UnsupportedLanguageError if the named backend is not found.

    Raises:
        UnsupportedLanguageError: No backend found for the language code.
        BackendLoadError: Backend found but failed to load or instantiate.
    """
    key = f"{language_code}:{backend}" if backend else language_code

    if key in _registered:
        return _registered[key]

    if key in _cache:
        return _cache[key]

    if backend is not None:
        named = _load_named_from_entry_points(language_code, backend)
        if named is not None:
            return named
        raise UnsupportedLanguageError(language_code, backend=backend)

    ep_instance = _load_from_entry_points(language_code)
    if ep_instance is not None:
        return ep_instance

    if _fallback is not None:
        return _fallback

    raise UnsupportedLanguageError(language_code)


def register_backend(language_code: str, instance: object, backend: str | None = None) -> None:
    """Register a backend instance for a language code.

    Pass backend='name' to register a named variant alongside the default.
    Overrides any existing registration, including cached entry-point instances.
    Calling again with the same instance is safe.
    """
    key = f"{language_code}:{backend}" if backend else language_code
    _cache.pop(key, None)
    _registered[key] = instance


def set_fallback_backend(instance: object) -> None:
    """Set the catch-all backend for unregistered languages."""
    global _fallback
    _fallback = instance


def supported_languages() -> dict[str, list[str]]:
    """Return mapping of language code → list of entry point values for discovered backends.

    Includes all entry-point backends without triggering lazy loads. Multiple backends
    may register for the same language code (e.g. dedicated + unimorph); all are listed.
    Does NOT include explicitly registered backends or the fallback backend.
    """
    result: dict[str, list[str]] = {}
    try:
        eps = importlib.metadata.entry_points(group="eee_project.backends.v1")
        for ep in eps:
            result.setdefault(ep.name, []).append(ep.value)
    except Exception:
        pass
    return result


# ── Chain configuration ────────────────────────────────────────────────────────


def set_chain(
    language: str,
    backends: list[str],
    pre_hook=None,
    post_hook=None,
) -> None:
    """Register an ordered chain of backends for language.

    Overwrites any existing chain, including YAML defaults.
    Raises ValueError for an empty backend list. Backend names are stored
    without validation and resolved lazily at inflect() time.
    """
    if not backends:
        raise ValueError("Chain must contain at least one backend")
    _chains[language] = {"backends": list(backends), "pre_hook": pre_hook, "post_hook": post_hook}


def get_chain(language: str) -> list[str]:
    """Return the current chain backends for language, or [] if none configured."""
    entry = _chains.get(language)
    return list(entry["backends"]) if entry else []


def get_chain_entry(language: str) -> dict | None:
    """Return the full chain entry for language (backends + hooks), or None."""
    return _chains.get(language)


def language_info(code: str) -> dict | None:
    """Return the manifest entry for the given EEE language code, or None."""
    return _raw_manifest.get("languages", {}).get(code)

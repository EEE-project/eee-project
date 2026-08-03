"""eee — language-agnostic morphology umbrella for the EEE project."""
from __future__ import annotations

from eee_project import _registry
from eee_project._registry import set_chain, get_chain, get_chain_entry
from eee_project._exceptions import (
    AmbiguousPOSError,
    BackendLoadError,
    FeatureNotSupportedError,
    PosNotSupportedError,
    UnsupportedLanguageError,
)
from eee_project._results import InflectResult, LemmaEntry, AnalysisEntry
from eee_project._hooks import HookContext, PreHook, PostHook
from eee_project._slot_template import SlotTemplate, SupportsSlotTemplates
from eee_project._tag_registry import register_tag_type
from eee_project._grammar_fmt import fmt_ud_feats
from eee_project.notebook_utils import (
    GreekUtils, GreekConfig, MODERN_GREEK, ANCIENT_GREEK,
    eee_topbar, eee_footer, magnify_image, strip_diacritics, greek_compare,
    load_ga_config, ConfigStore,
    build_grc_paradigm_table, build_modern_paradigm_table, build_grc_lexicon_tabs,
    make_paradigm_form, interactive_text, setup_ancient_greek, add_labels,
    filter_grc_quiz_words, grc_coverage_words, grc_lexicon_sources, norm_grc_surface, resolve_clicked_word,
    parse_stanza_text, parse_stanza_translations,
    LEXICON_TAG_POS, LEXICON_TAG_POS_ALIASES, TRANSLATION_PRESENCE_CONTENT_POS,
    _INC as increment_counter,
)

__version__ = "1.2.0"

_UNSET = object()  # sentinel distinguishing "not provided" from explicit None


def _eff_hook(hook, default):
    """Resolve an _UNSET hook sentinel: _UNSET → default, explicit value → that value."""
    return default if hook is _UNSET else hook


def _validate_dispatch_args(backend: str | None, chain: list | None) -> None:
    if backend is not None and chain is not None:
        raise ValueError("backend= and chain= are mutually exclusive")
    if chain is not None and not chain:
        raise ValueError("chain= must not be empty")

__all__ = [
    "inflect",
    "list_lemmas",
    "register_backend",
    "set_fallback_backend",
    "supported_languages",
    "language_info",
    "UnsupportedLanguageError",
    "BackendLoadError",
    "AmbiguousPOSError",
    "PosNotSupportedError",
    "FeatureNotSupportedError",
    "InflectResult",
    "LemmaEntry",
    "AnalysisEntry",
    "analyze",
    "analyze_traced",
    "HookContext",
    "PreHook",
    "PostHook",
    "set_chain",
    "get_chain",
    "inflect_traced",
    "list_lemmas_traced",
    "SlotTemplate",
    "SupportsSlotTemplates",
    "register_tag_type",
    "get_slot_templates",
    "inflect_slot",
    "GreekUtils",
    "GreekConfig",
    "MODERN_GREEK",
    "ANCIENT_GREEK",
    "eee_topbar",
    "eee_footer",
    "magnify_image",
    "strip_diacritics",
    "greek_compare",
    "fmt_ud_feats",
    "load_ga_config",
    "ConfigStore",
    "build_grc_paradigm_table",
    "build_modern_paradigm_table",
    "build_grc_lexicon_tabs",
    "make_paradigm_form",
    "interactive_text",
    "setup_ancient_greek",
    "add_labels",
    "filter_grc_quiz_words",
    "grc_coverage_words",
    "grc_lexicon_sources",
    "norm_grc_surface",
    "resolve_clicked_word",
    "parse_stanza_text",
    "parse_stanza_translations",
    "increment_counter",
    "LEXICON_TAG_POS",
    "LEXICON_TAG_POS_ALIASES",
    "TRANSLATION_PRESENCE_CONTENT_POS",
]


def _resolve_chain_args(
    lang: str,
    chain: list[str] | None,
    pre_hook,
    post_hook,
) -> tuple[list[str], object, object]:
    """Return (effective_backends, effective_pre, effective_post) for chain dispatch.

    _UNSET means the caller did not pass a hook — inherit the registered chain hook.
    None means the caller explicitly wants no hook — suppress any registered hook.
    """
    if chain is not None:
        return chain, _eff_hook(pre_hook, None), _eff_hook(post_hook, None)
    entry = get_chain_entry(lang) or {}
    return (entry.get("backends", []),
            _eff_hook(pre_hook, entry.get("pre_hook")),
            _eff_hook(post_hook, entry.get("post_hook")))


def _run_single_backend(
    lang: str, key: str, backend_instance: object,
    lemma: str, features: "dict[str, str] | str", pos: str,
    pre_hook, post_hook,
) -> set[str]:
    """Apply pre/post hooks around one backend.inflect() call.

    Shared by the named-backend path (_run_named_backend) and the no-chain
    default-backend path in inflect_traced() — both call exactly one backend,
    unlike BackendChain which iterates a list and silently skips backends
    that fail to load or raise (wrong here: an explicit backend= or the
    resolved default backend must propagate failures, not be swallowed).
    """
    _pre = _eff_hook(pre_hook, None)
    _post = _eff_hook(post_hook, None)
    _lemma, _features, _pos = lemma, features, pos
    if _pre is not None:
        _ctx = HookContext(lemma=_lemma, features=_features, pos=_pos,
                           language=lang, tried=[], stop="first")
        _lemma, _features, _pos = _pre(_lemma, _features, _pos, _ctx)
    result = set(backend_instance.inflect(_lemma, _features, _pos, language=lang))
    if _post is not None:
        _ctx = HookContext(lemma=_lemma, features=_features, pos=_pos,
                           language=lang, tried=[key], stop="first")
        result = set(_post(result, _ctx))
    return result


def _run_named_backend(
    lang: str, backend: str, lemma: str, features: "dict[str, str] | str", pos: str,
    pre_hook, post_hook,
) -> tuple[set[str], str]:
    """Run a single named backend with optional pre/post hooks. Returns (result, key)."""
    key = f"{lang}:{backend}"
    result = _run_single_backend(
        lang, key, _registry.get_backend(lang, backend=backend),
        lemma, features, pos, pre_hook, post_hook,
    )
    return result, key


def inflect(
    lemma: str,
    features: "dict[str, str] | str",
    pos: str,
    language: str | None = None,
    backend: str | None = None,
    chain: list[str] | None = None,
    pre_hook=_UNSET,
    post_hook=_UNSET,
) -> set[str]:
    """Return inflected forms for lemma matching the given UD feature bundle.

    Parameters
    ----------
    lemma:     base form of the word
    features:  UD FEATS dict, e.g. {"Tense": "Pres", "Mood": "Ind", "Person": "1"},
               or a raw backend tag string (e.g. "N;NOM;SG") for direct index lookup.
               When str, all backends in the chain receive the str unchanged; backends
               that do not handle str will raise. Use inflect_slot() for raw-tag dispatch.
    pos:       part of speech — "verb", "noun", "adjective", "adverb"
    language:  IETF language tag — "el", "grc", etc. Always required.
    backend:   named backend variant, e.g. "unimorph". None selects the default.
               Mutually exclusive with chain=.
    chain:     per-call ordered list of backend short names. Overrides the registered
               chain for this call only. Mutually exclusive with backend=.
    pre_hook:  callable(lemma, features, pos, ctx) -> (lemma, features, pos), or None
               to suppress any registered chain hook for this call.
    post_hook: callable(forms, ctx) -> set[str], or None to suppress.

    Raises
    ------
    ValueError                if both backend= and chain= are provided, or chain=[].
    UnsupportedLanguageError  if language cannot be resolved or no backend found
    BackendLoadError          if a backend is found but fails to load
    """
    return inflect_traced(
        lemma, features, pos, language=language, backend=backend, chain=chain,
        pre_hook=pre_hook, post_hook=post_hook,
    ).forms


def inflect_traced(
    lemma: str,
    features: "dict[str, str] | str",
    pos: str,
    language: str | None = None,
    backend: str | None = None,
    chain: list[str] | None = None,
    stop: str = "first",
    pre_hook=_UNSET,
    post_hook=_UNSET,
) -> InflectResult:
    """Return inflected forms with full chain attribution metadata.

    Unlike inflect(), always returns an InflectResult with .forms, .source, and
    .tried. When backend= is given, treats it as a one-element chain so the result
    carries correct source/tried attribution. backend= and chain= are mutually
    exclusive.
    """
    _validate_dispatch_args(backend, chain)

    lang = _registry.resolve_language(language, backend)

    if backend is not None:
        result, key = _run_named_backend(lang, backend, lemma, features, pos, pre_hook, post_hook)
        source = key if result else None
        return InflectResult(forms=result, source=source, tried=[key], by_backend={key: set(result)})

    effective_backends, effective_pre, effective_post = _resolve_chain_args(
        lang, chain, pre_hook, post_hook
    )

    if effective_backends:
        from eee_project._chain import BackendChain
        return BackendChain(
            language=lang, backends=effective_backends, stop=stop,
            pre_hook=effective_pre, post_hook=effective_post,
        ).run(lemma, features, pos)

    # No-chain single-backend path — apply per-call hooks if provided
    backend_key = f"{lang}:default"
    result = _run_single_backend(
        lang, backend_key, _registry.get_backend(lang),
        lemma, features, pos, effective_pre, effective_post,
    )
    source = backend_key if result else None
    return InflectResult(forms=result, source=source, tried=[backend_key], by_backend={backend_key: set(result)})


def _chain_walk_traced(lang: str, backend: str | None, method_name: str, arg, entry_ctor):
    """Query method_name(arg) on each backend in the chain (or an explicit backend=).

    Shared by list_lemmas_traced() and analyze_traced() -- same three-branch
    shape (explicit backend= / no chain registered / chain loop), differing
    only in which backend method to call, what argument it takes, and how to
    wrap each raw result item. entry_ctor(item, source_key) builds one entry.
    Backends without method_name are silently skipped. Duplicates across
    backends are NOT collapsed.
    """
    if backend is not None:
        b = _registry.get_backend(lang, backend=backend)
        fn = getattr(b, method_name, None)
        if fn is None:
            return []
        key = f"{lang}:{backend}"
        return [entry_ctor(item, key) for item in fn(arg)]

    chain = _registry.get_chain(lang)
    if not chain:
        b = _registry.get_backend(lang)
        fn = getattr(b, method_name, None)
        if fn is None:
            return []
        return [entry_ctor(item, lang) for item in fn(arg)]

    result = []
    for name in chain:
        try:
            b = _registry.get_backend(lang, backend=name)
        except (UnsupportedLanguageError, BackendLoadError):
            continue
        fn = getattr(b, method_name, None)
        if fn is None:
            continue
        key = f"{lang}:{name}"
        result.extend(entry_ctor(item, key) for item in fn(arg))
    return result


def list_lemmas_traced(
    pos: str,
    language: str,
    backend: str | None = None,
) -> list[LemmaEntry]:
    """Return lemmas with per-entry source attribution.

    Queries each backend in the registered chain (or explicit backend=). Returns
    one LemmaEntry per (lemma, backend) pair — duplicates across backends are NOT
    collapsed. Backends without list_lemmas() are silently skipped.
    """
    lang = _registry.resolve_language(language, backend)
    return _chain_walk_traced(lang, backend, "list_lemmas", pos,
                               lambda lm, key: LemmaEntry(lemma=lm, source=key))


def list_lemmas(pos: str, language: str | None = None, backend: str | None = None) -> list[str]:
    """Return lemmas available in the backend's corpus for the given POS.

    When backend=None and a chain is registered for language, queries all chain
    backends and returns a deduplicated union. Returns [] for algorithm-based
    backends that have no finite vocabulary.
    """
    lang = _registry.resolve_language(language, backend)

    if backend is None and _registry.get_chain(lang):
        return list(dict.fromkeys(e.lemma for e in list_lemmas_traced(pos, lang)))

    b = _registry.get_backend(lang, backend=backend)
    fn = getattr(b, "list_lemmas", None)
    if fn is None:
        return []
    return fn(pos)


def analyze_traced(
    form: str,
    language: str,
    backend: str | None = None,
) -> list[AnalysisEntry]:
    """Return candidate reverse-lookup analyses for form with per-entry source attribution.

    Queries each backend in the registered chain (or explicit backend=). Returns
    one AnalysisEntry per (candidate, backend) pair — duplicates across backends
    are NOT collapsed. Backends without analyze() are silently skipped.
    """
    lang = _registry.resolve_language(language, backend)
    return _chain_walk_traced(lang, backend, "analyze", form,
                               lambda r, key: AnalysisEntry(**r, source=key))


def analyze(form: str, language: str | None = None, backend: str | None = None) -> list[dict]:
    """Return candidate reverse-lookup analyses for form as plain dicts, deduplicated.

    When backend=None and a chain is registered for language, queries all chain
    backends and returns a deduplicated union (by lemma+pos+tag). Returns [] for
    backends without analyze().
    """
    lang = _registry.resolve_language(language, backend)

    if backend is None and _registry.get_chain(lang):
        dedup: dict[tuple, dict] = {}
        for e in analyze_traced(form, lang):
            dedup.setdefault((e.lemma, e.pos, e.tag),
                             {"lemma": e.lemma, "pos": e.pos, "tag": e.tag, "features": e.features})
        return list(dedup.values())

    b = _registry.get_backend(lang, backend=backend)
    fn = getattr(b, "analyze", None)
    if fn is None:
        return []
    return fn(form)


def get_slot_templates(
    lang: str, pos: str, terms_lang: str = "en", *, backend: "str | None" = None
) -> "list[SlotTemplate] | None":
    """Return slot templates for (lang, pos, terms_lang) from the registered backend.

    Uses the default backend only; does not walk chains. Returns None if no
    backend is registered for lang, the backend has no get_slot_templates
    attribute, or the backend returns None for this combination.

    Pass backend='name' to select a named variant (e.g. 'ancient-greek' vs
    'unimorph' when both are registered for the same language).
    """
    resolved = _registry.resolve_language(lang, backend)
    try:
        _backend = _registry.get_backend(resolved, backend)
    except (UnsupportedLanguageError, BackendLoadError):
        return None
    fn = getattr(_backend, "get_slot_templates", None)
    if fn is None:
        return None
    return fn(lang, pos, terms_lang)


def inflect_slot(
    lemma: str,
    slot: "SlotTemplate",
    pos: str,
    *,
    language: str,
    backend: "str | object | None" = None,
) -> set[str]:
    """Inflect lemma for a single SlotTemplate using the registered tag_type dispatch.

    Bypasses chains and hooks — slot-based calls use the backend-native tag directly.
    For UD slots needing chain semantics use eee.inflect(lemma, slot.features, pos, language=language).

    Parameters
    ----------
    backend : str | object | None
        Named backend variant (str), explicit backend instance (object), or None to
        use the default registered backend. Pass an instance when the language is not
        registered with eee (e.g. non-bundled UniMorph languages loaded via
        register_language()).

    Raises
    ------
    KeyError                  if slot.tag_type is not registered
    UnsupportedLanguageError  if no backend is found for language (and backend=None)
    """
    from eee_project._tag_registry import _get_tag_dispatch
    dispatch_fn = _get_tag_dispatch(slot.tag_type)
    lang = _registry.resolve_language(language, None)
    if isinstance(backend, str) or backend is None:
        _backend = _registry.get_backend(lang, backend=backend)
    else:
        _backend = backend
    return dispatch_fn(_backend, lemma, slot, pos, lang)


def register_backend(code: str, instance: object, backend: str | None = None) -> None:
    """Register or override a backend instance for a language code.

    Pass backend='name' to register a named variant alongside the default.
    Idempotent: calling twice with the same instance produces the same state.
    Overrides any existing registration, including cached entry-point instances.
    """
    _registry.register_backend(code, instance, backend=backend)


def set_fallback_backend(instance: object) -> None:
    """Register a catch-all backend for unregistered languages.

    Not included in supported_languages().
    """
    _registry.set_fallback_backend(instance)


def language_info(code: str) -> dict | None:
    """Return the manifest entry for the given EEE language code, or None if unknown."""
    return _registry.language_info(code)


def supported_languages() -> dict[str, list[str]]:
    """Return a mapping of language code → list of entry point values for discovered backends.

    Includes all entry-point backends without triggering lazy loads. Multiple backends
    may register for the same language code (e.g. dedicated + unimorph); all are listed.
    Does NOT include explicitly registered backends or the fallback backend.
    """
    return _registry.supported_languages()

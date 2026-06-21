"""Tag type dispatch registry for slot-based inflection."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from eee_project._slot_template import SlotTemplate

_BUILTIN_NAMES = frozenset({"ud", "unimorph"})


def _ud_dispatch(backend: Any, lemma: str, slot: "SlotTemplate", pos: str, lang: str) -> set[str]:
    if slot.features is None:
        raise ValueError(f"UD slot {slot.label!r} requires a features dict; got None")
    return set(backend.inflect(lemma, slot.features, pos, language=lang))


def _unimorph_dispatch(backend: Any, lemma: str, slot: "SlotTemplate", pos: str, lang: str) -> set[str]:
    if not slot.tag:
        raise ValueError(f"UniMorph slot {slot.label!r} requires a non-empty tag")
    return set(backend.inflect(lemma, slot.tag, pos, language=lang))


_TAG_REGISTRY: dict[str, Callable] = {
    "ud": _ud_dispatch,
    "unimorph": _unimorph_dispatch,
}


def register_tag_type(
    name: str,
    dispatch_fn: "Callable[[Any, str, SlotTemplate, str, str], set[str]]",
) -> None:
    """Register a custom tag type for slot template dispatch.

    dispatch_fn signature: (backend, lemma, slot, pos, lang) -> set[str]

    Raises ValueError if name is 'ud' or 'unimorph' (built-ins are protected).
    Custom names can be re-registered (overwrite without error).
    """
    if name in _BUILTIN_NAMES:
        raise ValueError(f"Cannot overwrite built-in tag type {name!r}")
    _TAG_REGISTRY[name] = dispatch_fn


def _get_tag_dispatch(name: str) -> Callable:
    """Return the dispatch function for name, or raise KeyError if not registered."""
    return _TAG_REGISTRY[name]


def _clear_tag_registry() -> None:
    """Remove all custom tag type registrations; restore built-in 'ud' and 'unimorph'."""
    _TAG_REGISTRY.clear()
    _TAG_REGISTRY["ud"] = _ud_dispatch
    _TAG_REGISTRY["unimorph"] = _unimorph_dispatch

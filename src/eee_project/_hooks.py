from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class HookContext:
    """Read-only execution snapshot passed to pre- and post-hooks.

    tried is empty when passed to pre_hook; populated when passed to post_hook.
    Hook exceptions propagate to the caller (unlike backend exceptions).
    Do not mutate features or tried — they are shared across the call chain.
    """

    lemma: str
    features: "dict[str, str] | str"
    pos: str
    language: str
    tried: list[str]
    stop: str


PreHook = Callable[
    [str, "dict[str, str] | str", str, HookContext],
    tuple[str, "dict[str, str] | str", str],
]
PostHook = Callable[[set[str], HookContext], set[str]]

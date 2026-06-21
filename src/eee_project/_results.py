from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InflectResult:
    """Returned by inflect_traced() and BackendChain.run().

    Not hashable (forms is a mutable set). Do not mutate forms, tried, or by_backend.
    """

    forms: set[str]
    source: str | None           # None for stop="all" or all-empty stop="first"
    tried: list[str]             # unavailable backends suffixed " (unavailable)"
    by_backend: dict[str, set[str]] = field(default_factory=dict)
    # Maps each backend key that ran → forms it returned (empty set if it returned nothing).
    # Backends that were unavailable or raised exceptions are excluded.


@dataclass(frozen=True)
class LemmaEntry:
    """One lemma + its source backend, from list_lemmas_traced()."""

    lemma: str
    source: str

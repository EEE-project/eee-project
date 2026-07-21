"""Backend chain executor."""
from __future__ import annotations

import logging

from eee_project._exceptions import BackendLoadError, UnsupportedLanguageError
from eee_project._hooks import HookContext, PostHook, PreHook
from eee_project._registry import get_backend
from eee_project._results import InflectResult

log = logging.getLogger(__name__)


class BackendChain:
    """Ordered chain of backends with optional pre/post hooks."""

    def __init__(
        self,
        language: str,
        backends: list[str],
        stop: str = "first",
        pre_hook: PreHook | None = None,
        post_hook: PostHook | None = None,
    ) -> None:
        if stop not in ("first", "all"):
            raise ValueError(f"stop must be 'first' or 'all', got {stop!r}")
        self.language = language
        self._backends = backends
        self.stop = stop
        self._pre_hook = pre_hook
        self._post_hook = post_hook

    def run(
        self,
        lemma: str,
        features: "dict[str, str] | str",
        pos: str,
    ) -> InflectResult:
        """Execute the chain and return InflectResult."""
        tried: list[str] = []
        forms: set[str] = set()
        source: str | None = None
        by_backend: dict[str, set[str]] = {}

        if self._pre_hook is not None:
            ctx = HookContext(
                lemma=lemma, features=features, pos=pos,
                language=self.language, tried=[], stop=self.stop,
            )
            lemma, features, pos = self._pre_hook(lemma, features, pos, ctx)

        for name in self._backends:
            key = f"{self.language}:{name}"
            try:
                backend = get_backend(self.language, name)
            except (UnsupportedLanguageError, ModuleNotFoundError, BackendLoadError):
                log.info("Chain for %s: skipping %s (not installed)", self.language, name)
                tried.append(f"{key} (unavailable)")
                continue

            try:
                result = backend.inflect(lemma, features, pos, language=self.language)
            except Exception:
                log.debug("Chain for %s: backend %s raised, skipping", self.language, name, exc_info=True)
                tried.append(f"{key} (error)")
                continue

            tried.append(key)
            by_backend[key] = set(result)

            if self.stop == "first":
                if result:
                    forms = set(result)
                    source = key
                    break
            else:
                forms |= result

        if self._post_hook is not None:
            ctx = HookContext(
                lemma=lemma, features=features, pos=pos,
                language=self.language, tried=list(tried), stop=self.stop,
            )
            forms = self._post_hook(forms, ctx)

        return InflectResult(forms=forms, source=source, tried=tried, by_backend=by_backend)

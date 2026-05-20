"""
MorphologyBackend Protocol — language-agnostic morphology contract.

Third-party backends need not import or inherit from this module.
Any class with the correct methods and `language` attribute satisfies
the Protocol structurally (duck typing). See AnalysisNotSupportedError
in eee._exceptions for the expected exception from non-analyzing backends.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from eee._exceptions import AnalysisNotSupportedError  # noqa: F401

__all__ = ["MorphologyBackend"]


@runtime_checkable
class MorphologyBackend(Protocol):
    """
    Structural protocol for EEE morphology backends.

    A backend must expose:
      - language (str): IETF language tag, e.g. "el", "grc", "la"
      - inflect(lemma, features, pos) -> set[str]
      - analyze(form, pos=None) -> list[dict[str, str]]

    Backends that do not implement analysis must raise
    AnalysisNotSupportedError (not return []).
    """

    language: str

    def inflect(
        self,
        lemma: str,
        features: dict[str, str],
        pos: str,
    ) -> set[str]:
        """
        Return the set of surface forms for lemma matching the given feature bundle.

        Args:
            lemma: Dictionary/citation form of the word.
            features: UD FEATS dict, e.g.
                {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Sing"}.
                UniMorph strings are not accepted in v1.
                Unknown keys are silently ignored by backends.
            pos: Part of speech — "verb", "noun", "adjective", "adverb".
                Required; UD features do not encode POS.

        Returns:
            Set of alternative surface forms. Empty set if no forms match.
        """
        ...

    def analyze(
        self,
        form: str,
        pos: str | None = None,
    ) -> list[dict[str, str]]:
        """
        Return possible morphological analyses for an inflected surface form.

        Args:
            form: Inflected surface form.
            pos: Optional POS filter.

        Returns:
            List of UD FEATS dicts. List because morphological ambiguity is
            common — a single form may match multiple lemmas or analyses.

        Raises:
            AnalysisNotSupportedError: If this backend has no analysis
                implementation. This distinguishes "no analyzer" from
                "analyzer ran, found zero results".
        """
        ...

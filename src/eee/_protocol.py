"""
MorphologyBackend Protocol — language-agnostic morphology contract.

Third-party backends need not import or inherit from this module.
Any class with the correct methods and `language` attribute satisfies
the Protocol structurally (duck typing).
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

__all__ = ["MorphologyBackend"]


@runtime_checkable
class MorphologyBackend(Protocol):
    """
    Structural protocol for EEE morphology backends.

    A backend must expose:
      - language (str): IETF language tag, e.g. "el", "grc", "la"
      - inflect(lemma, features, pos) -> set[str]
    """

    language: str

    def inflect(
        self,
        lemma: str,
        features: dict[str, str],
        pos: str,
        **_kw,
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

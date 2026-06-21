"""SlotTemplate dataclass and SupportsSlotTemplates protocol."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Protocol


@dataclass(frozen=True)
class SlotTemplate:
    """One paradigm slot definition — label, backend-native key, and optional UD features.

    For tag_type="ud": tag is a canonical display key derived from features by joining
    values in sorted-key order (e.g. "Nom;Sing" from {"Case": "Nom", "Number": "Sing"})
    if not provided explicitly.
    For tag_type="unimorph": tag is the full UniMorph string used for direct index lookup.
    """

    label: str
    tag_type: str
    tag: str = ""
    features: Mapping[str, str] | None = None

    def __post_init__(self) -> None:
        # Wrap features in MappingProxyType so the frozen contract is complete:
        # frozen=True blocks attribute reassignment but not dict mutation.
        if self.features is not None:
            object.__setattr__(self, "features", MappingProxyType(dict(self.features)))
        if self.tag == "" and self.tag_type == "ud" and self.features:
            object.__setattr__(
                self,
                "tag",
                ";".join(self.features[k] for k in sorted(self.features.keys())),
            )

    def __hash__(self) -> int:
        feats_key = tuple(sorted(self.features.items())) if self.features is not None else None
        return hash((self.label, self.tag_type, self.tag, feats_key))


class SupportsSlotTemplates(Protocol):
    def get_slot_templates(
        self, lang: str, pos: str, terms_lang: str = "en"
    ) -> "list[SlotTemplate] | None":
        """Return slot definitions for (lang, pos) with labels in terms_lang.

        Returns None if no template is available for this combination.
        """
        ...

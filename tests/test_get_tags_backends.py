"""Cross-backend get_tags() consistency and label-coverage tests.

Each backend produces a list of tag dicts (UD features + a native tag string).
eee-project joins those features against label TSVs to produce human-readable
slot labels. These tests verify that every tag row has a matching label and
that feature vocabularies are consistent across backends.
"""
from __future__ import annotations

import csv
import importlib.resources as _pkg

import pytest

from ancient_greek_backend_eee.backend import AncientGreekBackend
from modern_greek_backend_eee.backend import ModernGreekBackend
from unimorph_backend_eee.backend import UniMorphBackend


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_label_tsv(pos: str, lang: str = "en") -> dict[frozenset, str]:
    """Return {frozenset(feature_items) → label} from eee_project label TSV."""
    text = (
        _pkg.files("eee_project.data.labels") / f"{pos}-{lang}.tsv"
    ).read_text(encoding="utf-8")
    result = {}
    for row in csv.DictReader(text.splitlines(), delimiter="\t"):
        feats = frozenset((k, v) for k, v in row.items() if k != "label" and v)
        result[feats] = row["label"]
    return result


_LABELS: dict[str, dict[frozenset, str]] = {}


def _labels(pos: str) -> dict[frozenset, str]:
    if pos not in _LABELS:
        _LABELS[pos] = _load_label_tsv(pos)
    return _LABELS[pos]


def _tag_feats(row: dict[str, str]) -> frozenset:
    return frozenset((k, v) for k, v in row.items() if k != "tag")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ALL_BACKENDS = [
    pytest.param(AncientGreekBackend(), id="ancient-greek"),
    pytest.param(UniMorphBackend(), id="unimorph"),
    pytest.param(ModernGreekBackend(), id="modern-greek"),
]

_VALID_CASES = {"Nom", "Gen", "Dat", "Acc", "Voc"}
_VALID_NUMBERS = {"Sing", "Plur"}
_VALID_GENDERS = {"Masc", "Fem", "Neut"}
_NOUN_ADJ_KEYS = {"tag", "Case", "Number", "Gender"}


# ---------------------------------------------------------------------------
# Label coverage: every tag row MUST resolve to a label in the TSV
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_noun_tags_all_have_label(backend):
    labels = _labels("noun")
    for row in backend.get_tags("noun"):
        key = _tag_feats(row)
        assert key in labels, (
            f"{type(backend).__name__}: noun tag has no label: {dict(row)}"
        )


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_adj_tags_all_have_label(backend):
    labels = _labels("adj")
    for row in backend.get_tags("adjective"):
        key = _tag_feats(row)
        assert key in labels, (
            f"{type(backend).__name__}: adj tag has no label: {dict(row)}"
        )


# ---------------------------------------------------------------------------
# Feature vocabulary: values must come from the known UD sets
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_noun_feature_vocabulary(backend):
    for row in backend.get_tags("noun"):
        if "Case" in row:
            assert row["Case"] in _VALID_CASES
        if "Number" in row:
            assert row["Number"] in _VALID_NUMBERS
        if "Gender" in row:
            assert row["Gender"] in _VALID_GENDERS


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_adj_feature_vocabulary(backend):
    for row in backend.get_tags("adjective"):
        if "Case" in row:
            assert row["Case"] in _VALID_CASES
        if "Number" in row:
            assert row["Number"] in _VALID_NUMBERS
        if "Gender" in row:
            assert row["Gender"] in _VALID_GENDERS


# ---------------------------------------------------------------------------
# Structural checks: no unexpected feature keys, tag string always present
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_noun_rows_have_no_extra_keys(backend):
    for row in backend.get_tags("noun"):
        assert set(row) <= _NOUN_ADJ_KEYS, (
            f"{type(backend).__name__}: unexpected keys in noun row: {set(row) - _NOUN_ADJ_KEYS}"
        )


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_adj_rows_have_no_extra_keys(backend):
    for row in backend.get_tags("adjective"):
        assert set(row) <= _NOUN_ADJ_KEYS, (
            f"{type(backend).__name__}: unexpected keys in adj row: {set(row) - _NOUN_ADJ_KEYS}"
        )


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_noun_all_rows_have_tag_string(backend):
    for row in backend.get_tags("noun"):
        assert row.get("tag"), f"Missing or empty tag in noun row: {row}"


@pytest.mark.parametrize("backend", ALL_BACKENDS)
def test_adj_all_rows_have_tag_string(backend):
    for row in backend.get_tags("adjective"):
        assert row.get("tag"), f"Missing or empty tag in adj row: {row}"


# ---------------------------------------------------------------------------
# Cross-backend comparison: grc backends share same case/number coverage
# (UniMorph has no gender for nouns; ancient-greek always has gender)
# ---------------------------------------------------------------------------

def test_grc_noun_case_coverage_matches():
    """Ancient-greek and unimorph cover the same 5 cases for nouns."""
    agb_cases = {r["Case"] for r in AncientGreekBackend().get_tags("noun")}
    umb_cases = {r["Case"] for r in UniMorphBackend().get_tags("noun")}
    assert agb_cases == umb_cases == _VALID_CASES


def test_grc_noun_number_coverage_matches():
    """Ancient-greek and unimorph both cover Sing and Plur for nouns."""
    agb_nums = {r["Number"] for r in AncientGreekBackend().get_tags("noun")}
    umb_nums = {r["Number"] for r in UniMorphBackend().get_tags("noun")}
    assert agb_nums == umb_nums == _VALID_NUMBERS


def test_unimorph_noun_has_no_gender():
    """UniMorph grc noun tags don't track gender (corpus lacks it)."""
    for row in UniMorphBackend().get_tags("noun"):
        assert "Gender" not in row


def test_ancient_greek_noun_always_has_gender():
    """Ancient-greek noun tags always include Gender."""
    for row in AncientGreekBackend().get_tags("noun"):
        assert "Gender" in row


def test_modern_greek_noun_no_dative():
    """Modern Greek nouns don't have Dative (case doesn't exist in MG)."""
    cases = {r["Case"] for r in ModernGreekBackend().get_tags("noun") if "Case" in r}
    assert "Dat" not in cases


def test_all_backends_noun_labels_are_nonempty_strings():
    """Label lookup returns a non-empty string for every tag in every backend."""
    noun_labels = _labels("noun")
    for backend in (AncientGreekBackend(), UniMorphBackend(), ModernGreekBackend()):
        for row in backend.get_tags("noun"):
            label = noun_labels[_tag_feats(row)]
            assert isinstance(label, str) and label.strip(), (
                f"{type(backend).__name__}: label is blank for {row}"
            )

"""Tests for SlotTemplate, SupportsSlotTemplates, tag registry, and public API."""
from __future__ import annotations

import dataclasses
import pytest

import eee_project as eee
from eee_project import SlotTemplate, SupportsSlotTemplates
from eee_project._tag_registry import _get_tag_dispatch, register_tag_type


# ---------------------------------------------------------------------------
# Section 01: SlotTemplate construction and immutability
# ---------------------------------------------------------------------------

def test_slot_template_construction():
    slot = SlotTemplate(label="Nominative Sg", tag="N;NOM;SG", tag_type="unimorph")
    assert slot.label == "Nominative Sg"
    assert slot.tag == "N;NOM;SG"
    assert slot.tag_type == "unimorph"
    assert slot.features is None


def test_slot_template_construction_with_features():
    features = {"Case": "Nom", "Number": "Sing"}
    slot = SlotTemplate(
        label="Nominative Singular",
        tag="Nom;Sing",
        tag_type="ud",
        features=features,
    )
    assert slot.label == "Nominative Singular"
    assert slot.tag == "Nom;Sing"
    assert slot.tag_type == "ud"
    assert slot.features == features


def test_slot_template_frozen():
    slot = SlotTemplate(label="Test", tag="N;NOM;SG", tag_type="unimorph")
    with pytest.raises(dataclasses.FrozenInstanceError):
        slot.label = "Changed"
    with pytest.raises(dataclasses.FrozenInstanceError):
        slot.tag = "N;ACC;SG"
    with pytest.raises(dataclasses.FrozenInstanceError):
        slot.tag_type = "ud"
    with pytest.raises(dataclasses.FrozenInstanceError):
        slot.features = {}


def test_slot_template_ud_auto_tag():
    slot = SlotTemplate(
        label="Nominative Singular",
        tag_type="ud",
        features={"Case": "Nom", "Number": "Sing"},
    )
    assert slot.tag == "Nom;Sing"


def test_slot_template_ud_auto_tag_sorted():
    # Keys in reverse alphabetical order — tag is derived from values in sorted-key order
    slot = SlotTemplate(
        label="Test",
        tag_type="ud",
        features={"Number": "Sing", "Case": "Nom"},
    )
    # sorted(keys) = ["Case", "Number"] → values in key order: "Nom;Sing"
    assert slot.tag == "Nom;Sing"


def test_slot_template_ud_explicit_tag_preserved():
    # When tag is explicitly provided for ud, it is kept as-is
    slot = SlotTemplate(
        label="Nominative Singular",
        tag="ud:Nom:Sing",
        tag_type="ud",
        features={"Case": "Nom", "Number": "Sing"},
    )
    assert slot.tag == "ud:Nom:Sing"


def test_slot_template_unimorph_no_features():
    slot = SlotTemplate(label="Hab. Pres. 3sg", tag="V;HAB;PRS;3;SG;DIR", tag_type="unimorph")
    assert slot.features is None
    assert slot.tag == "V;HAB;PRS;3;SG;DIR"


def test_slot_template_hashable():
    slot = SlotTemplate(label="Test", tag="N;NOM;SG", tag_type="unimorph")
    assert hash(slot) is not None
    s = {slot}
    assert slot in s


def test_slot_template_hashable_with_features():
    slot = SlotTemplate(
        label="Nominative Singular",
        tag_type="ud",
        features={"Case": "Nom", "Number": "Sing"},
    )
    # Slots with dict features must still be hashable (frozen=True with dict field)
    h = hash(slot)
    assert isinstance(h, int)
    s = {slot}
    assert slot in s


# ---------------------------------------------------------------------------
# Section 02: Tag type registry
# ---------------------------------------------------------------------------

def test_register_custom_tag_type_and_retrieve():
    fn = lambda backend, lemma, slot, pos, lang: set()
    register_tag_type("custom", fn)
    assert _get_tag_dispatch("custom") is fn


def test_register_ud_raises():
    with pytest.raises(ValueError, match="ud"):
        register_tag_type("ud", lambda *a: set())


def test_register_unimorph_raises():
    with pytest.raises(ValueError, match="unimorph"):
        register_tag_type("unimorph", lambda *a: set())


def test_register_custom_overwrites_without_error():
    fn1 = lambda backend, lemma, slot, pos, lang: set()
    fn2 = lambda backend, lemma, slot, pos, lang: {"form"}
    register_tag_type("custom", fn1)
    register_tag_type("custom", fn2)  # must not raise
    assert _get_tag_dispatch("custom") is fn2


def test_get_tag_dispatch_unknown_raises():
    with pytest.raises(KeyError):
        _get_tag_dispatch("not_registered")


def test_builtin_ud_dispatch_exists():
    fn = _get_tag_dispatch("ud")
    assert callable(fn)


def test_builtin_unimorph_dispatch_exists():
    fn = _get_tag_dispatch("unimorph")
    assert callable(fn)


def test_supports_slot_templates_protocol():
    # EEE uses getattr, not isinstance — test the actual dispatch pattern
    class FakeBackend:
        def get_slot_templates(self, lang, pos, terms_lang="en"):
            return None

    class NoSlots:
        pass

    assert getattr(FakeBackend(), "get_slot_templates", None) is not None
    assert getattr(NoSlots(), "get_slot_templates", None) is None


# ---------------------------------------------------------------------------
# Section 03: Public API — get_slot_templates, inflect_slot, inflect(str)
# ---------------------------------------------------------------------------

def test_get_slot_templates_no_backend():
    result = eee.get_slot_templates("xx_no_backend", "noun")
    assert result is None


def test_get_slot_templates_backend_missing_attr():
    class MinimalBackend:
        def inflect(self, lemma, features, pos, **kw):
            return set()

    eee.register_backend("el", MinimalBackend())
    result = eee.get_slot_templates("el", "noun")
    assert result is None


def test_get_slot_templates_backend_returns_list():
    expected = [
        SlotTemplate(label="Nom Sg", tag_type="ud", features={"Case": "Nom", "Number": "Sing"})
    ]

    class FakeBackend:
        def inflect(self, lemma, features, pos, **kw):
            return set()

        def get_slot_templates(self, lang, pos, terms_lang="en"):
            return expected

    eee.register_backend("el", FakeBackend())
    result = eee.get_slot_templates("el", "noun")
    assert result == expected


def test_inflect_slot_ud_uses_features():
    received = {}

    class FakeBackend:
        def inflect(self, lemma, features, pos, **kw):
            received["features"] = features
            return set()

    eee.register_backend("el", FakeBackend())
    slot = SlotTemplate(
        label="Nom Sg", tag_type="ud", features={"Case": "Nom", "Number": "Sing"}
    )
    eee.inflect_slot("γυναίκα", slot, "noun", language="el")
    from collections.abc import Mapping
    assert isinstance(received["features"], Mapping)
    assert received["features"] == {"Case": "Nom", "Number": "Sing"}


def test_inflect_slot_unimorph_uses_tag():
    received = {}

    class FakeBackend:
        def inflect(self, lemma, features, pos, **kw):
            received["features"] = features
            return {"γυναίκες"}

    eee.register_backend("el", FakeBackend())
    slot = SlotTemplate(label="Nom Pl", tag="N;NOM;PL", tag_type="unimorph")
    eee.inflect_slot("γυναίκα", slot, "noun", language="el")
    assert received["features"] == "N;NOM;PL"


def test_inflect_slot_unregistered_tag_type_raises():
    class FakeBackend:
        def inflect(self, lemma, features, pos, **kw):
            return set()

    eee.register_backend("el", FakeBackend())
    slot = SlotTemplate(label="X", tag="X;Y;Z", tag_type="exotic_unknown")
    with pytest.raises(KeyError):
        eee.inflect_slot("λέξη", slot, "noun", language="el")


def test_inflect_str_features_passes_str_to_backend():
    received = {}

    class FakeBackend:
        def inflect(self, lemma, features, pos, **kw):
            received["features"] = features
            return {"form1"}

    eee.register_backend("el", FakeBackend())
    eee.inflect("λέξη", "N;NOM;SG", "noun", language="el")
    assert received["features"] == "N;NOM;SG"
    assert isinstance(received["features"], str)

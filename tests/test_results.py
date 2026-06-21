"""Tests for InflectResult, LemmaEntry, and HookContext dataclasses."""
import pytest
from dataclasses import FrozenInstanceError

from eee_project import InflectResult, LemmaEntry, HookContext


# ── InflectResult ────────────────────────────────────────────────────────────

def test_inflect_result_frozen():
    r = InflectResult(forms={"foo"}, source="ancient-greek", tried=["grc:ancient-greek"])
    with pytest.raises(FrozenInstanceError):
        r.forms = {"bar"}


def test_inflect_result_forms_set():
    r = InflectResult(forms={"α", "β"}, source=None, tried=[])
    assert r.forms == {"α", "β"}
    assert isinstance(r.forms, set)


def test_inflect_result_source_none():
    r = InflectResult(forms=set(), source=None, tried=[])
    assert r.source is None


def test_inflect_result_tried_list():
    r = InflectResult(forms=set(), source=None, tried=["grc:ancient-greek", "grc:unimorph"])
    assert isinstance(r.tried, list)
    assert r.tried == ["grc:ancient-greek", "grc:unimorph"]


def test_inflect_result_equality():
    r1 = InflectResult(forms={"θεός"}, source="ancient-greek", tried=["grc:ancient-greek"])
    r2 = InflectResult(forms={"θεός"}, source="ancient-greek", tried=["grc:ancient-greek"])
    assert r1 == r2


# ── LemmaEntry ───────────────────────────────────────────────────────────────

def test_lemma_entry_frozen():
    e = LemmaEntry(lemma="θεός", source="ancient-greek")
    with pytest.raises(FrozenInstanceError):
        e.lemma = "λόγος"


def test_lemma_entry_fields():
    e = LemmaEntry(lemma="θεός", source="ancient-greek")
    assert isinstance(e.lemma, str)
    assert isinstance(e.source, str)
    assert e.lemma == "θεός"
    assert e.source == "ancient-greek"


# ── HookContext ───────────────────────────────────────────────────────────────

def test_hook_context_frozen():
    ctx = HookContext(lemma="θεός", features={}, pos="noun",
                      language="grc", tried=[], stop="first")
    with pytest.raises(FrozenInstanceError):
        ctx.stop = "all"


def test_hook_context_all_fields():
    ctx = HookContext(lemma="θεός", features={"Case": "Nom"}, pos="noun",
                      language="grc", tried=["grc:ancient-greek"], stop="first")
    assert ctx.lemma == "θεός"
    assert ctx.features == {"Case": "Nom"}
    assert ctx.pos == "noun"
    assert ctx.language == "grc"
    assert ctx.tried == ["grc:ancient-greek"]
    assert ctx.stop == "first"


def test_hook_context_tried_empty_for_pre_hook():
    ctx = HookContext(lemma="θεός", features={}, pos="noun",
                      language="grc", tried=[], stop="first")
    assert ctx.tried == []


def test_hook_context_tried_populated_for_post_hook():
    ctx = HookContext(lemma="θεός", features={}, pos="noun",
                      language="grc", tried=["grc:ancient-greek", "grc:unimorph"],
                      stop="first")
    assert len(ctx.tried) == 2
    assert "grc:ancient-greek" in ctx.tried

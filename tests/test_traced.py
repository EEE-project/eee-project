"""Tests for inflect_traced() and list_lemmas_traced()."""
import pytest

import eee_project as eee
import eee_project._registry as _reg
from eee_project._results import InflectResult, LemmaEntry
from conftest import MockBackend, register, corpus_backend


# ── inflect_traced() ──────────────────────────────────────────────────────────

def test_inflect_traced_returns_inflect_result():
    register("grc", "mock-a", MockBackend({"θεός"}))
    _reg.set_chain("grc", ["mock-a"])
    result = eee.inflect_traced("θεός", {}, "noun", language="grc")
    assert isinstance(result, InflectResult)


def test_inflect_traced_explicit_backend_attribution():
    register("grc", "mock", MockBackend({"θεός"}))
    result = eee.inflect_traced("θεός", {}, "noun", language="grc", backend="mock")
    assert isinstance(result, InflectResult)
    assert result.source == "grc:mock"
    assert result.tried == ["grc:mock"]


def test_inflect_traced_chain_source_is_producing_backend():
    register("grc", "first", MockBackend(set()))
    register("grc", "second", MockBackend({"form"}))
    _reg.set_chain("grc", ["first", "second"])
    result = eee.inflect_traced("θεός", {}, "noun", language="grc")
    assert result.source == "grc:second"
    assert result.forms == {"form"}


def test_inflect_traced_stop_all_source_is_none():
    register("grc", "a", MockBackend({"α"}))
    register("grc", "b", MockBackend({"β"}))
    _reg.set_chain("grc", ["a", "b"])
    result = eee.inflect_traced("θεός", {}, "noun", language="grc", stop="all")
    assert result.source is None
    assert result.forms == {"α", "β"}


def test_inflect_traced_per_call_post_hook_overrides_chain_hook():
    register("grc", "mock-a", MockBackend({"θεός"}))
    chain_called = []

    def chain_hook(forms, ctx):
        chain_called.append(True)
        return forms | {"chain_form"}

    _reg.set_chain("grc", ["mock-a"], post_hook=chain_hook)
    result = eee.inflect_traced("θεός", {}, "noun", language="grc",
                                post_hook=lambda forms, ctx: forms | {"call_form"})
    assert "call_form" in result.forms
    assert "chain_form" not in result.forms
    assert not chain_called


def test_inflect_traced_no_chain_applies_post_hook():
    _reg.register_backend("grc", MockBackend({"θεός"}))
    _reg._chains.pop("grc", None)   # remove YAML default chain for this test
    result = eee.inflect_traced("θεός", {}, "noun", language="grc",
                                post_hook=lambda forms, ctx: forms | {"call_form"})
    assert result.forms == {"θεός", "call_form"}


def test_inflect_traced_no_chain_applies_pre_hook():
    _reg.register_backend("grc", MockBackend({"θεός"}))
    _reg._chains.pop("grc", None)   # remove YAML default chain for this test
    seen = []

    def pre_hook(lemma, features, pos, ctx):
        seen.append(lemma)
        return lemma, features, pos

    eee.inflect_traced("λόγος", {}, "noun", language="grc", pre_hook=pre_hook)
    assert seen == ["λόγος"]


def test_inflect_traced_stop_all_by_backend():
    register("grc", "a", MockBackend({"α"}))
    register("grc", "b", MockBackend({"β"}))
    _reg.set_chain("grc", ["a", "b"])
    result = eee.inflect_traced("θεός", {}, "noun", language="grc", stop="all")
    assert result.by_backend == {"grc:a": {"α"}, "grc:b": {"β"}}


def test_inflect_traced_backend_and_chain_raises():
    with pytest.raises(ValueError):
        eee.inflect_traced("λόγος", {}, "noun", language="grc",
                           backend="unimorph", chain=["unimorph"])


# ── list_lemmas_traced() ──────────────────────────────────────────────────────

def test_list_lemmas_traced_returns_lemma_entries():
    b = corpus_backend(set(), ["α", "β"])
    register("grc", "mock-corp", b)
    _reg.set_chain("grc", ["mock-corp"])
    result = eee.list_lemmas_traced("noun", language="grc")
    assert all(isinstance(e, LemmaEntry) for e in result)
    assert len(result) == 2


def test_list_lemmas_traced_includes_all_chain_backends():
    b1 = corpus_backend(set(), ["α"])
    b2 = corpus_backend(set(), ["β"])
    register("grc", "corp-a", b1)
    register("grc", "corp-b", b2)
    _reg.set_chain("grc", ["corp-a", "corp-b"])
    result = eee.list_lemmas_traced("noun", language="grc")
    assert {e.lemma for e in result} == {"α", "β"}


def test_list_lemmas_traced_source_attribution():
    b1 = corpus_backend(set(), ["α"])
    b2 = corpus_backend(set(), ["β"])
    register("grc", "first", b1)
    register("grc", "second", b2)
    _reg.set_chain("grc", ["first", "second"])
    result = eee.list_lemmas_traced("noun", language="grc")
    assert LemmaEntry(lemma="α", source="grc:first") in result
    assert LemmaEntry(lemma="β", source="grc:second") in result


def test_list_lemmas_traced_duplicate_lemma_appears_twice():
    b1 = corpus_backend(set(), ["α"])
    b2 = corpus_backend(set(), ["α"])
    register("grc", "first", b1)
    register("grc", "second", b2)
    _reg.set_chain("grc", ["first", "second"])
    result = eee.list_lemmas_traced("noun", language="grc")
    alpha_entries = [e for e in result if e.lemma == "α"]
    assert len(alpha_entries) == 2
    assert {e.source for e in alpha_entries} == {"grc:first", "grc:second"}


def test_list_lemmas_traced_backend_without_list_lemmas_skipped():
    register("grc", "no-corpus", MockBackend(set()))
    _reg.set_chain("grc", ["no-corpus"])
    result = eee.list_lemmas_traced("noun", language="grc")
    assert result == []


# ── list_lemmas() chain-awareness ─────────────────────────────────────────────

def test_list_lemmas_chain_aware_deduplicates():
    b1 = corpus_backend(set(), ["α", "β"])
    b2 = corpus_backend(set(), ["β", "γ"])
    register("grc", "first", b1)
    register("grc", "second", b2)
    _reg.set_chain("grc", ["first", "second"])
    result = eee.list_lemmas("noun", language="grc")
    assert set(result) == {"α", "β", "γ"}


def test_list_lemmas_explicit_backend_bypasses_chain():
    b1 = corpus_backend(set(), ["α", "β"])
    b2 = corpus_backend(set(), ["γ"])
    register("grc", "first", b1)
    register("grc", "second", b2)
    _reg.set_chain("grc", ["second"])
    result = eee.list_lemmas("noun", language="grc", backend="first")
    assert set(result) == {"α", "β"}

"""Tests for inflect() chain integration. All tests use mock backends."""
import pytest

import eee_project as eee
import eee_project._registry as _reg
from conftest import MockBackend, register


# ── Core dispatch ─────────────────────────────────────────────────────────────

def test_inflect_no_chain_uses_single_backend():
    _reg.register_backend("grc", MockBackend({"θεός"}))
    _reg._chains.pop("grc", None)   # remove YAML default chain for this test
    result = eee.inflect("θεός", {}, "noun", language="grc")
    assert result == {"θεός"}
    assert isinstance(result, set)


def test_inflect_runs_chain_when_registered():
    register("grc", "mock-a", MockBackend({"θεός"}))
    _reg.set_chain("grc", ["mock-a"])
    result = eee.inflect("θεός", {}, "noun", language="grc")
    assert result == {"θεός"}
    assert isinstance(result, set)


def test_inflect_explicit_backend_bypasses_chain():
    register("grc", "mock-chain", MockBackend({"chain-form"}))
    register("grc", "mock-direct", MockBackend({"direct-form"}))
    _reg.set_chain("grc", ["mock-chain"])
    result = eee.inflect("θεός", {}, "noun", language="grc", backend="mock-direct")
    assert result == {"direct-form"}


def test_inflect_per_call_chain_overrides_registry():
    register("grc", "mock-reg", MockBackend({"registry-form"}))
    register("grc", "mock-call", MockBackend({"call-form"}))
    _reg.set_chain("grc", ["mock-reg"])
    result = eee.inflect("θεός", {}, "noun", language="grc", chain=["mock-call"])
    assert result == {"call-form"}


# ── Validation ────────────────────────────────────────────────────────────────

def test_inflect_backend_and_chain_raises():
    with pytest.raises(ValueError):
        eee.inflect("λόγος", {}, "noun", language="grc",
                    backend="unimorph", chain=["unimorph"])


def test_inflect_empty_chain_raises():
    with pytest.raises(ValueError):
        eee.inflect("λόγος", {}, "noun", language="grc", chain=[])


# ── Per-call hooks ────────────────────────────────────────────────────────────

def test_inflect_per_call_chain_with_post_hook():
    register("grc", "mock-a", MockBackend({"θεός"}))

    def sentinel_hook(forms, ctx):
        return forms | {"SENTINEL"}

    result = eee.inflect("θεός", {}, "noun", language="grc",
                         chain=["mock-a"], post_hook=sentinel_hook)
    assert "SENTINEL" in result


def test_inflect_registry_chain_hook_fires():
    register("grc", "mock-a", MockBackend({"θεός"}))

    called = []
    def post_hook(forms, ctx):
        called.append(True)
        return forms

    _reg.set_chain("grc", ["mock-a"], post_hook=post_hook)
    eee.inflect("θεός", {}, "noun", language="grc")
    assert called


def test_inflect_per_call_post_hook_overrides_registry_hook():
    register("grc", "mock-a", MockBackend({"θεός"}))

    registry_hook_called = []
    def registry_hook(forms, ctx):
        registry_hook_called.append(True)
        return forms

    per_call_called = []
    def per_call_hook(forms, ctx):
        per_call_called.append(True)
        return forms | {"PER-CALL"}

    _reg.set_chain("grc", ["mock-a"], post_hook=registry_hook)
    result = eee.inflect("θεός", {}, "noun", language="grc", post_hook=per_call_hook)

    assert "PER-CALL" in result
    assert not registry_hook_called  # overridden, not called
    assert per_call_called


def test_inflect_per_call_chain_does_not_fire_registry_hook():
    # Spec: when chain= is passed per-call, registry chain hooks do NOT apply.
    register("grc", "mock-a", MockBackend({"θεός"}))
    register("grc", "mock-b", MockBackend({"λόγος"}))

    registry_hook_called = []
    def registry_hook(forms, ctx):
        registry_hook_called.append(True)
        return forms

    _reg.set_chain("grc", ["mock-a"], post_hook=registry_hook)
    # Use per-call chain pointing to mock-b, no explicit hooks
    eee.inflect("θεός", {}, "noun", language="grc", chain=["mock-b"])

    assert not registry_hook_called


def test_inflect_chain_without_language_raises():
    # chain= with no language= cannot infer language from chain short-names.
    register("grc", "mock-a", MockBackend({"θεός"}))
    with pytest.raises((ValueError, Exception)):
        eee.inflect("θεός", {}, "noun", chain=["mock-a"])

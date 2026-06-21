"""Tests for registry chain storage, loading, and validation."""
import pytest
import eee_project._registry as _reg
from eee_project._registry import set_chain, get_chain


def test_set_chain_stores_chain():
    set_chain("grc", ["unimorph"])
    assert _reg._chains["grc"]["backends"] == ["unimorph"]


def test_get_chain_returns_stored_list():
    set_chain("grc", ["unimorph"])
    assert get_chain("grc") == ["unimorph"]


def test_get_chain_unknown_language_returns_empty():
    assert get_chain("la") == []


def test_set_chain_overwrites_existing():
    set_chain("el", ["modern-greek"])
    set_chain("el", ["unimorph"])
    assert get_chain("el") == ["unimorph"]


def test_set_chain_empty_list_raises():
    with pytest.raises(ValueError):
        set_chain("grc", [])


def test_chains_default_not_mutated_by_set_chain():
    default_grc_before = _reg._chains_default.get("grc")
    set_chain("grc", ["unimorph"])
    assert _reg._chains_default.get("grc") == default_grc_before


def test_no_yaml_default_chains():
    # No default chains — all chains must be set explicitly.
    assert _reg._chains_default == {}


def test_language_without_chain_returns_empty():
    assert get_chain("la") == []


def test_set_chain_stores_hooks():
    pre = lambda lemma, features, pos, ctx: (lemma, features, pos)
    post = lambda forms, ctx: forms
    set_chain("el", ["modern-greek"], pre_hook=pre, post_hook=post)
    entry = _reg._chains["el"]
    assert entry["pre_hook"] is pre
    assert entry["post_hook"] is post


def test_get_chain_returns_backends_only():
    pre = lambda lemma, features, pos, ctx: (lemma, features, pos)
    set_chain("el", ["modern-greek"], pre_hook=pre)
    result = get_chain("el")
    assert result == ["modern-greek"]
    assert not callable(result)

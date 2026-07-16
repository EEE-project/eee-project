"""Tests for BackendChain executor."""
import pytest
from unittest.mock import MagicMock

from eee_project._chain import BackendChain
from conftest import mock_backend, register


# ── Basic chain execution ─────────────────────────────────────────────────────

def test_stop_first_returns_first_non_empty():
    register("grc", "a", mock_backend(set()))
    register("grc", "b", mock_backend({"θεός"}))
    register("grc", "c", mock_backend({"λόγος"}))
    r = BackendChain("grc", ["a", "b", "c"]).run("θεός", {}, "noun")
    assert r.forms == {"θεός"}
    assert r.source == "grc:b"


def test_stop_first_skips_empty_continues():
    register("grc", "a", mock_backend(set()))
    register("grc", "b", mock_backend({"θεός"}))
    r = BackendChain("grc", ["a", "b"]).run("θεός", {}, "noun")
    assert r.forms == {"θεός"}
    assert r.source == "grc:b"


def test_stop_first_all_empty_returns_empty_result():
    register("grc", "a", mock_backend(set()))
    register("grc", "b", mock_backend(set()))
    r = BackendChain("grc", ["a", "b"]).run("θεός", {}, "noun")
    assert r.forms == set()
    assert r.source is None


def test_stop_all_unions_forms():
    register("grc", "a", mock_backend({"α", "β"}))
    register("grc", "b", mock_backend({"β", "γ"}))
    r = BackendChain("grc", ["a", "b"], stop="all").run("x", {}, "noun")
    assert r.forms == {"α", "β", "γ"}


def test_stop_all_source_is_none():
    register("grc", "a", mock_backend({"α"}))
    r = BackendChain("grc", ["a"], stop="all").run("x", {}, "noun")
    assert r.source is None


def test_stop_all_tried_lists_all_backends():
    register("grc", "a", mock_backend(set()))
    register("grc", "b", mock_backend({"α"}))
    r = BackendChain("grc", ["a", "b"], stop="all").run("x", {}, "noun")
    assert r.tried == ["grc:a", "grc:b"]


def test_stop_first_source_is_producing_backend():
    register("grc", "a", mock_backend(set()))
    register("grc", "b", mock_backend({"θεός"}))
    r = BackendChain("grc", ["a", "b"]).run("θεός", {}, "noun")
    assert r.source == "grc:b"


def test_stop_first_tried_only_includes_backends_up_to_result():
    register("grc", "a", mock_backend(set()))
    b_mock = mock_backend({"θεός"})
    register("grc", "b", b_mock)
    c_mock = mock_backend({"λόγος"})
    register("grc", "c", c_mock)
    r = BackendChain("grc", ["a", "b", "c"]).run("θεός", {}, "noun")
    assert r.tried == ["grc:a", "grc:b"]
    assert "grc:c" not in r.tried
    c_mock.inflect.assert_not_called()


# ── Exception handling ────────────────────────────────────────────────────────

def test_backend_exception_is_skipped():
    a = MagicMock()
    a.inflect.side_effect = RuntimeError("oops")
    b = mock_backend({"θεός"})
    register("grc", "a", a)
    register("grc", "b", b)
    r = BackendChain("grc", ["a", "b"]).run("θεός", {}, "noun")
    assert r.forms == {"θεός"}
    assert r.source == "grc:b"


def test_exception_backend_key_in_tried_with_error_marker():
    a = MagicMock()
    a.inflect.side_effect = RuntimeError("oops")
    register("grc", "a", a)
    register("grc", "b", mock_backend({"θεός"}))
    r = BackendChain("grc", ["a", "b"]).run("θεός", {}, "noun")
    assert "grc:a (error)" in r.tried
    assert "grc:a" not in r.tried
    assert "grc:a (unavailable)" not in r.tried


def test_unavailable_backend_in_tried_with_suffix():
    # "missing" is not registered; get_backend will raise UnsupportedLanguageError
    register("grc", "b", mock_backend({"θεός"}))
    r = BackendChain("grc", ["missing", "b"]).run("θεός", {}, "noun")
    assert "grc:missing (unavailable)" in r.tried


def test_module_not_found_treated_as_unavailable(monkeypatch):
    from unittest.mock import patch
    from eee_project import _chain as chain_mod
    register("grc", "b", mock_backend({"θεός"}))
    with patch.object(chain_mod, "get_backend", side_effect=[ModuleNotFoundError("no pkg"), mock_backend({"θεός"})]):
        r = BackendChain("grc", ["a", "b"]).run("θεός", {}, "noun")
    assert "grc:a (unavailable)" in r.tried


def test_all_backends_raising_returns_empty():
    a = MagicMock()
    a.inflect.side_effect = RuntimeError
    b = MagicMock()
    b.inflect.side_effect = RuntimeError
    register("grc", "a", a)
    register("grc", "b", b)
    r = BackendChain("grc", ["a", "b"]).run("θεός", {}, "noun")
    assert r.forms == set()
    assert r.source is None


# ── Hook dispatch ─────────────────────────────────────────────────────────────

def test_pre_hook_receives_empty_tried():
    seen_ctx = []
    def pre_hook(lemma, features, pos, ctx):
        seen_ctx.append(ctx)
        return lemma, features, pos

    register("grc", "a", mock_backend({"θεός"}))
    BackendChain("grc", ["a"], pre_hook=pre_hook).run("θεός", {}, "noun")
    assert seen_ctx[0].tried == []


def test_pre_hook_return_used_for_backends():
    calls = []
    backend = MagicMock()
    backend.inflect.side_effect = lambda l, f, p, **kw: calls.append((l, f, p)) or set()

    register("grc", "a", backend)

    def pre_hook(lemma, features, pos, ctx):
        return "MODIFIED", {"Tense": "Past"}, "verb"

    BackendChain("grc", ["a"], pre_hook=pre_hook).run("original", {}, "noun")
    assert calls[0] == ("MODIFIED", {"Tense": "Past"}, "verb")


def test_post_hook_receives_populated_tried():
    seen_ctx = []
    def post_hook(forms, ctx):
        seen_ctx.append(ctx)
        return forms

    register("grc", "a", mock_backend({"θεός"}))
    BackendChain("grc", ["a"], post_hook=post_hook).run("θεός", {}, "noun")
    assert "grc:a" in seen_ctx[0].tried


def test_post_hook_return_is_final_forms():
    def post_hook(forms, ctx):
        return forms | {"SENTINEL"}

    register("grc", "a", mock_backend({"θεός"}))
    r = BackendChain("grc", ["a"], post_hook=post_hook).run("θεός", {}, "noun")
    assert "SENTINEL" in r.forms


def test_pre_hook_exception_propagates():
    def bad_hook(lemma, features, pos, ctx):
        raise ValueError("bad pre")

    register("grc", "a", mock_backend(set()))
    with pytest.raises(ValueError, match="bad pre"):
        BackendChain("grc", ["a"], pre_hook=bad_hook).run("θεός", {}, "noun")


def test_post_hook_exception_propagates():
    def bad_hook(forms, ctx):
        raise ValueError("bad post")

    register("grc", "a", mock_backend({"θεός"}))
    with pytest.raises(ValueError, match="bad post"):
        BackendChain("grc", ["a"], post_hook=bad_hook).run("θεός", {}, "noun")


def test_no_hooks_runs_correctly():
    register("grc", "a", mock_backend({"θεός"}))
    r = BackendChain("grc", ["a"]).run("θεός", {}, "noun")
    assert r.forms == {"θεός"}


def test_only_post_hook_set():
    called = []
    def post_hook(forms, ctx):
        called.append(True)
        return forms

    register("grc", "a", mock_backend({"θεός"}))
    BackendChain("grc", ["a"], pre_hook=None, post_hook=post_hook).run("θεός", {}, "noun")
    assert called


# ── Backend key resolution ────────────────────────────────────────────────────

def test_resolution_ancient_greek_grc():
    b = mock_backend({"θεός"})
    register("grc", "ancient-greek", b)
    BackendChain("grc", ["ancient-greek"]).run("θεός", {}, "noun")
    b.inflect.assert_called_once()


def test_resolution_unimorph_grc():
    b = mock_backend({"βοηθός"})
    register("grc", "unimorph", b)
    BackendChain("grc", ["unimorph"]).run("βοηθός", {}, "noun")
    b.inflect.assert_called_once()


def test_resolution_unimorph_el():
    b = mock_backend({"θεός"})
    register("el", "unimorph", b)
    BackendChain("el", ["unimorph"]).run("θεός", {}, "noun")
    b.inflect.assert_called_once()


# ── Single-element chain ──────────────────────────────────────────────────────

def test_single_backend_stop_first_source_and_tried():
    register("grc", "a", mock_backend({"θεός"}))
    r = BackendChain("grc", ["a"]).run("θεός", {}, "noun")
    assert r.source == "grc:a"
    assert r.tried == ["grc:a"]


def test_single_backend_stop_all_source_none():
    register("grc", "a", mock_backend({"θεός"}))
    r = BackendChain("grc", ["a"], stop="all").run("θεός", {}, "noun")
    assert r.source is None
    assert r.tried == ["grc:a"]


# ── by_backend attribution ───────────────────────────────────────────────────

def test_by_backend_stop_first_only_tried_backends():
    register("grc", "a", mock_backend(set()))
    register("grc", "b", mock_backend({"θεός"}))
    register("grc", "c", mock_backend({"λόγος"}))
    r = BackendChain("grc", ["a", "b", "c"]).run("θεός", {}, "noun")
    assert "grc:a" in r.by_backend
    assert "grc:b" in r.by_backend
    assert "grc:c" not in r.by_backend   # never called


def test_by_backend_stop_first_empty_and_nonempty():
    register("grc", "a", mock_backend(set()))
    register("grc", "b", mock_backend({"θεός"}))
    r = BackendChain("grc", ["a", "b"]).run("θεός", {}, "noun")
    assert r.by_backend["grc:a"] == set()
    assert r.by_backend["grc:b"] == {"θεός"}


def test_by_backend_stop_all_all_backends():
    register("grc", "a", mock_backend({"α"}))
    register("grc", "b", mock_backend({"β"}))
    r = BackendChain("grc", ["a", "b"], stop="all").run("x", {}, "noun")
    assert r.by_backend == {"grc:a": {"α"}, "grc:b": {"β"}}


def test_by_backend_unavailable_excluded():
    register("grc", "b", mock_backend({"θεός"}))
    r = BackendChain("grc", ["missing", "b"]).run("θεός", {}, "noun")
    assert "grc:missing" not in r.by_backend
    assert "grc:b" in r.by_backend


def test_by_backend_errored_backend_excluded():
    a = MagicMock()
    a.inflect.side_effect = RuntimeError("oops")
    register("grc", "a", a)
    register("grc", "b", mock_backend({"θεός"}))
    r = BackendChain("grc", ["a", "b"]).run("θεός", {}, "noun")
    assert "grc:a" not in r.by_backend
    assert r.by_backend["grc:b"] == {"θεός"}


# ── Constructor validation ────────────────────────────────────────────────────

def test_invalid_stop_raises():
    with pytest.raises(ValueError):
        BackendChain("grc", ["a"], stop="invalid")


def test_valid_stop_modes():
    BackendChain("grc", ["a"], stop="first")
    BackendChain("grc", ["a"], stop="all")

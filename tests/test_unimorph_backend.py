"""UniMorphBackend unit tests — _lookup is patched, no external deps required."""
from unittest.mock import patch
import logging

import pytest

import eee._registry as _reg


@pytest.fixture(autouse=True)
def reset_registry():
    registered_before = dict(_reg._registered)
    cache_before = dict(_reg._cache)
    fallback_before = _reg._fallback
    yield
    _reg._registered.clear()
    _reg._registered.update(registered_before)
    _reg._cache.clear()
    _reg._cache.update(cache_before)
    _reg._fallback = fallback_before


@pytest.fixture()
def backend():
    from eee.backends.unimorph import UniMorphBackend
    return UniMorphBackend()


VERB_FEATURES = {"Tense": "Pres", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"}
NOUN_FEATURES = {"Case": "Gen", "Number": "Sing"}


def test_grc_verb_raises_pos_not_supported(backend):
    from eee._exceptions import PosNotSupportedError
    with pytest.raises(PosNotSupportedError):
        backend.inflect("λύω", VERB_FEATURES, "verb", language="grc")


def test_grc_verb_emits_warning(backend, caplog):
    from eee._exceptions import PosNotSupportedError
    with caplog.at_level(logging.WARNING):
        with pytest.raises(PosNotSupportedError):
            backend.inflect("λύω", VERB_FEATURES, "verb", language="grc")
    assert any("grc" in r.message and "verb" in r.message for r in caplog.records)


def test_ell_unsupported_pos_raises(backend):
    from eee._exceptions import PosNotSupportedError
    with pytest.raises(PosNotSupportedError):
        backend.inflect("ο", {}, "article", language="ell")


def test_unknown_language_raises(backend):
    from eee._exceptions import UnsupportedLanguageError
    with pytest.raises(UnsupportedLanguageError):
        backend.inflect("foo", {}, "noun", language="xx")


def test_ell_noun_returns_set(backend):
    with patch("eee.backends.unimorph._lookup", return_value={"λόγου"}):
        result = backend.inflect("λόγος", NOUN_FEATURES, "noun", language="ell")
    assert result == {"λόγου"}


def test_empty_result_returns_empty_set(backend):
    with patch("eee.backends.unimorph._lookup", return_value=set()):
        result = backend.inflect("λόγος", {"Case": "Nom", "Number": "Sing"}, "noun", language="ell")
    assert result == set()


def test_unk_sentinel_filtered(backend):
    with patch("eee.backends.unimorph._lookup", return_value={"UNK"}):
        result = backend.inflect("λόγος", {"Case": "Nom", "Number": "Sing"}, "noun", language="ell")
    assert result == set()


def test_empty_string_filtered(backend):
    with patch("eee.backends.unimorph._lookup", return_value={""}):
        result = backend.inflect("λόγος", {"Case": "Nom", "Number": "Sing"}, "noun", language="ell")
    assert result == set()


def test_supported_languages_contains_ell(backend):
    assert "ell" in backend.supported_languages()


def test_supported_languages_excludes_el(backend):
    assert "el" not in backend.supported_languages()


def test_emdash_sentinel_filtered(backend):
    with patch("eee.backends.unimorph._lookup", return_value={"—"}):
        result = backend.inflect("λόγος", {"Case": "Nom", "Number": "Sing"}, "noun", language="ell")
    assert result == set()


def test_inflect_future_no_aspect_calls_lookup_twice(backend):
    """Future without Aspect → _lookup called twice (IPFV;FUT and PFV;FUT), results unioned."""
    per_tag = {"V;1;SG;IPFV;FUT": {"ακούω"}, "V;1;SG;PFV;FUT": {"ακούσω"}}

    def _side(lemma, tag, language):
        return per_tag.get(tag, set())

    with patch("eee.backends.unimorph._lookup", side_effect=_side) as mock_lookup:
        result = backend.inflect(
            "ακούω",
            {"Tense": "Fut", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
            "verb",
            language="ell",
        )
    assert mock_lookup.call_count == 2
    assert result == {"ακούω", "ακούσω"}


def test_inflect_future_explicit_aspect_calls_lookup_once(backend):
    """Future with explicit Aspect=Imp → _lookup called exactly once."""
    with patch("eee.backends.unimorph._lookup", return_value={"ακούω"}) as mock_lookup:
        result = backend.inflect(
            "ακούω",
            {"Tense": "Fut", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
            "verb",
            language="ell",
        )
    assert mock_lookup.call_count == 1
    assert result == {"ακούω"}

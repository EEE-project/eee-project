"""Compare all backend selectors for the same inputs — real data, no mocks.

Three selectors per language:
  language="el"                          — default (ModernGreekBackend)
  language="el",  backend="modern-greek" — explicit name, must equal default
  language="el",  backend="unimorph"     — UniMorphBackend

  language="grc"                           — default (AncientGreekBackend)
  language="grc", backend="ancient-greek"  — explicit name, must equal default
  language="grc", backend="unimorph"       — UniMorphBackend (nouns/adj only)

Run:
    uv run pytest tests/integration/ -m integration
"""
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def clear_index_cache():
    from eee_project.backends.unimorph import _INDEX_CACHE
    _INDEX_CACHE.clear()
    yield
    _INDEX_CACHE.clear()


# ── el: default == modern-greek; unimorph is independent ─────────────────────


def test_el_verb_present_1sg_all_three():
    """el ακούω pres 1sg — default and modern-greek agree; unimorph also matches."""
    import eee_project as eee
    features = {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"}

    result_default     = eee.inflect("ακούω", features, "verb", language="el")
    result_modern_greek = eee.inflect("ακούω", features, "verb", backend="modern-greek")
    result_unimorph    = eee.inflect("ακούω", features, "verb", language="el", backend="unimorph")

    assert result_default == result_modern_greek  # explicit name == default
    assert "ακούω" in result_default
    assert "ακούω" in result_unimorph


def test_el_verb_aorist_1sg_all_three():
    """el ακούω aorist 1sg — default and modern-greek agree; unimorph also matches."""
    import eee_project as eee
    features = {
        "Tense": "Past", "Aspect": "Perf", "Mood": "Ind",
        "Person": "1", "Number": "Sing", "Voice": "Act",
    }

    result_default      = eee.inflect("ακούω", features, "verb", language="el")
    result_modern_greek = eee.inflect("ακούω", features, "verb", backend="modern-greek")
    result_unimorph     = eee.inflect("ακούω", features, "verb", language="el", backend="unimorph")

    assert result_default == result_modern_greek
    assert "άκουσα" in result_default
    assert "άκουσα" in result_unimorph


def test_el_noun_gen_sg_all_three():
    """el μαγκιά gen sg — default and modern-greek agree; unimorph also matches."""
    import eee_project as eee
    features = {"Case": "Gen", "Number": "Sing"}

    result_default      = eee.inflect("μαγκιά", features, "noun", language="el")
    result_modern_greek = eee.inflect("μαγκιά", features, "noun", backend="modern-greek")
    result_unimorph     = eee.inflect("μαγκιά", features, "noun", language="el", backend="unimorph")

    assert result_default == result_modern_greek == {"μαγκιάς"}
    assert result_unimorph == {"μαγκιάς"}


def test_el_default_not_called_for_unimorph():
    """Selecting backend='unimorph' bypasses ModernGreekBackend entirely."""
    import eee_project as eee
    import eee_project._registry as _reg

    features = {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"}

    # Prime the default backend cache to ensure it exists
    _ = eee.inflect("ακούω", features, "verb", language="el")
    default_backend = _reg._cache.get("el")
    assert default_backend is not None

    from unittest.mock import patch
    with patch.object(default_backend, "inflect", wraps=default_backend.inflect) as spy:
        eee.inflect("ακούω", features, "verb", language="el", backend="unimorph")
        spy.assert_not_called()


# ── grc: default == ancient-greek; unimorph is independent ───────────────────


def test_grc_verb_aorist_default_and_ancient_greek_agree():
    """grc λύω aorist — default and ancient-greek return the same forms."""
    import eee_project as eee
    features = {
        "VerbForm": "Fin", "Tense": "Aor", "Mood": "Ind",
        "Voice": "Act", "Person": "1", "Number": "Sing",
    }

    result_default       = eee.inflect("λύω", features, "verb", language="grc")
    result_ancient_greek = eee.inflect("λύω", features, "verb", backend="ancient-greek")

    assert result_default == result_ancient_greek
    assert "ἔλυσα" in result_default


def test_grc_verb_unimorph_not_supported():
    """grc verb — UniMorph has no Ancient Greek verbs, raises PosNotSupportedError."""
    import eee_project as eee
    from eee_project._exceptions import PosNotSupportedError

    features = {
        "VerbForm": "Fin", "Tense": "Aor", "Mood": "Ind",
        "Voice": "Act", "Person": "1", "Number": "Sing",
    }
    with pytest.raises(PosNotSupportedError):
        eee.inflect("λύω", features, "verb", language="grc", backend="unimorph")


def test_grc_noun_default_and_ancient_greek_agree():
    """grc θεός gen sg — default and ancient-greek return the same forms."""
    import eee_project as eee
    features = {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}

    result_default       = eee.inflect("θεός", features, "noun", language="grc")
    result_ancient_greek = eee.inflect("θεός", features, "noun", backend="ancient-greek")

    assert result_default == result_ancient_greek == {"θεοῦ"}


def test_grc_noun_unimorph_independent():
    """grc βοηθός gen sg — UniMorph returns forms from its own TSV dataset."""
    import eee_project as eee

    result_unimorph = eee.inflect(
        "βοηθός", {"Case": "Gen", "Number": "Sing"}, "noun", language="grc", backend="unimorph"
    )
    assert "βοηθοῦ" in result_unimorph


def test_grc_default_not_called_for_unimorph():
    """Selecting backend='unimorph' for grc noun bypasses AncientGreekBackend."""
    import eee_project as eee
    import eee_project._registry as _reg

    # Prime the grc entry-point backend into cache
    _ = eee.inflect("θεός", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "noun", language="grc")
    grc_backend = _reg._cache.get("grc")
    assert grc_backend is not None

    from unittest.mock import patch
    with patch.object(grc_backend, "inflect", wraps=grc_backend.inflect) as spy:
        eee.inflect("βοηθός", {"Case": "Gen", "Number": "Sing"}, "noun", language="grc", backend="unimorph")
        spy.assert_not_called()

"""
Integration tests for the Ancient Greek (grc) backend via eee public API.

Requires ancient-greek-morphology-eee installed (dev dependency).
The backend is auto-discovered via the eee.backends.v1 entry point.
"""
import pytest
import eee


def test_grc_in_supported_languages():
    assert "grc" in eee.supported_languages()


def test_inflect_verb():
    result = eee.inflect(
        "λύω",
        {"VerbForm": "Fin", "Tense": "Aor", "Voice": "Act",
         "Mood": "Ind", "Person": "1", "Number": "Sing"},
        "verb",
        language="grc",
    )
    assert "ἔλυσα" in result


def test_inflect_noun():
    result = eee.inflect(
        "θεός",
        {"Case": "Nom", "Number": "Sing", "Gender": "Masc"},
        "noun",
        language="grc",
    )
    assert "θεός" in result


def test_inflect_adjective():
    result = eee.inflect(
        "ἀγαθός",
        {"Case": "Nom", "Number": "Sing", "Gender": "Fem", "Degree": "Pos"},
        "adjective",
        language="grc",
    )
    assert "ἀγαθή" in result



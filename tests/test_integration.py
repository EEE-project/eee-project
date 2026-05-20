"""
End-to-end integration tests for the eee package.

Exercises the full call chain: public API → registry → lazy load →
ModernGreekBackend → _mg_features → modern-greek-inflexion-eee library.
No mocking. All assertions against real Greek forms.
"""
import subprocess
import sys

import pytest

import eee
from eee import AnalysisNotSupportedError


# ── Lazy-load guarantee ───────────────────────────────────────────────────────


def _run(code: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)


def test_lazy_load_before_inflect():
    result = _run(
        "import eee; "
        "assert 'modern_greek_inflexion_eee' not in __import__('sys').modules, "
        "'library imported at package load time'"
    )
    assert result.returncode == 0, result.stderr


def test_lazy_load_after_inflect():
    result = _run(
        "import eee; "
        "eee.inflect('λύω', {'Tense':'Pres','Mood':'Ind','VerbForm':'Fin','Voice':'Act','Person':'1','Number':'Sing'}, 'verb', language='el'); "
        "assert 'modern_greek_inflexion_eee' in __import__('sys').modules, "
        "'library not imported after inflect()'"
    )
    assert result.returncode == 0, result.stderr


# ── Full round-trip inflect tests ─────────────────────────────────────────────


def test_inflect_verb_present_active_singular():
    result = eee.inflect(
        "λύω",
        {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act", "Person": "1", "Number": "Sing"},
        "verb",
        language="el",
    )
    assert result == {"λύω"}


def test_inflect_verb_third_person_singular():
    result = eee.inflect(
        "λύω",
        {"Tense": "Pres", "Mood": "Ind", "VerbForm": "Fin", "Voice": "Act", "Person": "3", "Number": "Sing"},
        "verb",
        language="el",
    )
    assert result == {"λύει"}


def test_inflect_noun_nom_sing():
    result = eee.inflect(
        "γυναίκα",
        {"Gender": "Fem", "Number": "Sing", "Case": "Nom"},
        "noun",
        language="el",
    )
    assert result == {"γυναίκα"}


def test_inflect_noun_gen_plural():
    result = eee.inflect(
        "γυναίκα",
        {"Gender": "Fem", "Number": "Plur", "Case": "Gen"},
        "noun",
        language="el",
    )
    assert "γυναικών" in result


def test_inflect_adjective():
    result = eee.inflect(
        "καλός",
        {"Degree": "Pos", "Gender": "Masc", "Number": "Sing", "Case": "Nom"},
        "adjective",
        language="el",
    )
    assert result == {"καλός"}


# ── analyze() ─────────────────────────────────────────────────────────────────


def test_analyze_raises_not_supported():
    with pytest.raises(AnalysisNotSupportedError):
        eee.analyze("λόγου", language="el")


# ── supported_languages() ─────────────────────────────────────────────────────


def test_supported_languages_contains_el():
    assert "el" in eee.supported_languages()


# ── Error handling ────────────────────────────────────────────────────────────


def test_unsupported_language_raises():
    with pytest.raises(eee.UnsupportedLanguageError):
        eee.inflect("test", {}, "noun", language="la")


def test_unsupported_error_message_contains_language_code():
    with pytest.raises(eee.UnsupportedLanguageError) as exc_info:
        eee.inflect("test", {}, "noun", language="la")
    assert "la" in str(exc_info.value)

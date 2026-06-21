"""Verify that named backends produce results identical to their defaults.

language="el"  == backend="modern-greek"   for all el inputs
language="grc" == backend="ancient-greek"  for all grc inputs

Each parametrize case is (lemma, features, pos). The test calls inflect() twice
and asserts the results are equal. No other assertion — equality is the contract.

Run:
    uv run pytest tests/integration/test_default_equals_named.py -m integration -v
"""
import pytest
import eee_project as eee

pytestmark = pytest.mark.integration


# ── el: language="el" == backend="modern-greek" ───────────────────────────────

EL_CASES = [
    # verbs — present
    ("ακούω",    {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"}, "verb"),
    ("ακούω",    {"Tense": "Pres", "Mood": "Ind", "Person": "2", "Number": "Sing", "Voice": "Act"}, "verb"),
    ("ακούω",    {"Tense": "Pres", "Mood": "Ind", "Person": "3", "Number": "Sing", "Voice": "Act"}, "verb"),
    ("ακούω",    {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Plur", "Voice": "Act"}, "verb"),
    ("ακούω",    {"Tense": "Pres", "Mood": "Ind", "Person": "2", "Number": "Plur", "Voice": "Act"}, "verb"),
    ("ακούω",    {"Tense": "Pres", "Mood": "Ind", "Person": "3", "Number": "Plur", "Voice": "Act"}, "verb"),
    # verbs — imperfect
    ("ακούω",    {"Tense": "Past", "Aspect": "Imp", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"}, "verb"),
    ("ακούω",    {"Tense": "Past", "Aspect": "Imp", "Mood": "Ind", "Person": "3", "Number": "Plur", "Voice": "Act"}, "verb"),
    # verbs — aorist
    ("ακούω",    {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"}, "verb"),
    ("ακούω",    {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind", "Person": "2", "Number": "Sing", "Voice": "Act"}, "verb"),
    ("ακούω",    {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind", "Person": "3", "Number": "Plur", "Voice": "Act"}, "verb"),
    # verbs — subjunctive (perf)
    ("ακούω",    {"Mood": "Sub", "Aspect": "Perf", "Person": "1", "Number": "Sing", "Voice": "Act"}, "verb"),
    ("ακούω",    {"Mood": "Sub", "Aspect": "Perf", "Person": "3", "Number": "Plur", "Voice": "Act"}, "verb"),
    # second verb paradigm
    ("αγαπώ",   {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"}, "verb"),
    ("αγαπώ",   {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"}, "verb"),
    # nouns
    ("λόγος",   {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "noun"),
    ("λόγος",   {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun"),
    ("λόγος",   {"Case": "Acc", "Number": "Sing", "Gender": "Masc"}, "noun"),
    ("λόγος",   {"Case": "Nom", "Number": "Plur", "Gender": "Masc"}, "noun"),
    ("λόγος",   {"Case": "Gen", "Number": "Plur", "Gender": "Masc"}, "noun"),
    ("μαγκιά",  {"Case": "Gen", "Number": "Sing"}, "noun"),
    ("μαγκιά",  {"Case": "Nom", "Number": "Plur"}, "noun"),
    # adjectives
    ("ωραίος",  {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "adjective"),
    ("ωραίος",  {"Case": "Nom", "Number": "Sing", "Gender": "Fem"},  "adjective"),
    ("ωραίος",  {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "adjective"),
    ("ωραίος",  {"Case": "Nom", "Number": "Plur", "Gender": "Masc"}, "adjective"),
]


def _el_ids():
    return [f"el/{pos}/{lemma}/{'+'.join(f'{k}{v}' for k,v in features.items())}"
            for lemma, features, pos in EL_CASES]


@pytest.mark.parametrize("lemma,features,pos", EL_CASES, ids=_el_ids())
def test_el_language_equals_modern_greek_explicit(lemma, features, pos):
    """language="el" == language="el", backend="modern-greek"."""
    result_language     = eee.inflect(lemma, features, pos, language="el")
    result_modern_greek = eee.inflect(lemma, features, pos, language="el", backend="modern-greek")
    assert result_language == result_modern_greek


@pytest.mark.parametrize("lemma,features,pos", EL_CASES, ids=_el_ids())
def test_el_language_equals_modern_greek_inferred(lemma, features, pos):
    """language="el" == backend="modern-greek"  (language inferred from backend name)."""
    result_language  = eee.inflect(lemma, features, pos, language="el")
    result_inferred  = eee.inflect(lemma, features, pos, backend="modern-greek")
    assert result_language == result_inferred


# ── grc: language="grc" == backend="ancient-greek" ───────────────────────────

GRC_CASES = [
    # verbs — present active indicative
    ("λύω",      {"VerbForm": "Fin", "Tense": "Pres", "Mood": "Ind", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb"),
    ("λύω",      {"VerbForm": "Fin", "Tense": "Pres", "Mood": "Ind", "Voice": "Act", "Person": "2", "Number": "Sing"}, "verb"),
    ("λύω",      {"VerbForm": "Fin", "Tense": "Pres", "Mood": "Ind", "Voice": "Act", "Person": "3", "Number": "Sing"}, "verb"),
    ("λύω",      {"VerbForm": "Fin", "Tense": "Pres", "Mood": "Ind", "Voice": "Act", "Person": "1", "Number": "Plur"}, "verb"),
    # verbs — aorist active indicative
    ("λύω",      {"VerbForm": "Fin", "Tense": "Aor", "Mood": "Ind", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb"),
    ("λύω",      {"VerbForm": "Fin", "Tense": "Aor", "Mood": "Ind", "Voice": "Act", "Person": "2", "Number": "Sing"}, "verb"),
    ("λύω",      {"VerbForm": "Fin", "Tense": "Aor", "Mood": "Ind", "Voice": "Act", "Person": "3", "Number": "Plur"}, "verb"),
    # verbs — imperfect
    ("λύω",      {"VerbForm": "Fin", "Tense": "Imp", "Mood": "Ind", "Voice": "Act", "Person": "1", "Number": "Sing"}, "verb"),
    # nouns
    ("θεός",     {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "noun"),
    ("θεός",     {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun"),
    ("θεός",     {"Case": "Acc", "Number": "Sing", "Gender": "Masc"}, "noun"),
    ("θεός",     {"Case": "Nom", "Number": "Plur", "Gender": "Masc"}, "noun"),
    ("θεός",     {"Case": "Gen", "Number": "Plur", "Gender": "Masc"}, "noun"),
    ("ἄνθρωπος", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "noun"),
    ("ἄνθρωπος", {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun"),
    # adjectives
    ("ἀγαθός",   {"Case": "Nom", "Number": "Sing", "Gender": "Masc", "Degree": "Pos"}, "adjective"),
    ("ἀγαθός",   {"Case": "Nom", "Number": "Sing", "Gender": "Fem",  "Degree": "Pos"}, "adjective"),
    ("ἀγαθός",   {"Case": "Gen", "Number": "Sing", "Gender": "Masc", "Degree": "Pos"}, "adjective"),
    ("ἀγαθός",   {"Case": "Nom", "Number": "Plur", "Gender": "Masc", "Degree": "Pos"}, "adjective"),
]


def _grc_ids():
    return [f"grc/{pos}/{lemma}/{'+'.join(f'{k}{v}' for k,v in features.items())}"
            for lemma, features, pos in GRC_CASES]


@pytest.mark.parametrize("lemma,features,pos", GRC_CASES, ids=_grc_ids())
def test_grc_language_equals_ancient_greek_explicit(lemma, features, pos):
    """language="grc" == language="grc", backend="ancient-greek"."""
    result_language      = eee.inflect(lemma, features, pos, language="grc")
    result_ancient_greek = eee.inflect(lemma, features, pos, language="grc", backend="ancient-greek")
    assert result_language == result_ancient_greek


@pytest.mark.parametrize("lemma,features,pos", GRC_CASES, ids=_grc_ids())
def test_grc_language_equals_ancient_greek_inferred(lemma, features, pos):
    """language="grc" == backend="ancient-greek"  (language inferred from backend name)."""
    result_language  = eee.inflect(lemma, features, pos, language="grc")
    result_inferred  = eee.inflect(lemma, features, pos, backend="ancient-greek")
    assert result_language == result_inferred

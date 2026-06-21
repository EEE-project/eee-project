import pytest
from eee_project.backends.unimorph import ud_to_unimorph_tag
from eee_project._exceptions import FeatureNotSupportedError, PosNotSupportedError


def tokens(tag):
    """Split a single tag string into tokens (for noun/adjective assertions)."""
    return tag.split(";")


# ---------------------------------------------------------------------------
# Verb tests — return type is list[str]
# ---------------------------------------------------------------------------

def test_verb_pres_act_1sg():
    tags = ud_to_unimorph_tag(
        {"VerbForm": "Fin", "Tense": "Pres", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert tags == ["V;1;SG;IPFV;PRS"]


def test_verb_past_imperfective():
    tags = ud_to_unimorph_tag(
        {"Tense": "Past", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert tags == ["V;1;SG;IPFV;PST"]


def test_verb_aorist():
    tags = ud_to_unimorph_tag(
        {"Tense": "Aor", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert tags == ["V;1;SG;PFV;PST"]


def test_verb_aorist_explicit_aspect_perf():
    """Aor + Aspect=Perf (defensive case) → single PFV;PST"""
    tags = ud_to_unimorph_tag(
        {"Tense": "Aor", "Aspect": "Perf", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert tags == ["V;1;SG;PFV;PST"]


def test_verb_perfect_present():
    """Tense=Perf (παρακείμενος) → PRF;PRS"""
    tags = ud_to_unimorph_tag(
        {"Tense": "Perf", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert tags == ["V;1;SG;PRF;PRS"]


def test_verb_future():
    """Future without Aspect → two-element list (IPFV;FUT and PFV;FUT)"""
    tags = ud_to_unimorph_tag(
        {"Tense": "Fut", "Voice": "Act", "Mood": "Ind", "Person": "3", "Number": "Plur"},
        "verb",
    )
    assert "V;3;PL;IPFV;FUT" in tags
    assert "V;3;PL;PFV;FUT" in tags
    assert len(tags) == 2


def test_verb_future_with_explicit_aspect():
    """Future with explicit Aspect=Imp → single IPFV;FUT"""
    tags = ud_to_unimorph_tag(
        {"Tense": "Fut", "Aspect": "Imp", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert tags == ["V;1;SG;IPFV;FUT"]


def test_verb_subjunctive_no_aspect():
    """Subjunctive without Aspect → two-element list (IPFV;SBJV and PFV;SBJV)"""
    tags = ud_to_unimorph_tag(
        {"Mood": "Sub", "Voice": "Act", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert "V;1;SG;IPFV;SBJV" in tags
    assert "V;1;SG;PFV;SBJV" in tags
    assert len(tags) == 2


def test_verb_imperative_2sg():
    """Imperative 2sg → no ASPECT slot, no TENSE slot"""
    tags = ud_to_unimorph_tag(
        {"Mood": "Imp", "Person": "2", "Number": "Sing"},
        "verb",
    )
    assert tags == ["V;2;SG;IMP"]


def test_verb_imperative_2pl():
    tags = ud_to_unimorph_tag(
        {"Mood": "Imp", "Person": "2", "Number": "Plur"},
        "verb",
    )
    assert tags == ["V;2;PL;IMP"]


def test_verb_imperative_with_voice():
    """Voice is stripped before Mood check; imperative+Voice must not raise or include voice."""
    tags = ud_to_unimorph_tag(
        {"Mood": "Imp", "Voice": "Act", "Person": "2", "Number": "Sing"},
        "verb",
    )
    assert tags == ["V;2;SG;IMP"]


def test_verb_voice_ignored():
    """Voice=Pass accepted without error and not present in output tag"""
    tags = ud_to_unimorph_tag(
        {"Tense": "Pres", "Voice": "Pass", "Mood": "Ind", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert len(tags) == 1
    assert "PASS" not in tags[0]
    assert "ACT" not in tags[0]
    assert "MID" not in tags[0]


def test_tag_order_verb():
    """Token order must be V;PERSON;NUMBER;ASPECT;TENSE"""
    tags = ud_to_unimorph_tag(
        {"Tense": "Pres", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
        "verb",
    )
    assert tags == ["V;1;SG;IPFV;PRS"]



def test_verbform_part_raises():
    """VerbForm=Part is out of scope → FeatureNotSupportedError"""
    with pytest.raises(FeatureNotSupportedError):
        ud_to_unimorph_tag(
            {"VerbForm": "Part", "Tense": "Pres", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing"},
            "verb",
        )


def test_verbform_inf_raises():
    """VerbForm=Inf is out of scope → FeatureNotSupportedError"""
    with pytest.raises(FeatureNotSupportedError):
        ud_to_unimorph_tag(
            {"VerbForm": "Inf"},
            "verb",
        )


def test_unknown_feature_raises():
    with pytest.raises(FeatureNotSupportedError):
        ud_to_unimorph_tag(
            {"Tense": "Pres", "Voice": "Act", "Mood": "Ind", "Person": "1", "Number": "Sing", "Polarity": "Neg"},
            "verb",
        )


# ---------------------------------------------------------------------------
# Noun / adjective tests — return type is list[str] (single element)
# ---------------------------------------------------------------------------

def test_noun_nom_sing():
    tags = ud_to_unimorph_tag({"Case": "Nom", "Number": "Sing"}, "noun")
    assert len(tags) == 1
    assert set(tokens(tags[0])) >= {"N", "NOM", "SG"}


def test_adjective_gen_pl_masc():
    tags = ud_to_unimorph_tag({"Case": "Gen", "Number": "Plur", "Gender": "Masc"}, "adjective")
    assert len(tags) == 1
    assert set(tokens(tags[0])) >= {"ADJ", "GEN", "PL", "MASC"}


def test_noun_no_gender():
    tags = ud_to_unimorph_tag({"Case": "Acc", "Number": "Plur"}, "noun")
    t = tokens(tags[0])
    assert "N" in t and "ACC" in t and "PL" in t
    assert not any(g in t for g in ("MASC", "FEM", "NEUT"))


def test_unsupported_pos_raises():
    with pytest.raises(PosNotSupportedError):
        ud_to_unimorph_tag({"Case": "Nom"}, "article")

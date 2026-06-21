"""Live UniMorph TSV lookup tests — require bundled ell.tsv / grc.tsv data files.

Run manually:
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


def test_ell_noun_genitive_returns_nonempty():
    from eee_project.backends.unimorph import UniMorphBackend
    result = UniMorphBackend().inflect(
        "μαγκιά", {"Case": "Gen", "Number": "Sing"}, "noun", language="ell"
    )
    assert result == {"μαγκιάς"}


def test_ell_adjective_nom_sg_masc():
    from eee_project.backends.unimorph import UniMorphBackend
    result = UniMorphBackend().inflect(
        "πράος", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "adjective", language="ell"
    )
    assert result == {"πράος"}


def test_grc_noun_article_stripped():
    from eee_project.backends.unimorph import UniMorphBackend
    result = UniMorphBackend().inflect(
        "βοηθός", {"Case": "Gen", "Number": "Sing"}, "noun", language="grc"
    )
    assert result == {"βοηθοῦ"}


def test_grc_noun_voc_no_article():
    from eee_project.backends.unimorph import UniMorphBackend
    result = UniMorphBackend().inflect(
        "βοηθός", {"Case": "Voc", "Number": "Sing"}, "noun", language="grc"
    )
    assert result == {"βοηθέ"}


def test_missing_lemma_returns_empty():
    from eee_project.backends.unimorph import _lookup
    assert _lookup("nonexistent_lemma", "N;NOM;SG", "ell") == set()


@pytest.mark.integration
def test_verb_present_1sg():
    """ακούω present indicative 1sg — basic verb lookup smoke test."""
    from eee_project.backends.unimorph import UniMorphBackend
    result = UniMorphBackend().inflect(
        "ακούω",
        {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"},
        "verb",
        language="ell",
    )
    assert "ακούω" in result


@pytest.mark.integration
def test_verb_imperfect_1sg():
    """ακούω imperfect 1sg — IPFV;PST tag lookup."""
    from eee_project.backends.unimorph import UniMorphBackend
    result = UniMorphBackend().inflect(
        "ακούω",
        {"Tense": "Past", "Aspect": "Imp", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"},
        "verb",
        language="ell",
    )
    assert "άκουγα" in result


@pytest.mark.integration
def test_verb_aorist_1sg():
    """ακούω aorist 1sg — PFV;PST tag lookup."""
    from eee_project.backends.unimorph import UniMorphBackend
    result = UniMorphBackend().inflect(
        "ακούω",
        {"Tense": "Past", "Aspect": "Perf", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"},
        "verb",
        language="ell",
    )
    assert "άκουσα" in result


@pytest.mark.integration
def test_verb_future_1sg_union():
    """ακούω future 1sg without Aspect — two lookups (IPFV;FUT + PFV;FUT), results unioned."""
    from eee_project.backends.unimorph import UniMorphBackend
    result = UniMorphBackend().inflect(
        "ακούω",
        {"Tense": "Fut", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"},
        "verb",
        language="ell",
    )
    assert "ακούω" in result   # IPFV;FUT form
    assert "ακούσω" in result  # PFV;FUT form


@pytest.mark.integration
def test_verb_perfect_1sg():
    """ακούω perfect 1sg — PRF;PRS tag.

    ell.tsv stores perfect forms as auxiliary + participle ("έχω ακούσει").
    _load_index strips the auxiliary via space-rsplit; only the participle is returned.
    """
    from eee_project.backends.unimorph import UniMorphBackend
    result = UniMorphBackend().inflect(
        "ακούω",
        {"Tense": "Perf", "Mood": "Ind", "Person": "1", "Number": "Sing", "Voice": "Act"},
        "verb",
        language="ell",
    )
    assert "ακούσει" in result


@pytest.mark.integration
def test_verb_imperative_2sg():
    """ακούω imperative 2sg — V;2;SG;IMP tag (no aspect slot)."""
    from eee_project.backends.unimorph import UniMorphBackend
    result = UniMorphBackend().inflect(
        "ακούω",
        {"Mood": "Imp", "Person": "2", "Number": "Sing"},
        "verb",
        language="ell",
    )
    assert "άκου" in result  # one of: άκου, άκουε, άκουσε, άκουγε


@pytest.mark.integration
def test_comma_variant_both_forms_present():
    """δροσίζω 1pl present must return both comma-listed variants from ell.tsv.

    NOTE: requires section-02 verb tag fix to pass end-to-end; _load_index fix alone
    is insufficient because ud_to_unimorph_tag() still produces the wrong verb tag.
    """
    from eee_project.backends.unimorph import UniMorphBackend
    backend = UniMorphBackend()
    result = backend.inflect(
        "δροσίζω",
        {"Tense": "Pres", "Mood": "Ind", "Person": "1", "Number": "Plur", "Voice": "Act"},
        "verb",
        language="ell",
    )
    assert "δροσίζουμε" in result
    assert "δροσίζομε" in result


@pytest.mark.integration
def test_emdash_not_in_results():
    """πέστροφα genitive plural has "—" in TSV; result must be empty, not {"—"}."""
    from eee_project.backends.unimorph import UniMorphBackend
    backend = UniMorphBackend()
    result = backend.inflect(
        "πέστροφα",
        {"Case": "Gen", "Number": "Plur"},
        "noun",
        language="ell",
    )
    assert result == set()


# ── grc: gender-stripping for nouns and adjectives ────────────────────────────


@pytest.mark.integration
def test_grc_noun_with_gender_equals_without_gender():
    """grc noun lookup strips Gender — results identical with or without Gender feature."""
    from eee_project.backends.unimorph import UniMorphBackend
    backend = UniMorphBackend()
    with_gender    = backend.inflect("βοηθός", {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun", language="grc")
    without_gender = backend.inflect("βοηθός", {"Case": "Gen", "Number": "Sing"},                   "noun", language="grc")
    assert with_gender == without_gender
    assert "βοηθοῦ" in with_gender


@pytest.mark.integration
def test_grc_adj_masc_fem_gender_stripped():
    """grc adj Masc/Fem: gender stripped → ADJ;NOM;SG matches masc/fem form."""
    from eee_project.backends.unimorph import UniMorphBackend
    backend = UniMorphBackend()
    masc = backend.inflect("ἄγναπτος", {"Case": "Nom", "Number": "Sing", "Gender": "Masc"}, "adjective", language="grc")
    fem  = backend.inflect("ἄγναπτος", {"Case": "Nom", "Number": "Sing", "Gender": "Fem"},  "adjective", language="grc")
    assert "ἄγναπτος" in masc
    assert masc == fem


@pytest.mark.integration
def test_grc_adj_neut_gender_kept():
    """grc adj Neut: gender kept → ADJ;NOM;SG;NEUT matches neuter form."""
    from eee_project.backends.unimorph import UniMorphBackend
    backend = UniMorphBackend()
    neut = backend.inflect("ἄγναπτος", {"Case": "Nom", "Number": "Sing", "Gender": "Neut"}, "adjective", language="grc")
    assert "ἄγναπτον" in neut
    assert "ἄγναπτος" not in neut


@pytest.mark.integration
def test_grc_noun_gender_via_eee_inflect():
    """eee.inflect with language='grc', backend='unimorph' strips noun gender correctly."""
    import eee_project as eee
    result = eee.inflect("βοηθός", {"Case": "Gen", "Number": "Sing", "Gender": "Masc"}, "noun",
                         language="grc", backend="unimorph")
    assert "βοηθοῦ" in result

"""Language quality manifest tests."""
import eee_project as eee


def test_el_is_dedicated():
    assert eee.language_info("el")["tier"] == "dedicated"


def test_ell_is_unimorph():
    assert eee.language_info("ell")["tier"] == "unimorph"


def test_la_is_unimorph():
    assert eee.language_info("la")["tier"] == "unimorph"


def test_ru_is_unimorph():
    assert eee.language_info("ru")["tier"] == "unimorph"


def test_es_is_unimorph():
    assert eee.language_info("es")["tier"] == "unimorph"


def test_tr_is_unimorph():
    assert eee.language_info("tr")["tier"] == "unimorph"


def test_unknown_code_returns_none():
    assert eee.language_info("xx") is None


def test_manifest_schema_valid():
    # importing eee and calling language_info must not raise ValueError
    assert eee.language_info("el") is not None



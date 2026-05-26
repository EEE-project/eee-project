"""Language quality manifest tests."""
import pytest
import eee


def test_el_is_dedicated():
    assert eee.language_info("el")["tier"] == "dedicated"


def test_ell_is_unimorph():
    assert eee.language_info("ell")["tier"] == "unimorph"


def test_la_is_unsupported():
    assert eee.language_info("la")["tier"] == "unsupported"


def test_unknown_code_returns_none():
    assert eee.language_info("xx") is None


def test_manifest_schema_valid():
    # importing eee and calling language_info must not raise ValueError
    assert eee.language_info("el") is not None


def test_invalid_tier_raises_on_load():
    from eee.backends.unimorph import _validate_manifest
    with pytest.raises(ValueError, match="invalid tier"):
        _validate_manifest({"languages": {"zz": {"tier": "bogus"}}})

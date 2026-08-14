from eee_project._exceptions import (
    UnsupportedLanguageError,
    BackendLoadError,
    AmbiguousPOSError,
    PosNotSupportedError,
)


def test_unsupported_language_error_has_language_code():
    exc = UnsupportedLanguageError("la")
    assert "la" in str(exc)
    assert exc.language_code == "la"


def test_unsupported_language_error_has_install_hint():
    exc = UnsupportedLanguageError("la")
    assert "register_backend" in str(exc)


def test_backend_load_error_chains_cause():
    cause = ImportError("no module named 'latin_eee'")
    try:
        raise BackendLoadError("la", cause) from cause
    except BackendLoadError as exc:
        assert exc.__cause__ is cause


def test_backend_load_error_has_language_code():
    cause = ImportError("missing")
    exc = BackendLoadError("la", cause)
    assert "la" in str(exc)
    assert exc.language_code == "la"


def test_ambiguous_pos_error_has_lemma():
    exc = AmbiguousPOSError("λύω")
    assert "λύω" in str(exc)
    assert exc.lemma == "λύω"


def test_pos_not_supported_error_has_pos():
    exc = PosNotSupportedError("pronoun")
    assert "pronoun" in str(exc)
    assert exc.pos == "pronoun"
    assert exc.language is None


def test_pos_not_supported_error_includes_language_when_given():
    exc = PosNotSupportedError("pronoun", "grc")
    assert "pronoun" in str(exc)
    assert "grc" in str(exc)
    assert exc.language == "grc"

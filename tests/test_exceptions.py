from eee._exceptions import (
    UnsupportedLanguageError,
    BackendLoadError,
    AnalysisNotSupportedError,
    AmbiguousPOSError,
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


def test_analysis_not_supported_error_has_backend_name():
    exc = AnalysisNotSupportedError("ModernGreekBackend")
    assert "ModernGreekBackend" in str(exc)
    assert exc.backend_name == "ModernGreekBackend"


def test_ambiguous_pos_error_has_lemma():
    exc = AmbiguousPOSError("λύω")
    assert "λύω" in str(exc)
    assert exc.lemma == "λύω"

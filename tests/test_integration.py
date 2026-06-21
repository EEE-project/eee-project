"""
Framework-level integration tests for the eee package.

These tests verify error handling and core dispatch without any bundled backend.
Backend-specific inflection tests live in the individual backend repos.
"""
import pytest

import eee_project as eee


def test_unsupported_language_raises():
    with pytest.raises(eee.UnsupportedLanguageError):
        eee.inflect("test", {}, "noun", language="xx-unknown")


def test_unsupported_error_message_contains_language_code():
    with pytest.raises(eee.UnsupportedLanguageError) as exc_info:
        eee.inflect("test", {}, "noun", language="xx-unknown")
    assert "xx-unknown" in str(exc_info.value)


def test_missing_language_raises_value_error():
    with pytest.raises(ValueError, match="language is required"):
        eee.inflect("test", {}, "noun")

"""
Protocol compliance tests for MorphologyBackend.

NOTE: @runtime_checkable Protocol checks method *existence* only, not return
types. A class with `inflect` returning arbitrary types will satisfy
isinstance() regardless.

As of Python 3.12, MagicMock() without spec does NOT satisfy the Protocol
(the runtime check no longer goes through __getattr__). MagicMock(spec=...)
does satisfy it because spec builds a real attribute map.
"""
from unittest.mock import MagicMock


from eee_project._protocol import MorphologyBackend


class _ValidFakeBackend:
    """Has all required Protocol members."""

    language: str = "xx"

    def inflect(self, lemma, features, pos, **_kw):
        return set()


class _MissingInflect:
    """Missing inflect — should NOT satisfy Protocol."""

    language: str = "xx"


class _MissingLanguage:
    """Missing language attribute — should NOT satisfy Protocol."""

    def inflect(self, lemma, features, pos, **_kw):
        return set()


class _ExtraMethodsFakeBackend:
    """Has Protocol members plus extra methods — should still satisfy Protocol."""

    language: str = "xx"

    def inflect(self, lemma, features, pos, **_kw):
        return set()

    def paradigm(self, lemma, pos):
        return {}


class _InstanceLevelLanguage:
    """Sets language only in __init__, no class-level annotation."""

    def __init__(self):
        self.language = "xx"

    def inflect(self, lemma, features, pos, **_kw):
        return set()


def test_valid_fake_backend_satisfies_protocol():
    assert isinstance(_ValidFakeBackend(), MorphologyBackend)


def test_missing_inflect_does_not_satisfy_protocol():
    assert not isinstance(_MissingInflect(), MorphologyBackend)


def test_missing_language_does_not_satisfy_protocol():
    assert not isinstance(_MissingLanguage(), MorphologyBackend)


def test_extra_methods_still_satisfies_protocol():
    assert isinstance(_ExtraMethodsFakeBackend(), MorphologyBackend)


def test_instance_level_language_satisfies_protocol():
    assert isinstance(_InstanceLevelLanguage(), MorphologyBackend)


def test_magicmock_with_spec_satisfies_protocol():
    mock = MagicMock(spec=MorphologyBackend)
    assert isinstance(mock, MorphologyBackend)


def test_magicmock_without_spec_does_not_satisfy_protocol():
    # Python 3.12+ no longer routes isinstance through __getattr__,
    # so MagicMock() without spec correctly fails the check.
    mock = MagicMock()
    assert not isinstance(mock, MorphologyBackend)


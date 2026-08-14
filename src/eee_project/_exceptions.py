class UnsupportedLanguageError(Exception):
    def __init__(self, language_code: str, backend: str | None = None) -> None:
        self.language_code = language_code
        if backend is not None:
            msg = (
                f"No backend named '{backend}' found for language '{language_code}'. "
                f"Install a backend package that registers '{backend}' in the "
                f"eee_project.named_backends.v1 entry point group, or register one explicitly "
                f"with eee.register_backend({language_code!r}, instance, backend={backend!r})."
            )
        else:
            msg = (
                f"No backend registered for language '{language_code}'. "
                f"Install a backend package (e.g., pip install {language_code}-eee) "
                f"or register one with eee.register_backend()."
            )
        super().__init__(msg)


class BackendLoadError(Exception):
    def __init__(self, language_code: str, cause: Exception) -> None:
        self.language_code = language_code
        super().__init__(
            f"Failed to load backend for language '{language_code}': {cause}"
        )


class AmbiguousPOSError(Exception):
    def __init__(self, lemma: str) -> None:
        self.lemma = lemma
        super().__init__(
            f"POS is required but was not provided for lemma '{lemma}'."
        )


class PosNotSupportedError(Exception):
    def __init__(self, pos: str, language: str | None = None) -> None:
        self.pos = pos
        self.language = language
        where = f" for language '{language}'" if language else ""
        super().__init__(f"POS '{pos}' is not supported{where}.")


class FeatureNotSupportedError(Exception):
    def __init__(self, key: str, value: str) -> None:
        self.key = key
        self.value = value
        super().__init__(f"UD feature '{key}={value}' has no UniMorph mapping.")

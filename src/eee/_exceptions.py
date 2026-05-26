class UnsupportedLanguageError(Exception):
    def __init__(self, language_code: str) -> None:
        self.language_code = language_code
        super().__init__(
            f"No backend registered for language '{language_code}'. "
            f"Install a backend package (e.g., pip install {language_code}-eee) "
            f"or register one with eee.register_backend()."
        )


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
    def __init__(self, pos: str) -> None:
        self.pos = pos
        super().__init__(f"POS '{pos}' is not supported by the UniMorph translator.")


class FeatureNotSupportedError(Exception):
    def __init__(self, key: str, value: str) -> None:
        self.key = key
        self.value = value
        super().__init__(f"UD feature '{key}={value}' has no UniMorph mapping.")

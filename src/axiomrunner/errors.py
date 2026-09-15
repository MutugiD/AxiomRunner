"""Domain-specific errors with stable CLI exit semantics."""


class AxiomRunnerError(Exception):
    """Base class for expected application failures."""


class InvalidChallengeError(AxiomRunnerError, ValueError):
    """Raised when a challenge document violates its contract."""


class UnsupportedLanguageError(InvalidChallengeError):
    """Raised before inference for every non-Python challenge."""


class RuntimeUnavailableError(AxiomRunnerError):
    """Raised when a required local runtime is unavailable."""


class OutputWriteError(AxiomRunnerError, OSError):
    """Raised when an output cannot be published atomically."""

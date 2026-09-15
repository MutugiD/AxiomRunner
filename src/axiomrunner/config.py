"""Configuration loading without secret-bearing settings."""

from __future__ import annotations

import os
from collections.abc import Mapping

from axiomrunner.domain import SandboxLimits, SolveOptions


class ConfigurationError(ValueError):
    """Raised when environment configuration is invalid."""


def _integer(values: Mapping[str, str], name: str, default: int, *, minimum: int) -> int:
    raw = values.get(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError as error:
        raise ConfigurationError(f"{name} must be an integer") from error
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return value


def load_options(values: Mapping[str, str] | None = None) -> SolveOptions:
    """Load non-secret defaults from an environment-like mapping."""
    source = os.environ if values is None else values
    return SolveOptions(
        model=source.get("AXIOMRUNNER_MODEL", "qwen3:8b"),
        ollama_host=source.get("AXIOMRUNNER_OLLAMA_HOST", "http://127.0.0.1:11434"),
        seed=_integer(source, "AXIOMRUNNER_SEED", 7, minimum=0),
        candidate_limit=_integer(source, "AXIOMRUNNER_CANDIDATES", 3, minimum=1),
        repair_limit=_integer(source, "AXIOMRUNNER_REPAIRS", 2, minimum=0),
        sandbox=SandboxLimits(
            memory_mb=_integer(source, "AXIOMRUNNER_MEMORY_MB", 256, minimum=64),
            processes=_integer(source, "AXIOMRUNNER_PROCESSES", 64, minimum=1),
        ),
    )

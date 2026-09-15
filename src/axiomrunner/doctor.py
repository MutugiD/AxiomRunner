"""Read-only checks for local runtime prerequisites."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import urlopen

from axiomrunner.domain import SolveOptions


@dataclass(frozen=True, slots=True)
class Diagnostic:
    name: str
    ok: bool
    detail: str


def is_loopback_url(value: str) -> bool:
    parsed = urlsplit(value)
    return parsed.scheme == "http" and parsed.hostname in {"127.0.0.1", "localhost", "::1"}


def _ollama(options: SolveOptions) -> Diagnostic:
    if not is_loopback_url(options.ollama_host):
        return Diagnostic("ollama", False, "endpoint must use HTTP loopback")
    try:
        with urlopen(f"{options.ollama_host.rstrip('/')}/api/tags", timeout=2.0) as response:
            payload = json.load(response)
    except (OSError, URLError, ValueError, json.JSONDecodeError) as error:
        return Diagnostic("ollama", False, f"unavailable: {type(error).__name__}")
    names = {model.get("name") for model in payload.get("models", []) if isinstance(model, dict)}
    if options.model not in names:
        return Diagnostic("ollama", False, f"model is not installed: {options.model}")
    return Diagnostic("ollama", True, f"model available: {options.model}")


def _docker() -> Diagnostic:
    executable = shutil.which("docker")
    if executable is None:
        return Diagnostic("docker", False, "docker executable not found")
    try:
        completed = subprocess.run(
            [executable, "version", "--format", "{{.Server.Version}}"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5.0,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return Diagnostic("docker", False, f"unavailable: {type(error).__name__}")
    if completed.returncode != 0:
        return Diagnostic("docker", False, "daemon is unavailable")
    return Diagnostic("docker", True, f"server available: {completed.stdout.strip()}")


def _output_directory(path: Path) -> Diagnostic:
    target = path.resolve()
    while not target.exists() and target != target.parent:
        target = target.parent
    writable = target.is_dir() and os_access_write(target)
    return Diagnostic(
        "output", writable, f"writable directory: {target}" if writable else "no writable parent"
    )


def os_access_write(path: Path) -> bool:
    """Wrapped for deterministic tests and platform-specific permission checks."""
    import os

    return os.access(path, os.W_OK)


def run_doctor(options: SolveOptions, output_path: str | Path = ".") -> tuple[Diagnostic, ...]:
    return (_ollama(options), _docker(), _output_directory(Path(output_path)))

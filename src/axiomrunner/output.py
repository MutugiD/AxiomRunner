"""Atomic artifact publication."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from axiomrunner.errors import OutputWriteError


def atomic_write_text(path: str | Path, content: str) -> None:
    """Replace a UTF-8 text file without exposing a partial destination."""
    destination = Path(path)
    temporary: Path | None = None
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
    except OSError as error:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise OutputWriteError(f"cannot publish {destination.name}: {error}") from error

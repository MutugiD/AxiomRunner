from pathlib import Path

import pytest

from axiomrunner.errors import OutputWriteError
from axiomrunner.output import atomic_write_text


def test_atomic_write_creates_parents_and_replaces(tmp_path: Path) -> None:
    destination = tmp_path / "nested" / "solution.py"
    atomic_write_text(destination, "def answer():\n    return 1\n")
    assert destination.read_text(encoding="utf-8") == "def answer():\n    return 1\n"
    atomic_write_text(destination, "def answer():\n    return 2\n")
    assert "return 2" in destination.read_text(encoding="utf-8")
    assert not list(destination.parent.glob("*.tmp"))


def test_atomic_write_wraps_os_errors(tmp_path: Path) -> None:
    directory = tmp_path / "directory"
    directory.mkdir()
    with pytest.raises(OutputWriteError):
        atomic_write_text(directory, "content")

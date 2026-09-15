"""Small dependency-free repository policy checks used by initial CI."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TITLE_PATTERN = re.compile(r"^(task|feat): [a-z0-9].+")
TEXT_SUFFIXES = {".md", ".py", ".toml", ".yml", ".yaml"}
FORBIDDEN = ("generated " + "by codex", "co-authored-by: " + "codex")
IGNORED_PARTS = {".git", ".venv", ".mypy_cache", ".pytest_cache", ".ruff_cache", "dist"}


def main() -> int:
    failures: list[str] = []
    required = (ROOT / "README.md", ROOT / "documentation" / "README.md")
    failures.extend(
        f"missing required file: {path.relative_to(ROOT)}"
        for path in required
        if not path.is_file()
    )

    title = os.environ.get("PR_TITLE")
    if title and not TITLE_PATTERN.fullmatch(title):
        failures.append("pull request title must start with 'task: ' or 'feat: '")

    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or any(part in IGNORED_PARTS for part in path.parts)
            or path.suffix not in TEXT_SUFFIXES
        ):
            continue
        text = path.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN:
            if phrase in text:
                failures.append(f"forbidden attribution in {path.relative_to(ROOT)}")

    for failure in failures:
        print(f"ERROR: {failure}", file=sys.stderr)
    return bool(failures)


if __name__ == "__main__":
    raise SystemExit(main())

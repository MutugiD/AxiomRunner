# AxiomRunner

AxiomRunner is a local-first system for producing and validating Python
solutions to adversarial algorithmic challenge specifications.

The project is being delivered documentation-first. Start with the
[documentation index](documentation/README.md).

## Status

Architecture and product definition precede runtime implementation. Python is
the only supported challenge language; hosted and paid model APIs are out of
scope.

## Development

Python 3.12 and `uv` are required.

```text
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run mypy
```

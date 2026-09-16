# AxiomRunner

AxiomRunner is a local-first system for producing and validating Python
solutions to adversarial algorithmic challenge specifications.

The project is being delivered documentation-first. Start with the
[documentation index](documentation/README.md).

## Status

AxiomRunner supports Python function challenges through a local Ollama model
and a resource-limited Docker verification sandbox. Hosted model APIs and Rust
challenge generation are out of scope.

## Usage

Check local prerequisites:

```text
uv run axiomrunner doctor
```

Solve one challenge and retain a redacted evidence report:

```text
uv run axiomrunner solve PROBLEM.json --output SOLUTION.py --report REPORT.json
```

Benchmark a corpus without retaining candidate source:

```text
uv run axiomrunner benchmark PATH --report BENCHMARK.json
```

Exit code `0` means success, `2` invalid or unsupported input, `3` unavailable
local runtime, `4` no verified candidate, and `5` output publication failure.
Candidate code is never executed on the host.

The latest CPU-only `qwen3:8b` corpus run did not meet the `v0.1.0` release
gate; see the [benchmark evidence](documentation/benchmark-methodology.md).

## Development

Python 3.12 and `uv` are required.

```text
uv sync --all-groups
uv run pytest
uv run ruff check .
uv run mypy
```

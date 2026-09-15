# ADR-0002: Support Python Challenges Only

- Status: accepted
- Date: 2026-09-15
- Owners: maintainers

## Decision

The orchestrator, public API, CLI, and generated solutions are Python. Inputs
whose language is not exactly `python` fail validation before inference. Rust
may be installed as developer tooling but is not a product dependency.

## Consequences

Four supplied Rust samples document an unsupported boundary and do not enter
benchmarks or prompts.

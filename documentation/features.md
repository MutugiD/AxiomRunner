# Feature Catalogue and Roadmap

## Feature catalogue

### Input and control plane

- Immutable challenge parsing and Python-only gate.
- Environment, API, and CLI configuration precedence.
- Monotonic deadlines, phase cutoffs, cancellation, and atomic publication.
- Local prerequisite and model diagnostics.

### Reasoning plane

- Constraint and invariant extraction.
- Ambiguity and trap detection.
- Complexity-aware strategy diversification.
- Exact-source generation and bounded counterexample repair.

### Evidence plane

- AST, import, top-level-effect, compilation, and entrypoint checks.
- Public-example conversion and execution.
- Independent boundary, property, metamorphic, and oracle test design.
- Resource-limited dynamic execution and failure minimization.
- Deterministic ranking with evidence provenance.

### Experience and operations

- `solve`, `doctor`, and `benchmark` CLI commands.
- Importable `solve` API.
- Human-readable status plus machine-readable reports.
- Gitignored local run artifacts and benchmark summaries.

## Supported matrix

| Capability | Version 0.1.0 |
| --- | --- |
| Python function challenges | Supported |
| Python standard-library output | Enforced |
| Public examples | Supported when structurally representable |
| Missing public examples | Supported through generated evidence |
| Rust challenge files | Rejected |
| Hosted/cloud models | Rejected |
| Local Ollama models | Supported; `qwen3:8b` default |
| Host candidate execution | Prohibited |
| Docker sandbox | Required for viable status |
| HTTP service | Not included |

## Roadmap

### Foundation

Documentation, contracts, packaging, CI, configuration, input validation, and
deadline control.

### First complete vertical slice

Local analysis, one strategy, one candidate, static checks, sandbox execution,
selection, and atomic output using deterministic fixture responses.

### Reliability expansion

Multiple strategies, independent test design, small oracles, properties,
metamorphic cases, minimization, repairs, and richer evidence scoring.

### Release hardening

Acceptance-corpus runs, resource calibration, failure documentation, package
build, branch protection, and version 0.1.0.

Future work may evaluate additional local models or operating systems. New
challenge languages and hosted APIs require new accepted decisions and are not
implicit extensions.

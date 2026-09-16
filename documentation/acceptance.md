# Acceptance and Observability

## Acceptance corpus

The source corpus contributes these Python challenges by entrypoint:

| Entrypoint | Dominant verification concern |
| --- | --- |
| `simulate_writes` | Compressed outcomes, persistent state, huge retry counts |
| `track_indicator` | Dynamic sequence order, identity, lazy reversals |
| `refresh_references` | Temporal snapshots, candidate precedence, activation |
| `validate_build` | Enormous recursive layouts and container-stack validity |
| `normalize_protection` | Sparse geometry, fixed dimensions, canonical union |
| `capture_binders` | Path-sensitive scope over an unfolded acyclic graph |

The four Rust samples must fail with the unsupported-language result without an
Ollama or Docker call.

## Hosted CI acceptance

- Repository policy and dependency review pass.
- Package builds on Python 3.12.
- Ruff formatting/lint, mypy strict checks, and pytest pass.
- Coverage remains at or above 90% once application code is present.
- Model integration uses deterministic mock responses.
- Docker integration checks prove timeout, network, and read-only controls
  without downloading or running an LLM.

## Local live acceptance

- `doctor` confirms loopback Ollama, `qwen3:8b`, Docker, and output access.
- Each Python sample completes within its declared deadline.
- Published candidates pass syntax, policy, compile, entrypoint, sandbox, and
  every generated mandatory check.
- No source or report is written partially.
- Generated solutions and raw run directories remain untracked.

The latest measured outcome is recorded in
[Benchmark methodology and results](benchmark-methodology.md). The 2026-09-16
CPU run did not meet the Python-corpus release gate, so `v0.1.0` remains
untagged.

The next acceptance run uses the
[Google Colab T4 runbook](colab-t4-runbook.md). A release decision requires the
downloaded evidence bundle from that run; a GPU allocation by itself does not
change the gate.

## Event model

Every run has a random identifier unrelated to problem content. Structured
events include run start/end, phase start/end, model request metrics, candidate
creation, check outcomes, cutoff activation, selection, finalization, and
terminal failure. Default console output is concise; verbose output includes
phase events.

## Report fields

- Schema version, run ID, normalized problem ID, terminal status, and elapsed
  time.
- Non-secret options including model name, candidate limit, seed, and sandbox
  limits.
- Phase timestamps relative to run start and activated cutoffs.
- Candidate IDs, lineage, strategy IDs, model usage, evidence, and score.
- Selected candidate ID or structured failure.

Reports exclude prompt text by default, all environment values, credentials,
absolute host paths, and raw candidate source. An explicit debug mode may store
prompts and source only in the gitignored run directory.

## Benchmark interpretation

Benchmark success means the observable release gates passed within the time
budget. It is not evidence that unavailable hidden cases will pass. Benchmark
summaries report success and failure counts, phase timing, model throughput,
candidate counts, repair counts, and verification coverage.

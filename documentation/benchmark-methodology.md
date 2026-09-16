# Benchmark Methodology and 2026-09-16 Results

## Method

The release benchmark uses the unmodified ten-file ChallengeBox sample corpus:
six Python challenges and four Rust challenges. Files are processed in stable
filename order with one local model request active at a time.

The measured CPU profile was:

- Model: local Ollama `qwen3:8b`, reasoning trace disabled.
- Seed: `7`.
- Candidate limit: `1`.
- Repair limit: `1`.
- Per-problem declared deadline: `300` seconds.
- Candidate-start cutoff: approximately `228` seconds after reserving final
  validation and atomic publication time.
- Sandbox: pinned Python 3.12 image, no network, read-only root/source,
  non-root user, one CPU, 256 MB memory, 64-process limit.
- Host: AMD Ryzen 7 5800U, 8 cores/16 logical processors, 15.3 GiB RAM,
  CPU-only model execution.
- Runtime: Ollama 0.34.0, Docker 29.6.1, Python 3.12.8.

`axiomrunner benchmark` retained no generated source. Its redacted aggregate
report was written outside the repository. The committed table below contains
only normalized outcomes and timing evidence.

## Calibration

A trivial `answer(x) = x + 1` challenge completed successfully in 102.02
seconds with one candidate. It passed syntax, entrypoint, policy, compilation,
the public example, three independent boundary checks, and final static
revalidation.

The supplied problems have much larger contracts. Even after combining
candidate-independent planning into one call and reducing the CPU planning
schema, a direct `simulate_writes` planning request timed out at 228.14 seconds.
There was no remaining safe window for candidate generation.

## Corpus result

| Entrypoint or policy | Status | Seconds | Candidates |
| --- | --- | ---: | ---: |
| `simulate_writes` | Runtime unavailable: model timeout | 228.09 | 0 |
| Rust rejection 1 | Unsupported language, accepted | 0.00 | 0 |
| `track_indicator` | Runtime unavailable: model timeout | 228.00 | 0 |
| `refresh_references` | Runtime unavailable: model timeout | 228.03 | 0 |
| Rust rejection 2 | Unsupported language, accepted | 0.00 | 0 |
| `validate_build` | Runtime unavailable: model timeout | 228.02 | 0 |
| Rust rejection 3 | Unsupported language, accepted | 0.02 | 0 |
| Rust rejection 4 | Unsupported language, accepted | 0.01 | 0 |
| `normalize_protection` | Runtime unavailable: model timeout | 228.03 | 0 |
| `capture_binders` | Runtime unavailable: model timeout | 228.06 | 0 |

Aggregate elapsed time was 1,368.33 seconds. All four Rust inputs were rejected
before inference. None of the six Python problems reached candidate creation,
so no generated source was compiled or published for the corpus.

## Release decision

The `v0.1.0` acceptance gate is **not met** on this host: zero of six Python
challenges produced a verified candidate within the declared deadline. No
release tag is created. This is a throughput failure, not a hidden-test result;
candidate correctness was never evaluated because planning exhausted the
generation window.

The gate can be rerun without changing methodology on a supported GPU host, or
the product decision can be revised to permit a smaller planning model. Either
change requires a new benchmark record. Hardcoding corpus solutions, extending
the challenge deadlines, or silently weakening verification are not valid
release fixes.

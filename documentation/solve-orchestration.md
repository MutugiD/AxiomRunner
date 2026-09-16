# Solve Orchestration

## Production path

`solve(problem, options)` constructs one local Ollama client, one Docker
sandbox, and a `SolveOrchestrator`. The orchestrator owns the monotonic budget,
run identifier, candidate repository, and phase transitions for that request.

1. Produce a compact, candidate-independent plan containing analysis,
   strategies, and exact executable boundary cases.
2. Generate, statically inspect, compile, and sandbox each candidate.
3. Run the compact cases plus any configured oracle, property, or metamorphic
   checks.
4. Minimize observed failures and create bounded child repairs.
5. Rank only candidates with mandatory passes and at least one independent
   behavioral pass.
6. Statically revalidate the selected candidate in the finalization reserve.
7. Return source and evidence to the CLI for atomic publication.

Malformed structured model responses receive one retry. Model/runtime failures
return runtime-unavailable status with partial evidence. Candidate and repair
cutoffs stop new work; existing verified candidates remain eligible. Repaired
source never inherits successful checks and must pass the full pipeline again.

## Publication boundary

The Python API returns `SolveResult` and never chooses filesystem paths. The
CLI atomically publishes the selected source and, when requested, a redacted
JSON report. Reports contain configuration, lineage, model usage, scores, and
observed check results, but omit prompts, source, environment values, and
absolute host paths.

CLI exit codes are:

| Code | Meaning |
| --- | --- |
| `0` | Verified solution published |
| `2` | Invalid input or unsupported language |
| `3` | Ollama, model, Docker, or model protocol unavailable |
| `4` | No candidate passed all selection gates before the deadline |
| `5` | Atomic source or report publication failed |

## Deterministic acceptance

Hosted tests use injected reasoning fixtures while retaining the real
orchestration state machine. A Docker-marked integration test connects the
orchestrator to the production static verifier and container sandbox. Live
model execution remains local because hosted CI does not download Ollama
models.

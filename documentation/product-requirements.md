# Product Requirements

## Product statement

AxiomRunner helps a local developer turn an adversarial Python algorithm
specification into the strongest evidence-backed solution a local model can
produce before a fixed deadline.

## Primary user

The primary user is a technically capable developer evaluating challenge JSON
on a workstation with Python 3.12, Docker, and Ollama. The user values
correctness evidence, predictable local cost, and inspectable failure reports
over conversational interaction.

## Goals

- Accept a general challenge JSON file and write an exact-entrypoint Python
  solution before its declared deadline.
- Detect statement traps and complexity constraints before generation.
- Verify candidates independently and rank only observed evidence.
- Keep prompts, code, execution, and reports local.
- Explain why a solve succeeded or failed without exposing secrets.
- Offer the same behavior through a CLI and an importable Python function.

## Non-goals

- Rust or any non-Python challenge language.
- Hosted, cloud-tagged, or paid model APIs.
- A web or HTTP service.
- Direct submission to an external judge.
- Hardcoded implementations for supplied samples.
- A claim that locally generated tests prove hidden-test correctness.
- Host execution of generated candidate modules.

## Functional requirements

| ID | Requirement |
| --- | --- |
| FR-01 | Validate all challenge fields and reject unsupported language before inference. |
| FR-02 | Use a monotonic solve budget derived from `deadline_s`. |
| FR-03 | Produce structured analysis covering constraints, invariants, ambiguities, complexity, and test ideas. |
| FR-04 | Produce distinct strategies and one or more lineage-tracked candidates. |
| FR-05 | Enforce syntax, entrypoint, import, and prohibited-operation policy. |
| FR-06 | Dynamically verify only in the configured disposable sandbox. |
| FR-07 | Run public examples plus independent boundary, oracle, property, and metamorphic tests when representable. |
| FR-08 | Repair from minimized counterexamples while the repair window remains open. |
| FR-09 | Select deterministically from viable observed evidence. |
| FR-10 | Atomically publish source and optionally publish a redacted JSON report. |
| FR-11 | Diagnose local prerequisites through `axiomrunner doctor`. |
| FR-12 | Benchmark a file or directory without committing generated artifacts. |

## Quality attributes

- **Safety:** generated source never imports on the host and cannot use network
  inside its sandbox.
- **Timeliness:** no phase can consume the finalization reserve.
- **Auditability:** candidate lineage, test origin, outcomes, and timing appear
  in the report.
- **Determinism:** configuration, fixed seed, evidence ordering, scoring, and
  tie-breaking are reproducible; local model kernels may still vary.
- **Portability:** host application behavior supports Windows and Linux;
  sandbox execution uses a pinned Linux Python image.
- **Maintainability:** typed contracts isolate the model, verifier, sandbox,
  storage, and clock.

## Failure behavior

Invalid input, unsupported language, unavailable prerequisites, no viable
candidate, and output failure are distinct terminal results. Existing output
files survive every failed solve. When requested, reports are produced for all
failures after successful input parsing.

## Release acceptance

Version 0.1.0 requires green hosted CI, deterministic integration fixtures,
and local end-to-end attempts for all six supplied Python samples using
`qwen3:8b`. Each attempt must finish within 300 seconds and either publish a
candidate satisfying all mandatory gates or produce an auditable failure
without a partial solution.

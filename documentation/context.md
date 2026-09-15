# Challenge Context

## Source brief

The source repository defines a system that accepts a challenge JSON document
and must return a correct implementation before a per-problem deadline. A
challenge contains an identifier, target language, statement, entrypoint,
optional public examples, and a deadline in seconds.

The supplied corpus contains ten problems: six target Python and four target
Rust. Public examples are absent. AxiomRunner intentionally supports only the
six Python problems and rejects every other language before model inference.

## Constraints that shape the product

- A single wrong hidden case scores zero, so observable verification evidence
  is more important than a model's confidence.
- Statements deliberately contain semantic traps, extreme numeric bounds,
  compressed structures, and workloads that make naive enumeration invalid.
- Generated Python must expose the requested function, use only the standard
  library, perform no input/output, and arrive before the deadline.
- There is no paid inference service. Planning, generation, critique, and
  repair run through a local Ollama server.
- Hidden tests are unavailable. The system must create independent small
  oracles, boundary cases, properties, and metamorphic checks.

## Product boundary

AxiomRunner is a Python package and CLI for general Python challenge JSON. It
is not a judge, hosted service, IDE, Rust solver, or guarantee of hidden-test
success. Generated artifacts and benchmark runs remain local unless explicitly
published.

# ADR-0001: Use Local Ollama Only

- Status: accepted
- Date: 2026-09-15
- Owners: maintainers

## Context

The product must not incur hosted inference charges and must keep challenge
content local.

## Decision

Use Ollama through a loopback-only HTTP endpoint. Default to `qwen3:8b` and use
`qwen3:1.7b` only for development smoke tests. Reject non-loopback endpoints.

## Consequences

Hosted CI uses mocks rather than live inference. Throughput is sequential and
deadline management must account for local model speed.

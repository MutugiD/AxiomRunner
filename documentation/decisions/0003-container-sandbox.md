# ADR-0003: Execute Candidates in Disposable Containers

- Status: accepted
- Date: 2026-09-15
- Owners: maintainers

## Decision

Dynamic verification uses pinned Python Docker images with network disabled,
read-only mounts, a non-root user, dropped capabilities, and explicit CPU,
memory, process, and time limits. Candidate code is never imported on the host.

## Consequences

Docker is required for full solves. Static-only checks may run without Docker
but cannot make a candidate viable.

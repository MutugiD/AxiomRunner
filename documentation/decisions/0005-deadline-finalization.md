# ADR-0005: Reserve Time for Deterministic Finalization

- Status: accepted
- Date: 2026-09-15
- Owners: maintainers

## Decision

Use a monotonic clock, absolute phase deadlines, an 80% candidate cutoff, a 90%
repair cutoff, and a protected finalization reserve of 5% bounded to 10-20
seconds.

## Consequences

The solver stops improving before the overall deadline so a complete validated
artifact can be written atomically.
